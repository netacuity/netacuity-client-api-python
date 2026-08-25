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

"""NetAcuity XML UDP protocol client."""

import contextlib
import ipaddress
import socket
from typing import Dict
from xml.etree import ElementTree

from netacuity._common import (
    DEFAULT_PORT,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_MESSAGE_SIZE,
    BaseNetAcuityClient,
    NetAcuityError,
    ips_equal,
)

PACKET_HEADER_SIZE = 4
PACKET_SEQUENCE_SLICE = slice(0, 2)
PACKET_TOTAL_SLICE = slice(2, 4)


class NetAcuityXML(BaseNetAcuityClient):
    """NetAcuity XML UDP protocol client."""

    def __init__(
        self,
        server: str,
        api_id: int = 0,
        *,
        port: int = DEFAULT_PORT,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the NetAcuityXML object."""
        super().__init__(server, api_id, port, timeout_seconds=timeout_seconds)
        self.server = server

    def query_xml(self, ip: str, feature_codes: str, transaction_id: int) -> str:
        """Run an XML UDP query and return the XML response.

        Raises:
            NetAcuityError: if a feature code is invalid, the query fails, or
                packets are received out of order.
        """
        feature_code_list = feature_codes.split(",")
        normalized_feature_codes = []
        for code in feature_code_list:
            try:
                code_int = int(code)
            except ValueError as e:
                raise NetAcuityError(f"invalid feature code: {code}") from e
            if not (3 <= code_int < 100):
                raise NetAcuityError(f"invalid feature code: {code}")
            normalized_feature_codes.append(code_int)

        try:
            ipaddress.ip_address(ip)
        except ValueError as e:
            raise NetAcuityError(f"invalid query IP: {ip}") from e
        xml_special_chars = {'"', "<", ">", "&"}
        if any(c in xml_special_chars for c in str(transaction_id)):
            raise NetAcuityError("transaction_id must not contain XML-special characters")

        queries = "".join(f' <query db="{code}"/>' for code in normalized_feature_codes)
        request = f'<request trans-id="{transaction_id}" ip="{ip}" api-id="{self.api_id}">{queries}</request>'

        done = False
        packets = 0
        response = []

        try:
            with contextlib.closing(socket.socket(self.addr_family, socket.SOCK_DGRAM)) as nasocket:
                nasocket.settimeout(self.timeout_seconds)
                # Restricts the OS to only deliver datagrams from (self.server, self.port) on
                # this socket, rejecting spoofed/stray packets from any other source.
                nasocket.connect((self.server, self.port))
                nasocket.send(request.encode("utf-8"))
                while not done:
                    res = nasocket.recv(MAX_MESSAGE_SIZE)
                    packets += 1
                    if int(res[PACKET_SEQUENCE_SLICE].decode("ascii").strip()) != packets:
                        raise NetAcuityError("packets received out of order")
                    response.append(res[PACKET_HEADER_SIZE:-1].decode("utf-8"))
                    if int(res[PACKET_TOTAL_SLICE].decode("ascii").strip()) == packets:
                        done = True
        except socket.timeout as e:
            raise NetAcuityError("timeout awaiting response") from e
        except (OSError, UnicodeDecodeError, ValueError) as e:
            raise NetAcuityError(f"python exception: {e!r}") from e

        full_response = "".join(response)
        try:
            root = ElementTree.fromstring(full_response)
        except ElementTree.ParseError as e:
            raise NetAcuityError(f"invalid XML response: {e!r}") from e

        error = root.get("error", "")
        if error != "":
            raise NetAcuityError(error, raw_response=full_response)

        response_trans_id = root.get("trans-id")
        if response_trans_id != str(transaction_id):
            raise NetAcuityError(
                f"response transaction ID mismatch: expected {transaction_id}, got {response_trans_id}",
                raw_response=full_response,
            )
        response_ip = root.get("ip")
        if not ips_equal(response_ip, ip):
            raise NetAcuityError(
                f"response IP mismatch: expected {ip}, got {response_ip}",
                raw_response=full_response,
            )

        return full_response

    def parse_response(self, xml: str) -> Dict[str, str]:
        """Parse a response XML string into a dict of field name to value."""
        parsed = {}
        root = ElementTree.fromstring(xml)
        for attribute in root.attrib:
            parsed[attribute] = root.get(attribute)
        return parsed
