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

import fnmatch
import logging
import platform

import bitmath
import eliot
from flocker.node.agents import blockdevice
from flocker.node.agents import loopback
from twisted.python import filepath
from zope import interface

import client as unity_client
import common
import exception
from lib.initiator import connector
import pool_scheduler as scheduler

LOG = logging.getLogger(__name__)

ALLOCATION_UNIT = bitmath.GiB(1).bytes
LUN_NAME_PREFIX = 'flocker'
MAX_RETRY_DEFAULT = 3


class EMCUnityBlockDriverLogHandler(logging.Handler):
    """Python log handler to route to Eliot logging."""

    def emit(self, record):
        """Writes log message to the stream.
        :param record: The record to be logged.
        """
        msg = self.format(record)
        eliot.Message.new(
            message_type="flocker:node:agents:blockdevice:emc_unity",
            message_level=record.levelname,
            message=msg).write()


def create_driver_instance(cluster_id, **config):
    """Instantiate a new driver instances.
    Creates a new instance with parameters passed in from the config.
    :param cluster_id: The container cluster ID.
    :param config: The driver configuration settings.
    :return: A new StorageCenterBlockDeviceAPI object.
    """
    # Configure log routing to the Flocker Eliot logging
    root_logger = logging.getLogger()
    root_logger.addHandler(EMCUnityBlockDriverLogHandler())

    log_level = config.get('DEBUG_LEVEL', logging.INFO)
    root_logger.setLevel(log_level)

    return EMCUnityBlockAPI(cluster_id, **config)


