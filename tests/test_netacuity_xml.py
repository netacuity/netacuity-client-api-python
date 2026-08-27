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

"""Tests for netacuity.netacuity_xml (NetAcuityXML XML UDP protocol)."""

import socket
import struct
import pytest
from unittest.mock import patch, MagicMock
from xml.etree import ElementTree

from netacuity.netacuity_xml import NetAcuityXML, NetAcuityError, DEFAULT_PORT, DEFAULT_TIMEOUT_SECONDS
from tests.helpers import make_xml_packet, make_socket_mock


@pytest.fixture
def mock_socket_class():
    """Patch netacuity.netacuity_xml.socket.socket for the duration of a test."""
    with patch("netacuity.netacuity_xml.socket.socket") as mock_class:
        yield mock_class


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestNetAcuityXMLInit:
    def test_server_stored(self):
        na = NetAcuityXML("192.0.2.1")
        assert na.server == "192.0.2.1"

    def test_default_api_id(self):
        na = NetAcuityXML("192.0.2.1")
        assert na.api_id == 0

    def test_default_port(self):
        na = NetAcuityXML("192.0.2.1")
        assert na.port == DEFAULT_PORT

    def test_default_timeout(self):
        na = NetAcuityXML("192.0.2.1")
        assert na.timeout_seconds == DEFAULT_TIMEOUT_SECONDS

    def test_custom_api_id(self):
        na = NetAcuityXML("192.0.2.1", api_id=42)
        assert na.api_id == 42

    def test_custom_port(self):
        na = NetAcuityXML("192.0.2.1", port=5401)
        assert na.port == 5401

    def test_ipv4_uses_af_inet(self):
        na = NetAcuityXML("192.0.2.3")
        assert na.addr_family == socket.AF_INET

    def test_ipv6_uses_af_inet6(self):
        na = NetAcuityXML("2001:db8::1")
        assert na.addr_family == socket.AF_INET6

    def test_ipv6_localhost_uses_af_inet6(self):
        na = NetAcuityXML("2001:db8::2")
        assert na.addr_family == socket.AF_INET6

    def test_ipv4_no_colon_is_af_inet(self):
        na = NetAcuityXML("192.0.2.2")
        assert na.addr_family == socket.AF_INET


# ---------------------------------------------------------------------------
# Attribute assignment
# ---------------------------------------------------------------------------

class TestNetAcuityXMLAttributes:
    def test_set_timeout_seconds(self):
        na = NetAcuityXML("192.0.2.1")
        na.timeout_seconds = 5.0
        assert na.timeout_seconds == 5.0

    def test_set_timeout_replaces_default(self):
        na = NetAcuityXML("192.0.2.1")
        na.timeout_seconds = 0.1
        assert na.timeout_seconds != DEFAULT_TIMEOUT_SECONDS

    def test_set_api_id(self):
        na = NetAcuityXML("192.0.2.1")
        na.api_id = 77
        assert na.api_id == 77

    def test_set_api_id_and_timeout_independently(self):
        na = NetAcuityXML("192.0.2.1")
        na.api_id = 20
        na.timeout_seconds = 3.0
        assert na.api_id == 20
        assert na.timeout_seconds == 3.0

    def test_set_api_id_below_zero_raises(self):
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError, match="invalid API ID"):
            na.api_id = -1

    def test_set_api_id_above_127_raises(self):
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError, match="invalid API ID"):
            na.api_id = 128


# ---------------------------------------------------------------------------
# query_xml — request construction
# ---------------------------------------------------------------------------

