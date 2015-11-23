# Copyright 2015 EMC Corporation

"""
EMC Test helpers for ``flocker.node.agents``.
"""

import os
import yaml
from uuid import uuid4
from emc_vmax_blockdevice import vmax_from_configuration


def _read_vmax_yaml():
    config_file_path = os.environ.get('VMAX_CONFIG_FILE')
    if config_file_path is None:
        config_file_path = "../conf/agent.yml"

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
    except Exception as e:
        print str(e.message)


def vmax_client_for_test():
    """
    Create a ``scaleiopy.scaleio.ScaleIO`` using credentials from a
    test_emc_sio.py (TODO move these to config file)

    :returns: An instance of ``scaleiopy.scaleio.ScaleIO`` authenticated
    """
    dataset = _read_vmax_yaml()
    protocol = dataset['protocol']
    min_mb = int(dataset['min_allocation'])
    hosts = dataset['hosts']
    dbhost = dataset['database']
    lock_path = dataset['lockdir']
    return vmax_from_configuration(cluster_id=unicode(uuid4()), hosts=hosts, protocol=protocol,
                                   min_allocation=min_mb, dbhost=dbhost, lock_path=lock_path)


def tidy_vmax_client_for_test(test_case):
    """
    Return a ``scaleiopy.scaleio.ScaleIO`` whose ScaleIO API is a
    wrapped by a ``TidyScaleIOVolumeManager`` and register a ``test_case``
    cleanup callback to remove any volumes that are created during each test.
    """
    client = vmax_client_for_test()
    test_case.addCleanup(_cleanup, client)
    return client
