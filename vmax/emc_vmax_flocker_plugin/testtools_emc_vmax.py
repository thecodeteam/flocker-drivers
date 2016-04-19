# Copyright Hybrid Logic Ltd.
# Copyright 2015 EMC Corporation
# See LICENSE file for details.

"""
EMC Test helpers for ``flocker.node.agents``.
"""

import os
import yaml
from uuid import uuid4
from bitmath import GiB
from emc_vmax_blockdevice import vmax_from_configuration, EMCVmaxBlockDeviceAPI


def _read_vmax_yaml():
    config_file_path = os.environ.get('VMAX_CONFIG_FILE')
    if config_file_path is None:
        if os.path.exists('/etc/flocker/agent.yml'):
            config_file_path = '/etc/flocker/agent.yml'
        else:
            config_file_path = '../conf/agent.yml'

    with open(config_file_path, 'r') as stream:
        vmax_conf = yaml.load(stream)
    return vmax_conf['dataset']


def _cleanup(api):
    print 'calling _cleanup method'
    try:
        blockdevices = api.list_volumes()
        for blockdevice in blockdevices:
            if blockdevice.attached_to is not None:
                print 'detach = ' + blockdevice.blockdevice_id + " from " + blockdevice.attached_to
                api.detach_volume(blockdevice.blockdevice_id)
            print 'destroy = ' + blockdevice.blockdevice_id
            api.destroy_volume(blockdevice.blockdevice_id)
        del api
    except Exception as e:
        print str(e.message)


def vmax_allocation_unit(size_in_gb):
    return EMCVmaxBlockDeviceAPI.vmax_round_allocation(int(GiB(size_in_gb).to_Byte().value))


def vmax_client_for_test():
    """
    Create a ``scaleiopy.scaleio.ScaleIO`` using credentials from a
    test_emc_sio.py (TODO move these to config file)

    :returns: An instance of ``scaleiopy.scaleio.ScaleIO`` authenticated
    """
    dataset = _read_vmax_yaml()
    config_file = dataset['config_file']
    protocol = dataset['protocol']
    hosts = dataset['hosts']
    dbhost = '%s:%s' % (dataset['database'], 'test_emc_flocker_hash')
    profiles = {}
    if 'profiles' in dataset:
        profiles = dataset['profiles']
    return vmax_from_configuration(cluster_id=unicode(uuid4()), config_file=config_file,
                                   hosts=hosts, profiles=profiles, protocol=protocol,
                                   dbhost=dbhost)


def tidy_vmax_client_for_test(test_case):
    """
    Return a ``scaleiopy.scaleio.ScaleIO`` whose ScaleIO API is a
    wrapped by a ``TidyScaleIOVolumeManager`` and register a ``test_case``
    cleanup callback to remove any volumes that are created during each test.
    """
    client = vmax_client_for_test()
    test_case.addCleanup(_cleanup, client)
    return client
