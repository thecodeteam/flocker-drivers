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
from bitmath import Byte, MiB
from eliot import Message, Logger
from subprocess import check_output, STDOUT
from zope.interface import implementer
import vmax.cinder.configuration as conf
from twisted.python.filepath import FilePath
from oslo_concurrency import lockutils

from vmax.emc_vmax_common import EMCVMAXCommon
import emc_flocker_db

# Eliot is transitioning away from the "Logger instances all over the place"
# approach.  And it's hard to put Logger instances on PRecord subclasses which
# we have a lot of.  So just use this global logger for now.
_logger = Logger()


@implementer(IBlockDeviceAPI)
class EMCVmaxBlockDeviceAPI(object):
    """
    Common operations provided by all block device backends, exposed via
    asynchronous methods.
    """
    def __init__(self, cluster_id, vmax_common=None, vmax_hosts=None, min_allocation=1000,
                 compute_instance=None, dbhost='localhost', lock_path='/tmp'):
        self.cluster_id = cluster_id
        self.min_allocation = self._round_allocation(int(MiB(min_allocation).to_Byte().value))
        self.vmax_common = vmax_common
        self.dbhost = dbhost
        self.dbconn = emc_flocker_db.EmcFlockerDb(self.dbhost)
        self.vmax_hosts = vmax_hosts
        self.compute_instance = compute_instance
        if self.compute_instance is None:
            self.compute_instance = platform.node()
        self.volume_stats = self.vmax_common.update_volume_stats()
        self.default_pool = self.volume_stats['pools'][0]
        self.lock_path = lock_path
        lockutils.set_defaults(lock_path)

    def _has_connection(self):
        has_connection = self.vmax_common.conn is not None
        Message.new(Info="_has_connecion: " + unicode(has_connection)).write(_logger)
        return has_connection

    def _round_allocation(self, in_bytes):
        """
        Returns a size in bytes that is on a MB and cylinder boundary.

        :param in_bytes: input size in bytes
        :return:
        """
        __cylinder__ = int(MiB(15).to_Byte().value)

        factor = int(in_bytes / __cylinder__) + 1
        return factor * __cylinder__

    def _get_volume(self, blockdevice_id):
        volume = self.dbconn.get_volume_by_uuid(blockdevice_id)
        if volume is None:
            Message.new(Error="_get_volume: UnknownVolume, " + unicode(blockdevice_id)).write(_logger)
            raise UnknownVolume(unicode(blockdevice_id))

        return volume

    def _generate_host(self, host=None, backend='Backend', pool=None):
        if host is None:
            host = self.compute_instance.split('.')[0]
        if pool is None:
            pool = self.default_pool['pool_name']
        return "{host}@{backend}#{pool}".format(host=host, backend=backend, pool=pool)

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

    def create_volume(self, dataset_id, size):
        """
        See ``IBlockDeviceAPI.create_volume``.
        :returns: ``BlockDeviceVolume`` when
            the volume has been created.
        """
        volume = {'id': unicode(dataset_id),
                  'size': int(Byte(size).to_MiB().value),
                  'host': self._generate_host(),
                  'attach_to': None}
        provider_location = self.vmax_common.create_volume(volume)

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
            Message.new(Error="attach_volume: AlreadyAttachedVolume, " + unicode(blockdevice_id)).write(_logger)
            raise AlreadyAttachedVolume(blockdevice_id)

        connector = self._find_vmax_host(attach_to)
        if connector is None:
            Message.new(Error="attach_volume: VolumeException, " + unicode(blockdevice_id)).write(_logger)
            raise VolumeException(blockdevice_id)

        Message.new(Info="attach_volume " + unicode(volume) + " to " + unicode(connector))

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
            Message.new(Error="detach_volume: UnattachedVolume, " + unicode(blockdevice_id)).write(_logger)
            raise UnattachedVolume(blockdevice_id)

        connector = self._find_vmax_host(volume['attach_to'])
        if connector is None:
            Message.new(Error="detach_volume: VolumeException, " + unicode(blockdevice_id)).write(_logger)
            raise VolumeException(blockdevice_id)

        Message.new(Info="detach_volume " + unicode(volume) + " to " + unicode(connector))

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

        output = self._execute_inq()
        for line in output.splitlines():
            fields = unicode(line).split()
            if len(fields) == 4 and fields[0].startswith('/dev/') \
                    and fields[1] == symm_id and fields[2] == volume['name']:
                device_path = FilePath(fields[0])
                break
        else:
            Message.new(Error="get_device_path: UnattachedVolume, " + unicode(blockdevice_id)).write(_logger)
            raise UnattachedVolume(blockdevice_id)

        return device_path

    def _get_symmetrix_id(self):
        location_info = self.default_pool['location_info']
        fields = location_info.split('#')
        return fields[0]

    def _rescan_scsi_bus(self):
        rescan_command = '/usr/bin/rescan-scsi-bus.sh'
        iscsiadm_command = '/usr/sbin/iscsiadm'
        try:
            check_output([iscsiadm_command, "-m", "session", "--rescan"], stderr=STDOUT)
            output = check_output([rescan_command, "-r", "-l"], stderr=STDOUT)
        except Exception as e:
            output = unicode(e)

        return output

    def _execute_inq(self):
        try:
            self._rescan_scsi_bus()
            output = check_output(["/usr/local/bin/inq", "-sym_wwn"], stderr=STDOUT)
        except Exception as e:
            output = unicode(e)

        return output


def _blockdevicevolume_from_vmax_volume(blockdevice_id, volume):
    """
    :param unicode blockdevice_id: An opaque identifier for the volume
    :param volume: a VMAX device Id
    :returns: ``BlockDeviceVolume```
    """
    size = volume['size']
    attached_to = volume['attach_to']

    # Return a ``BlockDeviceVolume``
    return BlockDeviceVolume(blockdevice_id=blockdevice_id,
                             size=int(MiB(size).to_Byte().value),
                             attached_to=attached_to,
                             dataset_id=UUID(volume['id']))


def vmax_from_configuration(cluster_id=None, protocol="FC", hosts=None, min_allocation=1000, compute_instance=None,
                            dbhost='localhost', lock_path='/tmp'):
    vmax_common = EMCVMAXCommon(protocol, '0.0.1', configuration=conf.Configuration(None))
    return EMCVmaxBlockDeviceAPI(cluster_id, vmax_common=vmax_common, vmax_hosts=hosts, min_allocation=min_allocation,
                                 compute_instance=compute_instance, dbhost=dbhost, lock_path=lock_path)
