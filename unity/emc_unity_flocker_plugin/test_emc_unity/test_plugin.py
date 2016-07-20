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
"""EMC Block Device Driver for Unity."""

import os
import sys
from uuid import uuid4
import yaml
from bitmath import GiB

from emc_unity_flocker_plugin import api_factory
from flocker.node.agents.test import test_blockdevice

if os.path.basename(sys.argv[0]) == "trial":
    from eliot.twisted import redirectLogsForTrial

    redirectLogsForTrial()


def emcblockdeviceapi_for_test(cluster_id, test_case):
    """Create ``EMCUnityBlockAPI`` instance.

    :returns: A ``EMCUnityBlockAPI`` instance
    """
    config_file_path = os.environ.get('UNITY_CONFIG_FILE')
    config_file = open(config_file_path)
    # configure file parameter:
    #   [Mandatory]
    #     backend:      ``emc_unity_flocker_plugin``
    #     ip:           IP address of storage
    #     user:         User name to login storage
    #     password:     Password to login storage
    #   [Optional]
    #     storage_pools: Storage pool names which split with the comma
    #     multipath:    True to enable multipath by default
    #     proto:        iSCSI(default) or FC
    config = yaml.load(config_file.read())['dataset']

    api = api_factory(cluster_id, **config)
    test_case.addCleanup(test_blockdevice.detach_destroy_volumes, api)
    return api


class EMCUnityBlockAPIInterfaceTests(
    test_blockdevice.make_iblockdeviceapi_tests(
        blockdevice_api_factory=(
            lambda test_case: emcblockdeviceapi_for_test(
                # XXX A hack to work around the LUN name length limit. We
                # need a better way to store the cluster_id.
                unicode(uuid4()).split('-')[0],
                test_case)
        ),
        minimum_allocatable_size=int(GiB(8).to_Byte().value),
        device_allocation_unit=int(GiB(8).to_Byte().value),
        unknown_blockdevice_id_factory=lambda test: unicode(uuid4())
    )
):
    """
    Interface adherence Tests for ``BlockAPIInterface``
    """


class EMCUnityProfiledBlockAPIInterfaceTests(
    test_blockdevice.make_iprofiledblockdeviceapi_tests(
        profiled_blockdevice_api_factory=(
            lambda test_case: emcblockdeviceapi_for_test(
                # XXX A hack to work around the LUN name length limit. We
                # need a better way to store the cluster_id.
                unicode(uuid4()).split('-')[0],
                test_case)
        ),
        dataset_size=int(GiB(8).to_Byte().value))
):
    """
    Interface adherence Tests for ``ProfiledBlockAPIInterface``
    """
