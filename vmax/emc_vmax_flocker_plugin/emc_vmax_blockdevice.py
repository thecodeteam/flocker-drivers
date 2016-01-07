# Copyright Hybrid Logic Ltd.
# Copyright 2015 EMC Corporation
# See LICENSE file for details.

from flocker.node.agents.blockdevice import (
    VolumeException,
    AlreadyAttachedVolume,
    UnknownVolume,
    UnattachedVolume,
    IBlockDeviceAPI,
    BlockDeviceVolume
)

import platform
from uuid import UUID
from bitmath import Byte, KiB, GiB
from subprocess import check_output, CalledProcessError, STDOUT
from zope.interface import implementer
import cinder.volume.configuration as conf
from twisted.python.filepath import FilePath
from oslo_config import cfg
from oslo_log import log as oslo_logging
from oslo_concurrency import lockutils
from distutils.spawn import find_executable

from eventlet import patcher
if not patcher.is_monkey_patched('socket'):
    from eventlet import monkey_patch
    monkey_patch(socket=True)

from cinder.volume.drivers.emc.emc_vmax_common import EMCVMAXCommon
import emc_flocker_db

CONF = cfg.CONF
LOG = oslo_logging.getLogger(__name__)


@implementer(IBlockDeviceAPI)
class EMCVmaxBlockDeviceAPI(object):
    """
    Common operations provided by all block device backends, exposed via
    asynchronous methods.
    """
    def __init__(self, cluster_id, vmax_common=None, vmax_hosts=None, compute_instance=None,
                 dbhost='localhost', lock_path='/tmp'):
        self.cluster_id = cluster_id
        self.vmax_common = vmax_common
        self.min_allocation = self.vmax_round_allocation(0)
        self.dbconn = emc_flocker_db.EmcFlockerDb(dbhost)
        self.vmax_hosts = vmax_hosts
        self.compute_instance = compute_instance
        if self.compute_instance is None:
            self.compute_instance = platform.node()
        self.volume_stats = self.vmax_common.update_volume_stats()
        if 'pools' in self.volume_stats:
            self.default_pool = self.volume_stats['pools'][0]
        else:
            self.default_pool = None
        self.lock_path = lock_path
        lockutils.set_defaults(lock_path)

    def _has_connection(self):
        has_connection = self.vmax_common.conn is not None
        LOG.info('_has_connection returns ' + unicode(self.vmax_common.conn))
        return has_connection

    def _get_volume(self, blockdevice_id):
        volume = self.dbconn.get_volume_by_uuid(blockdevice_id)
        if volume is None:
            LOG.error("_get_volume: UnknownVolume, " + unicode(blockdevice_id))
            raise UnknownVolume(unicode(blockdevice_id))

        return volume

    def _generate_host(self, host=None, backend='Backend', pool=None):
        if host is None:
            host = self.compute_instance.split('.')[0]
        if pool is None:
            if self.default_pool is not None:
                pool = self.default_pool['pool_name']
            else:
                location_info = self.volume_stats['location_info']
                pool = location_info.split('#')[1]
        return "{host}@{backend}#{pool}".format(host=host, backend=backend, pool=pool)

    @staticmethod
    def vmax_round_allocation(in_bytes):
        """
        Returns a size in bytes that is on a clean cylinder boundary.
        :param in_bytes: input size in bytes
        :return:
        """
        if in_bytes < int(GiB(1).to_Byte().value):
            in_bytes = int(GiB(1).to_Byte().value)

        boundary = int(KiB(1920).to_Byte().value)
        remainder = in_bytes % boundary
        if remainder == 0:
            round_up = in_bytes
        else:
            round_up = in_bytes + boundary - remainder

        return round_up

    def allocation_unit(self):
        """
        See ``IBlockDeviceAPI.allocation_unit``.
        :returns: ``int`` size of the
            allocation_unit.
        """
        return self.min_allocation

    def compute_instance_id(self):
        """
        See ``IBlockDeviceAPI.compute_instance_id``.
        :returns: ``unicode`` of a
            provider-specific node identifier which identifies the node where
            the method is run.
        """
        return unicode(self.compute_instance)

    def get_vmax_hosts(self):
        return self.vmax_hosts

    def get_volume_stats(self):
        self.volume_stats = self.vmax_common.update_volume_stats()
        return self.volume_stats

    def _create_vmax_vomume(self, volume):
        """

        :param volume:
        :return:
        """
        volumeSizeGB = volume['actual_size']
        volumeName = volume['id']
        extraSpecs = self.vmax_common._initial_setup(volume)
        self.vmax_common.conn = self.vmax_common._get_ecom_connection()

        if extraSpecs['isV3']:
            rc, volumeDict, storageSystemName = (
                self.vmax_common._create_v3_volume(volume, volumeName, volumeSizeGB,
                                       extraSpecs))
        else:
            rc, volumeDict, storageSystemName = (
                self.vmax_common._create_composite_volume(volume, volumeName, volumeSizeGB,
                                              extraSpecs))

        LOG.debug('_create_vmax_vomume: rc = %s, volume = %s' % (str(rc), str(volumeDict)))
        if hasattr(self.vmax_common, 'version'):
            volumeDict['version'] = self.vmax_common.version

        return volumeDict

    def create_volume(self, dataset_id, size):
        """
        See ``IBlockDeviceAPI.create_volume``.
        :returns: ``BlockDeviceVolume`` when
            the volume has been created.
        """
        volume = {'id': unicode(dataset_id),
                  'size': int(Byte(size).to_GB().value),
                  'actual_size': size,
                  'host': self._generate_host(),
                  'attach_to': None}

        provider_location = self._create_vmax_vomume(volume)

        volume['name'] = provider_location['keybindings']['DeviceID']
        volume['provider_location'] = unicode(provider_location)

        blockdevice_id = self.dbconn.add_volume(volume)
        return _blockdevicevolume_from_vmax_volume(blockdevice_id, volume)

    def destroy_volume(self, blockdevice_id):
        """
        See ``IBlockDeviceAPI.destroy_volume``.
        :return:
        """
        volume = self._get_volume(blockdevice_id)
        self.dbconn.delete_volume_by_id(blockdevice_id)
        self.vmax_common.delete_volume(volume)

    def _find_vmax_host(self, attach_to):
        connector = None
        s_attach_to = attach_to.split('.')[0]
        for host in self.vmax_hosts:
            if host['host'].lower() == s_attach_to.lower():
                connector = host
                break
        return connector

    def attach_volume(self, blockdevice_id, attach_to):
        """
        See ``IBlockDeviceAPI.attach_volume``.
        :returns:
        """
        volume = self._get_volume(blockdevice_id)

        if volume['attach_to'] is not None:
            LOG.error("attach_volume: AlreadyAttachedVolume, " + unicode(blockdevice_id))
            raise AlreadyAttachedVolume(blockdevice_id)

        connector = self._find_vmax_host(attach_to)
        if connector is None:
            LOG.error("attach_volume: VolumeException, " + unicode(blockdevice_id))
            raise VolumeException(blockdevice_id)

        LOG.info("attach_volume " + unicode(volume) + " to " + unicode(connector))

        volume['attach_to'] = unicode(attach_to)
        self.dbconn.update_volume_by_id(blockdevice_id, volume)
        self.vmax_common.initialize_connection(volume, connector)
        return _blockdevicevolume_from_vmax_volume(blockdevice_id, volume)

    def detach_volume(self, blockdevice_id):
        """
        See ``BlockDeviceAPI.detach_volume``.
        :returns:
        """
        volume = self._get_volume(blockdevice_id)
        if volume['attach_to'] is None:
            LOG.error("detach_volume: UnattachedVolume, " + unicode(blockdevice_id))
            raise UnattachedVolume(blockdevice_id)

        connector = self._find_vmax_host(volume['attach_to'])
        if connector is None:
            LOG.error("detach_volume: VolumeException, " + unicode(blockdevice_id))
            raise VolumeException(blockdevice_id)

        LOG.info("detach_volume " + unicode(volume) + " to " + unicode(connector))

        volume['attach_to'] = None
        self.dbconn.update_volume_by_id(blockdevice_id, volume)
        self.vmax_common.terminate_connection(volume, connector)

    def list_volumes(self):
        """
        See ``BlockDeviceAPI.list_volume``.
        :returns: ``list`` of
            ``BlockDeviceVolume``\ s.
        """
        block_devices = []
        for volume in self.dbconn.get_all_volumes():
            blockdevice_id = volume['uuid']
            block_devices.append(_blockdevicevolume_from_vmax_volume(blockdevice_id, volume))
        return block_devices

    def get_device_path(self, blockdevice_id):
        """
        See ``BlockDeviceAPI.get_device_path``.
        :returns: A ``Deferred`` that fires with a ``FilePath`` for the device.
        """
        volume = self._get_volume(blockdevice_id)
        symm_id = self._get_symmetrix_id()
        LOG.debug("get_device_path: bid = %s sid = %s" % (unicode(blockdevice_id), str(symm_id)))

        output = self._execute_inq()
        for line in output.splitlines():
            fields = unicode(line).split()
            if len(fields) == 4 and fields[0].startswith('/dev/') \
                    and fields[1] == symm_id and fields[2] == volume['name']:
                device_path = FilePath(fields[0])
                break
        else:
            LOG.error("get_device_path: UnattachedVolume, " + unicode(blockdevice_id))
            raise UnattachedVolume(blockdevice_id)

        return device_path

    def _get_symmetrix_id(self):
        if self.default_pool is not None:
            location_info = self.default_pool['location_info']
        else:
            location_info = self.volume_stats['location_info']
        fields = location_info.split('#')
        return fields[0]

    @staticmethod
    def _rescan_scsi_bus():
        iscsiadm_command = find_executable('iscsiadm')
        try:
            check_output([iscsiadm_command, "-m", "session", "--rescan"], stderr=STDOUT)
        except CalledProcessError as e:
            LOG.error("iscsiadm: error, %s" % str(e))

        rescan_command = find_executable('rescan-scsi-bus')
        if rescan_command is None:
            rescan_command = find_executable('rescan-scsi-bus.sh')
        try:
            check_output([rescan_command, "-r", "-l"], stderr=STDOUT)
        except CalledProcessError as e:
            LOG.error("%s: error, %s" % (rescan_command, str(e)))

    def _execute_inq(self):
        try:
            self._rescan_scsi_bus()
            output = check_output(["/usr/local/bin/inq", "-sym_wwn"], stderr=STDOUT)
        except CalledProcessError as e:
            output = unicode(e)
            LOG.error("_execute_inq: error, %s" % str(e))

        return output