@interface.implementer(blockdevice.IBlockDeviceAPI)
@interface.implementer(blockdevice.IProfiledBlockDeviceAPI)
class EMCUnityBlockAPI(object):
    VERSION = '0.1'

    def __init__(self, cluster_id, **kwargs):
        #   [Mandatory]
        #     backend:      ``emc_unity_flocker_plugin``
        #     ip:           IP address of storage
        #     user:         User name to login storage
        #     password:     Password to login storage
        #   [Optional]
        #     storage_pools: Storage pool names which split with the comma.
        #     multipath:    True to enable multipath by default
        #     proto:        iSCSI(default) or FC
        LOG.debug('Entering EMCUnityBlockAPI.__init__')

        self.cluster_id = cluster_id
        self.hostname = unicode(platform.uname()[1])
        self.max_retries = MAX_RETRY_DEFAULT

        self.client = unity_client.UnityClient(
            ip=kwargs.get('ip'),
            username=kwargs.get('user'),
            password=kwargs.get('password'))

        self.proto = kwargs.get('proto', 'iSCSI')

        self.pool_names = kwargs.get('storage_pools')
        # Verify the configuration storage_pools
        self._get_managed_storage_pools(self.pool_names)

        multipath = kwargs.get('multipath', True)
        self.allowed_ports = None
        if self.proto == 'FC':
            self.connector = connector.LinuxFibreChannelConnector(
                self.client, multipath=multipath)
            self.allowed_ports = self.client.get_fc_targets()
        elif self.proto == 'iSCSI':
            self.connector = connector.LinuxiSCSIConnector(
                self.client, multipath=multipath)
            self.allowed_ports = self.client.get_iscsi_targets()
        else:
            raise exception.InvalidProtocol(
                message='EMCUnityBlockAPI: Invalid protocol %s.' % self.proto)

        self.scheduler = {
            'profile': scheduler.ProfileBasePoolScheduler(self.client),
            'capacity': scheduler.CapacityPoolScheduler(self.client),
        }

        LOG.info(u'Exiting EMCUnityBlockAPI.__init__')

    def allocation_unit(self):
        """
        The size in bytes up to which ``IDeployer`` will round volume
        sizes before calling ``IBlockDeviceAPI.create_volume``.

        :rtype: ``int``
        :returns: 1 GiB in bytes.
        """
        return ALLOCATION_UNIT

    def compute_instance_id(self):
        """Get the backend-specific identifier for this node.

        This will be compared against ``BlockDeviceVolume.attached_to``
        to determine which volumes are locally attached and it will be used
        with ``attach_volume`` to locally attach volumes.

        :returns: A ``unicode`` object giving a provider-specific node
            identifier which identifies the node where the method is run.
        """
        return self.hostname

    def create_volume(self, dataset_id, size):
        """Create a new volume on the array.

        :param dataset_id: The Flocker dataset ID for the volume.
        :param size: The size of the new volume in bytes.
        :return: A ``BlockDeviceVolume``
        """
        return self.create_volume_with_profile(dataset_id, size, None)

    def create_volume_with_profile(self, dataset_id, size, profile_name):
        """Create a new volume on the array.

        :param dataset_id: The Flocker dataset ID for the volume.
        :param size: The size of the new volume in bytes.
        :param profile_name: The name of the storage profile for
                             this volume.
        :return: A ``BlockDeviceVolume``
        """
        LOG.debug('Entering EMCUnityBlockAPI.create_volume_with_profile: '
                  'dataset_id=%s, size=%s, profile_name=%s',
                  dataset_id, size, profile_name)

        pools = self._get_managed_storage_pools(self.pool_names)
        if profile_name:
            filter_properties = {
                'profile_name': profile_name.upper(),
                'size': size,
            }
            pool = self.scheduler['profile'].filter_one(
                pools, filter_properties)
        else:
            filter_properties = {
                'size': size,
            }
            pool = self.scheduler['capacity'].filter_one(
                pools, filter_properties)

        volume = loopback._blockdevicevolume_from_dataset_id(
            size=size, dataset_id=dataset_id)
        volume_name = self._build_volume_name_from_blockdevice_id(
            volume.blockdevice_id)

        volume_size = self._bytes_to_gib(size)

        self.client.create_lun(pool.name, volume_name, volume_size)

        LOG.debug('Exiting EMCUnityBlockAPI.create_volume_with_profile: '
                  'pool=%s, volume_name=%s, volume_size=%s',
                  pool.name, volume_name, volume_size)

        return volume

    def destroy_volume(self, blockdevice_id):
        LOG.debug('Entering EMCUnityBlockAPI.destroy_volume: blockdevice_id=%s',
                  blockdevice_id)

        volume_name = self._build_volume_name_from_blockdevice_id(
            blockdevice_id)

        lun = self.client.get_lun(name=volume_name)
        if self.client.is_lun_destroyed(lun):
            raise blockdevice.UnknownVolume(blockdevice_id)

        lun.delete()

        LOG.debug('Exiting EMCUnityBlockAPI.destroy_volume: volume_name=%s',
                  volume_name)

    def attach_volume(self, blockdevice_id, attach_to):
        LOG.debug('Entering EMCUnityBlockAPI.attach_volume: '
                  'blockdevice_id=%s, attach_to=%s',
                  blockdevice_id, attach_to)

        volume_name = self._build_volume_name_from_blockdevice_id(
            blockdevice_id)
        lun = self.client.get_lun(name=volume_name)
        if self.client.is_lun_destroyed(lun):
            raise blockdevice.UnknownVolume(blockdevice_id)

        if self._lun_already_in_host(lun):
            raise blockdevice.AlreadyAttachedVolume(blockdevice_id)

        host_info = self._build_host_info(attach_to)
        host = self._assure_host(host_info)

        try:
            hlu = self._assure_host_access(host, lun)
        except exception.UnityAluAlreadyAttachedError:
            raise blockdevice.AlreadyAttachedVolume(blockdevice_id)

        connection_properties = self.connector.build_connection_properties(
            hlu, host=host)

        self.connector.connect_volume(connection_properties['data'])

        volume = loopback._blockdevicevolume_from_blockdevice_id(
            blockdevice_id=blockdevice_id,
            size=lun.size_total,
            attached_to=unicode(attach_to))

        LOG.debug('Exiting EMCUnityBlockAPI.attach_volume: '
                  'host=%s, volume_name=%s, volume_size=%s, hlu=%s, '
                  'target_prop=%s',
                  attach_to,
                  volume_name,
                  lun.size_total,
                  hlu,
                  connection_properties)

        return volume

    def detach_volume(self, blockdevice_id):
        LOG.debug('Entering EMCUnityBlockAPI.detach_volume: blockdevice_id=%s',
                  blockdevice_id)

        volume_name = self._build_volume_name_from_blockdevice_id(
            blockdevice_id)
        lun = self.client.get_lun(volume_name)
        if self.client.is_lun_destroyed(lun):
            raise blockdevice.UnknownVolume(blockdevice_id)

        hosts = self.client.get_host()
        for host in hosts:
            if host.has_alu(lun):
                hlu = host.get_hlu(lun)
                break
        else:
            raise blockdevice.UnattachedVolume(blockdevice_id)

        connection_properties = self.connector.build_connection_properties(
            hlu, host=host)

        self.connector.disconnect_volume(connection_properties['data'])

        host.detach_alu(lun)

        LOG.debug('Exiting EMCUnityBlockAPI.detach_volume: '
                  'host=%s, volume_name=%s, volume_id=%s, hlu=%s, '
                  'target_prop=%s',
                  host.name,
                  volume_name,
                  lun.id,
                  hlu,
                  connection_properties)

    def list_volumes(self):
        LOG.debug('Entering EMCUnityBlockAPI.list_volumes')

        volumes = []
        cluster_luns = [lun for lun in self.client.get_lun()
                        if self._is_cluster_volume(lun.name)]

        hosts = self.client.get_host()

        for index, lun in enumerate(cluster_luns):
            blockdevice_id = self._get_blockdevice_id_from_lun_name(lun.name)

            for host in hosts:
                if host.has_alu(lun):
                    attached_to = unicode(host.name)
                    break
            else:
                attached_to = None

            vol = loopback._blockdevicevolume_from_blockdevice_id(
                blockdevice_id=blockdevice_id,
                size=lun.size_total,
                attached_to=attached_to)
            LOG.info('[Volume %s]: '
                     'volume_name=%s, volume_size=%s, attach_to=%s',
                     index,
                     lun.name,
                     lun.size_total,
                     attached_to)
            volumes.append(vol)

        LOG.debug('Exiting EMCUnityBlockAPI.list_volumes')

        return volumes

    def get_device_path(self, blockdevice_id):
        LOG.debug('Entering EMCUnityBlockAPI.get_device_path: '
                  'blockdevice_id=%s', blockdevice_id)

        lun_name = self._build_volume_name_from_blockdevice_id(blockdevice_id)
        lun = self.client.get_lun(lun_name)
        if self.client.is_lun_destroyed(lun):
            raise blockdevice.UnknownVolume(blockdevice_id)

        hosts = self.client.get_host()
        for host in hosts:
            if host.has_alu(lun):
                hlu = host.get_hlu(lun)
                break
        else:
            raise blockdevice.UnattachedVolume(blockdevice_id)

        # XXX This will only operate on one of the resulting device paths.
        # /sys/class/scsi_disk/x:x:x:HLU/device/block/sdvb for example.
        connection_properties = self.connector.build_connection_properties(
            hlu, host=host)

        device_info = self.connector.get_device_info(
            connection_properties['data'])

        LOG.info('EMCUnityBlockAPI.get_device_path: device_info=%s',
                 device_info)

        LOG.debug('Exiting EMCUnityBlockAPI.get_device_path')

        return filepath.FilePath(device_info['path'])

    def _assure_host(self, host_info):
        """Assures that the host with host_info.name exists.

        If the host doesn't exist in Unity, create a new one.

        :parameter host_info: common.Host object
        :return: storops host object
        """
        host = self.client.get_host(host_info.name)
        create_initiator = False
        if not host:
            host = self.client.create_host(host_info.name)
            create_initiator = True

        # [iSCSIConnector]
        #   Auto-register initiator.
        # [FibreChannel]
        #   User has to pre-configure the zone manually
        self._register_initiator(host, host_info, create_initiator)
        return host

    def _assure_host_access(self, host, lun):
        """Assures that Flocker node is connected to the Array.

        It first registers initiators to `storage_group` then add `volume` to
        `storage_group`.

        :param storage_group: object of storops storage group to which the
                              Flocker node access is registered.
        :param lun: storops lun object.
        """
        return self.client.add_lun_to_host(host, lun)

    def _register_initiator(self, host, host_info, create_initiator):
        for initiator in host_info.initiators:
            host.add_initiator(initiator, force_create=create_initiator)

        host.update()

    def _lun_already_in_host(self, lun):
        hosts = self.client.get_host()
        for host in hosts:
            if host.has_alu(lun):
                return True
        return False

    def _build_host_info(self, host_name):
        if isinstance(self.connector, connector.LinuxiSCSIConnector):
            initiators = [self.connector.get_initiator()]
            return common.Host(name=host_name,
                               initiators=initiators,
                               initiator_type='iSCSI')
        elif isinstance(self.connector, connector.LinuxFibreChannelConnector):
            initiator = self.connector.get_initiator()
            return common.Host(name=host_name,
                               initiators=initiator,
                               initiator_type='FC')

    def _build_volume_name_from_blockdevice_id(self, blockdevice_id):
        return (
            LUN_NAME_PREFIX + '--' +
            str(self.cluster_id).split('-')[0] + '--' +
            str(blockdevice_id)
        )

    def _get_blockdevice_id_from_lun_name(self, lun_name):
        try:
            prefix, cluster_id, blockdevice_id = lun_name.rsplit('--', 2)
        except ValueError:
            return None
        # XXX This is risky, but LUN names must be <=64 characters.
        short_lun_cluster_id = str(cluster_id).split('-')[0]
        short_api_cluster_id = str(self.cluster_id).split('-')[0]
        if short_lun_cluster_id != short_api_cluster_id:
            return None
        return blockdevice_id

    def _get_managed_storage_pools(self, pool_names):
        matched_pools = set()

        # Get the real pools from the backend storage
        real_pools = set([item for item in self.client.get_pool()])

        if pool_names:
            conf_pools = set([item.strip() for item in pool_names.split(",")])

            for pool in real_pools:
                for matcher in conf_pools:
                    if fnmatch.fnmatchcase(pool.name, matcher):
                        matched_pools.add(pool)

            nonexistent_pools = real_pools.difference(matched_pools)

            if not matched_pools:
                msg = ("All the specified storage pools to be managed "
                       "do not exist. Please check your configuration "
                       "emc_nas_pool_names in manila.conf. "
                       "The available pools in the backend are %s" %
                       ",".join(real_pools))
                raise exception.InvalidParameterValue(err=msg)
            if nonexistent_pools:
                LOG.warning("The following specified storage pools "
                            "do not exist: %(unexist)s. "
                            "This host will only manage the storage "
                            "pools: %(exist)s",
                            {'unexist': ",".join(map(lambda x: x.name,
                                                 nonexistent_pools)),
                             'exist': ",".join(map(lambda x: x.name,
                                               matched_pools))})
            else:
                LOG.debug("Storage pools: %s will be managed.",
                          ",".join(map(lambda x: x.name, matched_pools)))
        else:
            LOG.debug("No storage pool is specified, so all pools "
                      "in storage system will be managed.")
            return real_pools

        return matched_pools

    def _is_cluster_volume(self, lun_name):
        blockdevice_id = self._get_blockdevice_id_from_lun_name(lun_name)

        if blockdevice_id:
            return True
        else:
            return False

    @staticmethod
    def _bytes_to_gib(size):
        """Convert size in bytes to GiB.

        :param size: The number of bytes.
        :returns: The size in gigabytes.
        """
        return int(bitmath.Byte(size).GiB.value)

    @staticmethod
    def _gib_to_bytes(size):
        """Convert size in bytes to GiB.

        :param size: The number of bytes.
        :returns: The size in gigabytes.
        """
        return int(bitmath.GiB(size).bytes)