class TestQueryXmlRequestConstruction:
    def _get_sent_xml(self, mock_sock):
        return mock_sock.send.call_args[0][0].decode("utf-8")

    def test_single_feature_code_produces_one_query_element(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="123" ip="192.0.2.2"/>')
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1", api_id=1)
        na.query_xml("192.0.2.2", "3", 123)
        xml_str = self._get_sent_xml(mock_socket_class.return_value)
        root = ElementTree.fromstring(xml_str)
        queries = root.findall("query")
        assert len(queries) == 1
        assert queries[0].get("db") == "3"

    def test_multiple_feature_codes_produce_multiple_query_elements(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="123" ip="192.0.2.2"/>')
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1", api_id=1)
        na.query_xml("192.0.2.2", "3,4,10", 123)
        xml_str = self._get_sent_xml(mock_socket_class.return_value)
        root = ElementTree.fromstring(xml_str)
        queries = root.findall("query")
        assert len(queries) == 3
        assert queries[0].get("db") == "3"
        assert queries[1].get("db") == "4"
        assert queries[2].get("db") == "10"

    @pytest.mark.parametrize("noncanonical, canonical", [("+3", "3"), ("03", "3")])
    def test_noncanonical_feature_code_is_normalized_in_request(self, noncanonical, canonical, mock_socket_class):
        # int("+3") == int("03") == 3, so these pass validation -- but the
        # outgoing XML must embed the normalized "3", not the raw input text.
        packet = make_xml_packet(1, 1, '<response trans-id="123" ip="192.0.2.2"/>')
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1", api_id=1)
        na.query_xml("192.0.2.2", noncanonical, 123)
        xml_str = self._get_sent_xml(mock_socket_class.return_value)
        assert f'db="{noncanonical}"' not in xml_str
        root = ElementTree.fromstring(xml_str)
        queries = root.findall("query")
        assert len(queries) == 1
        assert queries[0].get("db") == canonical

    def test_request_includes_trans_id(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="456" ip="192.0.2.2"/>')
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1")
        na.query_xml("192.0.2.2", "3", 456)
        xml_str = self._get_sent_xml(mock_socket_class.return_value)
        root = ElementTree.fromstring(xml_str)
        assert root.get("trans-id") == "456"

    def test_request_includes_query_ip(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="1" ip="198.51.100.1"/>')
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1")
        na.query_xml("198.51.100.1", "3", 1)
        xml_str = self._get_sent_xml(mock_socket_class.return_value)
        root = ElementTree.fromstring(xml_str)
        assert root.get("ip") == "198.51.100.1"

    def test_request_includes_api_id(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="1" ip="192.0.2.2"/>')
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1", api_id=77)
        na.query_xml("192.0.2.2", "3", 1)
        xml_str = self._get_sent_xml(mock_socket_class.return_value)
        root = ElementTree.fromstring(xml_str)
        assert root.get("api-id") == "77"

    def test_request_sent_to_correct_server_and_port(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="1" ip="192.0.2.2"/>')
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1", port=5403)
        na.query_xml("192.0.2.2", "3", 1)
        dest = mock_socket_class.return_value.connect.call_args[0][0]
        assert dest == ("192.0.2.1", 5403)

    def test_socket_connected_to_server_before_send(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="1" ip="192.0.2.2"/>')
        mock_sock = make_socket_mock([packet])
        mock_socket_class.return_value = mock_sock
        na = NetAcuityXML("192.0.2.1")
        na.query_xml("192.0.2.2", "3", 1)
        # connect() restricts the OS to only deliver datagrams back from this
        # peer, rejecting spoofed/stray packets from any other source.
        mock_sock.connect.assert_called_once_with(("192.0.2.1", 5400))

    def test_timeout_applied_to_socket(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="1" ip="192.0.2.2"/>')
        mock_sock = make_socket_mock([packet])
        mock_socket_class.return_value = mock_sock
        na = NetAcuityXML("192.0.2.1")
        na.timeout_seconds = 6.0
        na.query_xml("192.0.2.2", "3", 1)
        mock_sock.settimeout.assert_called_with(6.0)

    def test_default_timeout_applied_to_socket(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="1" ip="192.0.2.2"/>')
        mock_sock = make_socket_mock([packet])
        mock_socket_class.return_value = mock_sock
        na = NetAcuityXML("192.0.2.1")
        na.query_xml("192.0.2.2", "3", 1)
        mock_sock.settimeout.assert_called_with(DEFAULT_TIMEOUT_SECONDS)

    def test_ipv4_socket_created_for_ipv4_server(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="1" ip="192.0.2.2"/>')
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1")
        na.query_xml("192.0.2.2", "3", 1)
        mock_socket_class.assert_called_with(socket.AF_INET, socket.SOCK_DGRAM)

    def test_ipv6_socket_created_for_ipv6_server(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="1" ip="2001:db8::1"/>')
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("2001:db8::ff")
        na.query_xml("2001:db8::1", "3", 1)
        mock_socket_class.assert_called_with(socket.AF_INET6, socket.SOCK_DGRAM)


# ---------------------------------------------------------------------------
# query_xml — response parsing
# ---------------------------------------------------------------------------

class TestQueryXmlResponseParsing:
    def test_single_packet_response_returned(self, mock_socket_class):
        xml_body = '<response trans-id="1" ip="192.0.2.2" country="usa"/>'
        packet = make_xml_packet(1, 1, xml_body)
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1")
        xml = na.query_xml("192.0.2.2", "3", 1)
        assert xml == xml_body


class TestQueryXmlMultiPacket:
    def test_two_packet_response_is_reassembled(self, mock_socket_class):
        chunk1 = '<response trans-id="1" ip="192.0.2.2" '
        chunk2 = 'country="usa"/>'
        p1 = make_xml_packet(1, 2, chunk1)
        p2 = make_xml_packet(2, 2, chunk2)
        mock_socket_class.return_value = make_socket_mock([p1, p2])
        na = NetAcuityXML("192.0.2.1")
        xml = na.query_xml("192.0.2.2", "3", 1)
        assert xml == chunk1 + chunk2

    def test_three_packet_response_is_reassembled(self, mock_socket_class):
        chunks = ['<response trans-id="1" ip="192.0.2.2" ', 'a="1" ', 'b="2"/>']
        packets = [
            make_xml_packet(i + 1, 3, chunk)
            for i, chunk in enumerate(chunks)
        ]
        mock_socket_class.return_value = make_socket_mock(packets)
        na = NetAcuityXML("192.0.2.1")
        xml = na.query_xml("192.0.2.2", "3", 1)
        assert xml == "".join(chunks)

    def test_out_of_order_packet_raises_error(self, mock_socket_class):
        # Send packet numbered 2 when packet 1 is expected.
        bad_packet = make_xml_packet(2, 2, "<response/>")
        mock_socket_class.return_value = make_socket_mock([bad_packet])
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError, match="out of order"):
            na.query_xml("192.0.2.2", "3", 1)


# ---------------------------------------------------------------------------
# query_xml — error handling
# ---------------------------------------------------------------------------

class TestQueryXmlInputValidation:
    @pytest.mark.parametrize("special_char", ['"', "<", ">", "&"])
    def test_trans_id_with_xml_special_char_raises(self, special_char, mock_socket_class):
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError, match="XML-special characters"):
            na.query_xml("192.0.2.2", "3", f"1{special_char}2")

    def test_trans_id_without_special_chars_is_allowed(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="123" ip="192.0.2.2"/>')
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1")
        na.query_xml("192.0.2.2", "3", 123)

    # -- feature code (database) range: "3 <= db < 100" for every comma-separated entry --

    def test_feature_code_below_range_raises(self, mock_socket_class):
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError, match="invalid feature code"):
            na.query_xml("192.0.2.2", "2", 123)

    def test_feature_code_at_or_above_100_raises(self, mock_socket_class):
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError, match="invalid feature code"):
            na.query_xml("192.0.2.2", "100", 123)

    def test_non_integer_feature_code_raises(self, mock_socket_class):
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError, match="invalid feature code"):
            na.query_xml("192.0.2.2", "geo", 123)

    def test_one_invalid_code_in_a_comma_separated_list_raises(self, mock_socket_class):
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError, match="invalid feature code"):
            na.query_xml("192.0.2.2", "3,200", 123)

    def test_feature_code_lower_bound_is_valid(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="123" ip="192.0.2.2"/>')
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1")
        na.query_xml("192.0.2.2", "3", 123)

    def test_feature_code_upper_bound_is_valid(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="123" ip="192.0.2.2"/>')
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1")
        na.query_xml("192.0.2.2", "99", 123)

    # -- query IP validation --

    def test_invalid_query_ip_raises(self, mock_socket_class):
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError, match="invalid query IP"):
            na.query_xml("not-an-ip", "3", 123)


class TestNetAcuityXMLApiIdValidation:
    # -- api_id range (validated in BaseNetAcuityClient.__init__) --

    def test_api_id_below_zero_raises(self):
        with pytest.raises(NetAcuityError, match="invalid API ID"):
            NetAcuityXML("192.0.2.1", api_id=-1)

    def test_api_id_above_127_raises(self):
        with pytest.raises(NetAcuityError, match="invalid API ID"):
            NetAcuityXML("192.0.2.1", api_id=128)

    def test_api_id_lower_bound_is_valid(self):
        na = NetAcuityXML("192.0.2.1", api_id=0)
        assert na.api_id == 0

    def test_api_id_upper_bound_is_valid(self):
        na = NetAcuityXML("192.0.2.1", api_id=127)
        assert na.api_id == 127


class TestQueryXmlErrorHandling:
    def test_socket_timeout_raises_timeout_error(self, mock_socket_class):
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = socket.timeout("timed out")
        mock_socket_class.return_value = mock_sock
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError, match="timeout"):
            na.query_xml("192.0.2.2", "3", 1)

    def test_os_error_raises_exception_error(self, mock_socket_class):
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = OSError("network unreachable")
        mock_socket_class.return_value = mock_sock
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError, match="exception"):
            na.query_xml("192.0.2.2", "3", 1)

    def test_socket_creation_failure_raises_exception_error(self, mock_socket_class):
        mock_socket_class.side_effect = OSError("cannot create socket")
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError, match="exception"):
            na.query_xml("192.0.2.2", "3", 1)

    def test_socket_closed_after_successful_query(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="1" ip="192.0.2.2"/>')
        mock_sock = make_socket_mock([packet])
        mock_socket_class.return_value = mock_sock
        na = NetAcuityXML("192.0.2.1")
        na.query_xml("192.0.2.2", "3", 1)
        mock_sock.close.assert_called()

    def test_socket_closed_after_timeout(self, mock_socket_class):
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = socket.timeout()
        mock_socket_class.return_value = mock_sock
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError):
            na.query_xml("192.0.2.2", "3", 1)
        mock_sock.close.assert_called()

    def test_socket_closed_after_os_error(self, mock_socket_class):
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = OSError("fail")
        mock_socket_class.return_value = mock_sock
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError):
            na.query_xml("192.0.2.2", "3", 1)
        mock_sock.close.assert_called()

    def test_differently_formatted_equal_ipv6_response_ip_accepted(self, mock_socket_class):
        # The server may echo back a compressed form of the same IPv6 address
        # that was queried in expanded form -- this must not be treated as a
        # mismatch.
        packet = make_xml_packet(1, 1, '<response trans-id="1" ip="2001:db8::1"/>')
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("2001:db8::ff")
        na.query_xml("2001:0db8:0000:0000:0000:0000:0000:0001", "3", 1)

    def test_genuinely_different_response_ip_raises_mismatch(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response trans-id="1" ip="198.51.100.9"/>')
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError, match="response IP mismatch"):
            na.query_xml("198.51.100.1", "3", 1)

    def test_server_error_in_response_raises_with_error_string(self, mock_socket_class):
        packet = make_xml_packet(1, 1, '<response error="DB Not Loaded"/>')
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError, match="DB Not Loaded"):
            na.query_xml("192.0.2.2", "3", 1)

    def test_server_error_preserves_raw_response_for_diagnostics(self, mock_socket_class):
        xml_body = '<response error="DB Not Loaded"/>'
        packet = make_xml_packet(1, 1, xml_body)
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError) as exc_info:
            na.query_xml("192.0.2.2", "3", 1)
        assert exc_info.value.raw_response == xml_body

    def test_ip_mismatch_preserves_raw_response_for_diagnostics(self, mock_socket_class):
        xml_body = '<response trans-id="1" ip="198.51.100.9"/>'
        packet = make_xml_packet(1, 1, xml_body)
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError) as exc_info:
            na.query_xml("198.51.100.1", "3", 1)
        assert exc_info.value.raw_response == xml_body

    def test_transaction_id_mismatch_preserves_raw_response_for_diagnostics(self, mock_socket_class):
        xml_body = '<response trans-id="999" ip="192.0.2.2"/>'
        packet = make_xml_packet(1, 1, xml_body)
        mock_socket_class.return_value = make_socket_mock([packet])
        na = NetAcuityXML("192.0.2.1")
        with pytest.raises(NetAcuityError, match="transaction ID mismatch") as exc_info:
            na.query_xml("192.0.2.2", "3", 1)
        assert exc_info.value.raw_response == xml_body


