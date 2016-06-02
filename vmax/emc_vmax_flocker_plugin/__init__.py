# Copyright Hybrid Logic Ltd.
# Copyright 2015 EMC Corporation
# See LICENSE file for details.

from flocker.node import BackendDescription, DeployerType
from emc_vmax_blockdevice import vmax_from_configuration

__VERSION__ = '0.9.2'

def api_factory(cluster_id, **kwargs):
    config_file = '/etc/flocker/vmax3.conf'
    if 'config_file' in kwargs:
        config_file = kwargs['config_file']

    protocol = 'iSCSI'
    if 'protocol' in kwargs:
        protocol = kwargs['protocol']

    hosts = {}
    if 'hosts' in kwargs:
        hosts = kwargs['hosts']

    profiles = {}
    if 'profiles' in kwargs:
        profiles = kwargs['profiles']

    dbhost='localhost:emc_flocker_hash'
    if 'database' in kwargs:
        dbhost = '%s:%s' % (kwargs['database'], 'emc_flocker_hash')

    return vmax_from_configuration(cluster_id=cluster_id, config_file=config_file, protocol=protocol,
                                   hosts=hosts, profiles=profiles, dbhost=dbhost)

FLOCKER_BACKEND = BackendDescription(
    name=u"emc_vmax_flocker_plugin",  # name isn't actually used for 3rd party plugins
    needs_reactor=False, needs_cluster_id=True,
    api_factory=api_factory, deployer_type=DeployerType.block)
