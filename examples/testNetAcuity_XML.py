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

import netacuity.netacuity_xml
import secrets
import sys

if len(sys.argv) != 4:
    print(f"Usage: {sys.argv[0]} <server_ip> <query_ip> <comma-separated list of feature_codes>")
    sys.exit(1)

# create a NetAcuity XML object
server_ip = sys.argv[1]
query_ip = sys.argv[2]
feature_codes = sys.argv[3]
transaction_id = secrets.randbelow(1_000_000_000)
example_api_id = 77  # arbitrary identifier for this API client
timeout_seconds = 3

naobj = netacuity.netacuity_xml.NetAcuityXML(server_ip, example_api_id)
naobj.timeout_seconds = timeout_seconds

# retrieve the query
try:
    xml = naobj.query_xml(query_ip, feature_codes, transaction_id)
except netacuity.netacuity_xml.NetAcuityError as e:
    print(f"Error: {e}")
    sys.exit(3)

# move into a response dictionary. The XML API does not require the database id
# to be known
responsemap = naobj.parse_response(xml)

if "error" in responsemap:
    print(f"Error: {responsemap['error']}")
    sys.exit(3)

# List the key = value pairs
print(f"ip = {responsemap.get('ip', '')}")
print(f"trans-id = {responsemap.get('trans-id', '')}")
for field_name, field_value in responsemap.items():
    if field_name in ("ip", "trans-id"):
        continue
    print(f"{field_name} = {field_value}")
print(f"raw-response = {xml}")