# ---------------------------------------------------------------------------
# parse_response
# ---------------------------------------------------------------------------

class TestParseResponse:
    def setup_method(self):
        self.na = NetAcuityXML("192.0.2.1")

    def test_single_attribute(self):
        xml = '<response country="usa"/>'
        result = self.na.parse_response(xml)
        assert result == {"country": "usa"}

    def test_multiple_attributes(self):
        xml = '<response trans-id="1" ip="192.0.2.2" country="usa" region="ca"/>'
        result = self.na.parse_response(xml)
        assert result["trans-id"] == "1"
        assert result["ip"] == "192.0.2.2"
        assert result["country"] == "usa"
        assert result["region"] == "ca"

    def test_no_attributes_returns_empty_dict(self):
        xml = "<response/>"
        result = self.na.parse_response(xml)
        assert result == {}

    def test_error_attribute_is_parsed(self):
        xml = '<response error="DB Not Loaded"/>'
        result = self.na.parse_response(xml)
        assert result.get("error") == "DB Not Loaded"

    def test_numeric_attribute_values_returned_as_strings(self):
        xml = '<response country-code="840" region-code="6"/>'
        result = self.na.parse_response(xml)
        assert result["country-code"] == "840"
        assert result["region-code"] == "6"

    def test_all_root_attributes_present(self):
        xml = '<response a="1" b="2" c="3" d="4" e="5"/>'
        result = self.na.parse_response(xml)
        assert len(result) == 5
        for key in ("a", "b", "c", "d", "e"):
            assert key in result

    def test_child_elements_are_not_included(self):
        # parse_response only reads root attributes, not child elements
        xml = '<response country="usa"><field name="city" value="denver"/></response>'
        result = self.na.parse_response(xml)
        assert "field" not in result
        assert "name" not in result
        assert result.get("country") == "usa"

    def test_realistic_geo_response(self):
        xml = (
            '<response trans-id="12345" ip="192.0.2.2" '
            'country="usa" two-letter-country="us" '
            'region="ca" city="mountain view" '
            'latitude="37.386" longitude="-122.084"/>'
        )
        result = self.na.parse_response(xml)
        assert result["country"] == "usa"
        assert result["two-letter-country"] == "us"
        assert result["latitude"] == "37.386"
        assert result["longitude"] == "-122.084"


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

class TestNetAcuityXMLConstants:
    def test_default_port_value(self):
        assert DEFAULT_PORT == 5400

    def test_default_timeout_value(self):
        assert DEFAULT_TIMEOUT_SECONDS == 2.0
