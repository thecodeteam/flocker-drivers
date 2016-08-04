# Copyright (c) 2016 EMC Corporation, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from flocker import node

from emc_unity_flocker_plugin import block_device_api

DRIVER_NAME = u'emc_unity_flocker_plugin'


def api_factory(cluster_id, **kwargs):
    return block_device_api.create_driver_instance(cluster_id, **kwargs)


FLOCKER_BACKEND = node.BackendDescription(
    name=DRIVER_NAME,
    needs_reactor=False,
    needs_cluster_id=True,
    api_factory=api_factory,
    required_config={u"ip", u"user", u"password"},
    deployer_type=node.DeployerType.block)
