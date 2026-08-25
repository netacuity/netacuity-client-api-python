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

"""Shared test helpers for building mock NetAcuity UDP response packets."""

from unittest.mock import MagicMock


def make_xml_packet(current_packet, total_packets, xml_chunk):
    """Build a valid XML UDP response packet.

    Layout: 2-byte ASCII-encoded current packet number (space-padded)
             + 2-byte ASCII-encoded total packet count (space-padded)
             + UTF-8 encoded XML chunk
             + null terminator byte
    """
    return (
        f"{current_packet:2d}".encode('ascii')
        + f"{total_packets:2d}".encode('ascii')
        + xml_chunk.encode("utf-8")
        + b"\x00"
    )


def make_socket_mock(responses):
    """Return a mock socket whose recv yields each item in *responses* in turn."""
    mock_sock = MagicMock()
    mock_sock.recv.side_effect = list(responses)
    return mock_sock