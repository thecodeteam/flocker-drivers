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
"""EMC Block Device Driver for VNX."""

import fnmatch
import logging
import platform

import bitmath
import eliot
from flocker.node.agents import blockdevice
from flocker.node.agents import loopback
from twisted.python import filepath
from zope import interface

import client as vnx_client
import common
import exception
from lib.initiator import connector
import pool_scheduler as scheduler

LOG = logging.getLogger(__name__)

ALLOCATION_UNIT = bitmath.GiB(1).bytes
LUN_NAME_PREFIX = 'flocker'
MAX_RETRY_DEFAULT = 3


class EMCVNXBlockDriverLogHandler(logging.Handler):
    """Python log handler to route to Eliot logging."""

    def emit(self, record):
        """Writes log message to the stream.
        :param record: The record to be logged.
        """
        msg = self.format(record)
        eliot.Message.new(
            message_type="flocker:node:agents:blockdevice:emc_midrange",
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
    root_logger.addHandler(EMCVNXBlockDriverLogHandler())

    log_level = config.get('DEBUG_LEVEL', logging.INFO)
    root_logger.setLevel(log_level)

    return EMCVNXBlockAPI(cluster_id, **config)


@interface.implementer(blockdevice.IBlockDeviceAPI)
@interface.implementer(blockdevice.IProfiledBlockDeviceAPI)
class EMCVNXBlockAPI(object):
    VERSION = '0.1'

    def __init__(self, cluster_id, **kwargs):
        """EMCVNXBlockAPI init.

        :param cluster_id: Flocker cluster ID
        :param kwargs:
            [Mandatory]
                ip: IP address of VNX storage
                user:         User name to login VNX storage
                password:     Password to login VNX storage
            [Optional]
                navicli_path: NaviSecCli absolute path
                navicli_security_file: Path for NaviSecCli security file
                storage_pools: Storage pool names which split with the comma
                multipath:    True to enable multipath by default
                proto:        iSCSI(default) or FC
                host_ip:      IP of Flocker agent Node.
                              It is used for iSCSI initiator auto-registration.
                              Otherwise the user has to register initiator
                              manually.
        """
        LOG.debug('Entering EMCVNXBlockAPI.__init__')

        self.cluster_id = cluster_id
        self.hostname = unicode(platform.uname()[1])
        self.client = vnx_client.VNXClient(
            ip=kwargs.get('ip'),
            username=kwargs.get('user'),
            password=kwargs.get('password'),
            naviseccli=kwargs.get('navicli_path', None),
            sec_file=kwargs.get('navicli_security_file', None))

        self.proto = kwargs.get('proto', 'iSCSI')
        self.host_ip = kwargs.get('host_ip', None)
        self.max_retries = MAX_RETRY_DEFAULT

        # Only support non profile-base volume creation
        self.scheduler = scheduler.CapacityPoolScheduler(self.client)

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
                message='EMCVNXBlockAPI: Invalid protocol %s.' % self.proto)

        LOG.debug('Exiting EMCVNXBlockAPI.__init__')

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
        LOG.debug('Entering EMCVNXBlockAPI.create_volume_with_profile: '
                  'dataset_id=%s, size=%s, profile_name',
                  dataset_id, size, profile_name)

        # For VNX, only CapacityPoolScheduler is used to get a pool which
        # has the biggest capacity.
        pools = self._get_managed_storage_pools(self.pool_names)
        filter_properties = {
            'size': size,
        }
        pool = self.scheduler.filter_one(pools, filter_properties)

        volume = loopback._blockdevicevolume_from_dataset_id(
            size=size, dataset_id=dataset_id)
        volume_name = self._build_volume_name_from_blockdevice_id(
            volume.blockdevice_id)

        volume_size = self._bytes_to_gib(size)

        self.client.create_lun(pool.name, volume_name, volume_size)

        LOG.debug('Exiting EMCVNXBlockAPI.create_volume_with_profile: '
                  'pool=%s, volume_name=%s, volume_size=%s',
                  pool.name, volume_name, volume_size)

        return volume

    def destroy_volume(self, blockdevice_id):
        LOG.debug('Entering EMCVNXBlockAPI.destroy_volume: blockdevice_id=%s',
                  blockdevice_id)

        volume_name = self._build_volume_name_from_blockdevice_id(
            blockdevice_id)

        lun = self.client.get_lun(name=volume_name)
        if self.client.is_lun_destroyed(lun):
            raise blockdevice.UnknownVolume(blockdevice_id)

        lun.delete()

        LOG.debug('Exiting EMCVNXBlockAPI.destroy_volume: volume_name=%s',
                  volume_name)

    def attach_volume(self, blockdevice_id, attach_to):
        LOG.debug('Entering EMCVNXBlockAPI.attach_volume: '
                  'blockdevice_id=%s, attach_to=%s',
                  blockdevice_id, attach_to)

        volume_name = self._build_volume_name_from_blockdevice_id(
            blockdevice_id)
        lun = self.client.get_lun(name=volume_name)
        if self.client.is_lun_destroyed(lun):
            raise blockdevice.UnknownVolume(blockdevice_id)

        if self._lun_already_in_sg(lun):
            raise blockdevice.AlreadyAttachedVolume(blockdevice_id)

        host_info = self._build_host_info(self.host_ip, attach_to)
        storage_group = self._assure_storage_group(host_info)

        try:
            hlu = self._assure_host_access(storage_group, lun)
        except exception.VNXAluAlreadyAttachedError:
            raise blockdevice.AlreadyAttachedVolume(blockdevice_id)

        connection_properties = self.connector.build_connection_properties(
            hlu, storage_group=storage_group)

        self.connector.connect_volume(connection_properties['data'])

        volume_size = self._gib_to_bytes(lun.total_capacity_gb)
        volume = loopback._blockdevicevolume_from_blockdevice_id(
            blockdevice_id=blockdevice_id,
            size=volume_size,
            attached_to=unicode(attach_to))

        LOG.debug('Exiting EMCVNXBlockAPI.attach_volume: '
                  'storage_group=%s, volume_name=%s, volume_size=%s, hlu=%s, '
                  'target_prop=%s',
                  attach_to,
                  volume_name,
                  volume_size,
                  hlu,
                  connection_properties)

        return volume

    def detach_volume(self, blockdevice_id):
        LOG.debug('Entering EMCVNXBlockAPI.detach_volume: blockdevice_id=%s',
                  blockdevice_id)

        volume_name = self._build_volume_name_from_blockdevice_id(
            blockdevice_id)
        lun = self.client.get_lun(volume_name)
        if self.client.is_lun_destroyed(lun):
            raise blockdevice.UnknownVolume(blockdevice_id)

        storage_groups = self.client.get_storage_group()

        for storage_group in storage_groups:
            if storage_group.has_alu(lun):
                hlu = storage_group.get_hlu(lun)
                break
        else:
            raise blockdevice.UnattachedVolume(blockdevice_id)

        connection_properties = self.connector.build_connection_properties(
            hlu, storage_group=storage_group)

        self.connector.disconnect_volume(connection_properties['data'])

        storage_group.detach_alu(lun)

        LOG.debug('Exiting EMCVNXBlockAPI.detach_volume: '
                  'storage_group=%s, volume_name=%s, volume_id=%s, hlu=%s, '
                  'target_prop=%s',
                  storage_group.name,
                  volume_name,
                  lun.lun_id,
                  hlu,
                  connection_properties)

    def list_volumes(self):
        LOG.debug('Entering EMCVNXBlockAPI.list_volumes')

        volumes = []
        cluster_luns = [lun for lun in self.client.get_lun()
                        if self._is_cluster_volume(lun.name) and
                        not self.client.is_lun_destroyed(lun)]

        storage_groups = self.client.get_storage_group()

        for index, lun in enumerate(cluster_luns):
            blockdevice_id = self._get_blockdevice_id_from_lun_name(lun.name)

            for storage_group in storage_groups:
                if storage_group.has_alu(lun):
                    attached_to = unicode(storage_group.name)
                    break
            else:
                attached_to = None

            volume_size = self._gib_to_bytes(lun.total_capacity_gb)

            vol = loopback._blockdevicevolume_from_blockdevice_id(
                blockdevice_id=blockdevice_id,
                size=volume_size,
                attached_to=attached_to)
            LOG.info('[Volume %s]: '
                     'volume_name=%s, volume_size=%s, attach_to=%s',
                     index,
                     lun.name,
                     volume_size,
                     attached_to)
            volumes.append(vol)

        LOG.debug('Exiting EMCVNXBlockAPI.list_volumes')

        return volumes

    def get_device_path(self, blockdevice_id):
        LOG.debug('Entering EMCVNXBlockAPI.get_device_path blockdevice_id=%s',
                  blockdevice_id)

        lun_name = self._build_volume_name_from_blockdevice_id(blockdevice_id)
        lun = self.client.get_lun(lun_name)
        if self.client.is_lun_destroyed(lun):
            raise blockdevice.UnknownVolume(blockdevice_id)

        storage_groups = self.client.get_storage_group()
        for storage_group in storage_groups:
            if storage_group.has_alu(lun):
                hlu = storage_group.get_hlu(lun)
                break
        else:
            raise blockdevice.UnattachedVolume(blockdevice_id)

        # XXX This will only operate on one of the resulting device paths.
        # /sys/class/scsi_disk/x:x:x:HLU/device/block/sdvb for example.
        connection_properties = self.connector.build_connection_properties(
            hlu, storage_group=storage_group)

        device_info = self.connector.get_device_info(
            connection_properties['data'])

        LOG.info('Exiting EMCVNXBlockAPI.get_device_path device_info=%s',
                 device_info)

        return filepath.FilePath(device_info['path'])

    def _build_host_info(self, host_ip, host_name):
        if isinstance(self.connector, connector.LinuxiSCSIConnector):
            initiators = [self.connector.get_initiator()]
            return common.Host(name=host_name,
                               ip=host_ip,
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
        # XXX This is risky, but VNX LUN names must be <=64 characters.
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

    def _assure_storage_group(self, host_info):
        """Assures that the storage group with host_info.name exists.

        If the storage group doesn't exist, create a new one.

        :parameter host_info: common.Host object
        :return: storage group
        """
        sg = self.client.get_storage_group(host_info.name)
        if not sg.existed:
            sg = self.client.create_storage_group(host_info.name)

            # [iSCSIConnector]
            #   auto-register initiator if host_ip is set in agent.yml.
            #   Otherwise user has to create initiator in VNX manually
            # [FibreChannel]
            #   User has to pre-configure the zone manually
            if host_info.initiator_type == 'iSCSI':
                if not host_info.ip:
                    LOG.info('Register host %s to VNX. Before that, the user '
                             'has to create initiator in VNX first.',
                             host_info.to_dict())
                    sg.connect_host(host_info.name)
                else:
                    LOG.info('Auto register host initiator to VNX. '
                             'Host info is %s', host_info.to_dict())
                    self._auto_register_initiator(sg, host_info)
        return sg

    def _assure_host_access(self, storage_group, lun):
        """Assures that Flocker node is connected to the Array.

        It first registers initiators to `storage_group` then add `volume` to
        `storage_group`.

        :param storage_group: object of storops storage group to which the
                              Flocker node access is registered.
        :param lun: storops lun object.
        """
        return self.client.add_lun_to_sg(storage_group, lun, self.max_retries)

    def _auto_register_initiator(self, storage_group, host_info):
        host_initiators = set(host_info.initiators)
        sg_initiators = set(storage_group.initiator_uid_list)

        unreg_initiators = host_initiators - sg_initiators
        initiator_port_map = {unreg_id: set(self.allowed_ports)
                              for unreg_id in unreg_initiators}

        self.client.register_initiator(
            storage_group, host_info, initiator_port_map)

    def _lun_already_in_sg(self, lun):
        storage_groups = self.client.get_storage_group()
        for storage_group in storage_groups:
            if storage_group.has_alu(lun):
                return True

        return False


BACKEND = {'vnx': EMCVNXBlockAPI}

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
            'host_ip': '192.168.21.237',
        }

        api = EMCVNXBlockAPI(**parameter)

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
