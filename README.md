# NetAcuity Client API — Python

Python client library for querying the [NetAcuity](https://www.digitalelement.com/solutions/netacuity/) Server for IP geolocation and intelligence data. Supports the XML UDP query protocol.

## Requirements

- **Python** 3.8 or later
- A running **NetAcuity Server** (default port 5400, configurable).
- An **API ID** (customer-provided integer, range 0–127; default 0)

## Installation / Build

```bash
git clone https://github.com/netacuity/netacuity-client-api-python.git
cd netacuity-client-api-python
pip install .
```

## Quick Start

### XML UDP Query (recommended)

The XML UDP protocol supports multiple feature codes in a single query.

```python
import secrets
import netacuity.netacuity_xml

na = netacuity.netacuity_xml.NetAcuityXML("<server_ip>")
na.api_id = 0          # your API ID (0–127)
na.timeout_seconds = 3

try:
    xml = na.query_xml(
        "<query_ip>",
        "3,4",                              # comma-separated feature codes to query — see Feature Codes below
        secrets.randbelow(1_000_000_000),  # transaction ID, used to match responses to requests
    )
except netacuity.netacuity_xml.NetAcuityError as error:
    print("Query failed:", error)
else:
    result = na.parse_response(xml)
    for field, value in result.items():
        print(f"{field}: {value}")
```

## API Reference

The client raises `netacuity.NetAcuityError` (importable as `netacuity.NetAcuityError`, or from `netacuity.netacuity_xml`) for network failures, timeouts, and server-side error responses — catch it around `query_xml` calls.

`NetAcuityError.raw_response` holds the raw response text when a response was actually received from the server (an IP/transaction-ID mismatch, or a server-side DB error), and is `None` when no response was ever received (invalid input, timeout, network error).

### `netacuity_xml.NetAcuityXML(server, api_id=0, *, port=5400, timeout_seconds=2.0)`

XML UDP protocol client.

| Parameter | Description |
|---|---|
| `server` | NetAcuity Server IP address |
| `api_id` | Customer-assigned API ID (0–127) |
| `port` | UDP port to connect to |
| `timeout_seconds` | The socket read timeout, in seconds |

**Attributes**

- `api_id` — the API ID; assign directly to change it (e.g. `na.api_id = 5`)
- `timeout_seconds` — the socket read timeout, in seconds; assign directly to change it

**Methods**

- `query_xml(ip, feature_codes, transaction_id) -> str` — query one or more comma-separated feature codes for `ip` and return the XML response; raises `NetAcuityError` on failure
- `parse_response(xml) -> dict` — parse a response XML string into a dict of field name to value

## Feature Codes

For the complete, up-to-date list of feature codes and their response fields, see the [NetAcuity documentation](https://docs.netacuity.com/).

## Examples

Runnable examples are provided in the `examples/` directory:

```bash
# XML UDP query (comma-separated feature codes)
python examples/testNetAcuity_XML.py <server_ip> <query_ip> <feature_code(s)>
```

## Running the Tests

This project uses [pytest](https://docs.pytest.org/):

```bash
pip install .[dev]
pytest
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Support

Technical Support is only available to those under active contract with Digital Element. To contact Support, use the contact information provided at contract initiation.

- Documentation: [docs.netacuity.com](https://docs.netacuity.com/)
- Issues: [GitHub Issues](https://github.com/netacuity/netacuity-client-api-python/issues)

## License

Copyright 2026 Digital Envoy, Inc.

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full license text.

This repository contains no third-party source code or binaries, and the published `netacuity` package has no runtime dependencies — the only third-party packages referenced (pytest, setuptools) are development and build tooling, never shipped.
