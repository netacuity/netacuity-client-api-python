# Copyright 2026 Digital Envoy, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared constants, exceptions, and base client state for the NetAcuity UDP protocol clients."""

import ipaddress
import socket
from typing import Optional

DEFAULT_TIMEOUT_SECONDS = 2.0
DEFAULT_PORT = 5400
MAX_MESSAGE_SIZE = 1500


class NetAcuityError(Exception):
    """Raised when a NetAcuity UDP query fails or the server returns an error.

    raw_response is set when a response was received but rejected (IP/transaction-ID
    mismatch, DB-level error); None if no response was ever received.
    """

    def __init__(self, message: str, raw_response: Optional[str] = None) -> None:
        super().__init__(message)
        self.raw_response = raw_response


def address_family_for(host: str) -> socket.AddressFamily:
    """Return the socket address family appropriate for *host*."""
    return socket.AF_INET6 if ":" in host else socket.AF_INET


def ips_equal(a: str, b: str) -> bool:
    """Return whether *a* and *b* denote the same IP address.

    Compares parsed address objects rather than raw text so that two
    differently-formatted-but-equal IPv6 literals (e.g. ``2001:db8::1`` vs.
    ``2001:0db8:0000:0000:0000:0000:0000:0001``) are correctly treated as
    equal. A malformed value is never treated as equal to anything.
    """
    try:
        return ipaddress.ip_address(a) == ipaddress.ip_address(b)
    except ValueError:
        return False


class BaseNetAcuityClient:
    """Shared timeout/API ID state for NetAcuity UDP protocol clients.

    ``timeout_seconds`` is a plain public attribute — assign to it directly
    (e.g. ``client.timeout_seconds = 5.0``) to change it. ``api_id`` is a
    validating property; assigning it directly (e.g. ``client.api_id = 5``)
    still works, but raises NetAcuityError if the value is out of range.
    """

    def __init__(
        self, host: str, api_id: int, port: int, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    ) -> None:
        try:
            ipaddress.ip_address(host)
        except ValueError as e:
            raise NetAcuityError(f"invalid server address: {host}") from e
        self.port = port
        self.api_id = api_id
        self.timeout_seconds = timeout_seconds
        self.addr_family = address_family_for(host)

    @property
    def api_id(self) -> int:
        return self._api_id

    @api_id.setter
    def api_id(self, value: int) -> None:
        if not (0 <= value <= 127):
            raise NetAcuityError(f"invalid API ID: {value}")
        self._api_id = value