def _blockdevicevolume_from_vmax_volume(blockdevice_id, volume):
    """
    :param unicode blockdevice_id: An opaque identifier for the volume
    :param volume: a VMAX device Id
    :returns: ``BlockDeviceVolume```
    """
    size = int(volume['actual_size'])
    attached_to = volume['attach_to']

    # Return a ``BlockDeviceVolume``
    return BlockDeviceVolume(blockdevice_id=blockdevice_id,
                             size=size,
                             attached_to=attached_to,
                             dataset_id=UUID(volume['id']))


def vmax_from_configuration(cluster_id=None, protocol="FC", hosts=None, compute_instance=None,
                            dbhost='localhost', lock_path='/tmp', log_file=None):
    CONF.debug = False
    CONF.verbose = False
    CONF.use_stderr = False
    try:
        if log_file is not None:
            CONF.log_file = log_file
        oslo_logging.setup(CONF, __name__)
    except:
        CONF.log_file = None
        oslo_logging.setup(CONF, __name__)
        LOG.error(unicode(log_file) + ': Failed to open, using stderr')

    try:
        vmax_common = EMCVMAXCommon(protocol, configuration=conf.Configuration(None))
    except TypeError as e:
        LOG.error(str(e))
        vmax_common = EMCVMAXCommon(protocol, '2.0.0', configuration=conf.Configuration(None))

    return EMCVmaxBlockDeviceAPI(cluster_id, vmax_common=vmax_common, vmax_hosts=hosts,
                                 compute_instance=compute_instance, dbhost=dbhost, lock_path=lock_path)