if __name__ == '__main__':
    from twisted.internet.task import react
    from eliot.logwriter import ThreadedWriter
    from eliot import FileDestination
    import uuid

    def main(reactor):
        logWriter = ThreadedWriter(
            FileDestination(file=open("emc_midrange_driver.log", "ab")),
            reactor)

        # Manually start the service, which will add it as a
        # destination. Normally we'd register ThreadedWriter with the usual
        # Twisted Service/Application infrastructure.
        logWriter.startService()

        parameter = {
            'cluster_id': uuid.uuid4(),
            'ip': '192.168.1.58',
            'user': 'admin',
            'password': 'Password123!',
            'storage_pools': 'Manila_Pool',
            'multipath': True,
            'proto': 'iSCSI',
        }

        api = EMCUnityBlockAPI(**parameter)

        print api.list_volumes()

        volume = api.create_volume(uuid.uuid4(), 80530636800)

        print api.list_volumes()

        volume = api.attach_volume(volume.blockdevice_id, api.hostname)
        print api.list_volumes()

        device_path = api.get_device_path(volume.blockdevice_id)
        print device_path

        api.detach_volume(volume.blockdevice_id)

        api.destroy_volume(volume.blockdevice_id)

        # Manually stop the service.
        done = logWriter.stopService()
        return done

    react(main, [])
