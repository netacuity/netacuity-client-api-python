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

"""Tests for netacuity/__init__.py's public API surface (``__all__``).

``from netacuity import *`` must work standalone, without anything else
having already imported the submodules first -- that requirement is why the
star-import happens here at module scope (Python only allows ``import *``
at module level) rather than inside a test function.
"""

from netacuity import *  # noqa: F401,F403 -- this is the behavior under test


def test_star_import_exposes_netacuity_xml_submodule():
    assert hasattr(netacuity_xml, "NetAcuityXML")


def test_star_import_exposes_netacuity_error():
    assert issubclass(NetAcuityError, Exception)
