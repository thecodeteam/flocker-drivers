# Copyright Hybrid Logic Ltd.
# Copyright 2015 EMC Corporation
# See LICENSE file for details.

from flocker.node.agents.blockdevice import (
    VolumeException,
    AlreadyAttachedVolume,
    UnknownVolume,
    UnattachedVolume,
    IBlockDeviceAPI,
    MandatoryProfiles,
    IProfiledBlockDeviceAPI,
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

flocker_opts = [
    cfg.StrOpt('lock_path',
               default='/tmp',
               help='Directory for lock files')
]

backend_opts = [
    cfg.StrOpt('volume_backend_name',
               default='DEFAULT',
               help='backend name'),
    cfg.StrOpt('volume_driver',
               default='cinder.volume.drivers.emc.emc_vmax_iscsi.EMCVMAXISCSIDriver',
               help='volume driver path')
]

from cinder.volume.drivers.emc.emc_vmax_common import EMCVMAXCommon
import emc_flocker_db

CONF = cfg.CONF
LOG = oslo_logging.getLogger(__name__)

PROFILES = [MandatoryProfiles.DEFAULT.name, MandatoryProfiles.GOLD.name,
            MandatoryProfiles.SILVER.name, MandatoryProfiles.BRONZE.name]

@implementer(IBlockDeviceAPI)
@implementer(IProfiledBlockDeviceAPI)
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

        self.volume_stats = {}
        self.default_pool = {}
        for profile in self.vmax_common.keys():
            self.vmax_common[profile]._initial_setup = self._initial_setup
            self.vmax_common[profile].create_volume = self._create_vmax_vomume
            self._gather_info(profile)
            self.volume_stats[profile] = self.vmax_common[profile].update_volume_stats()
            self.default_pool[profile] = None if 'pools' not in self.volume_stats[profile] \
                                            else self.volume_stats[profile]['pools'][0]

        self.lock_path = lock_path
        lockutils.set_defaults(lock_path)

    def _has_connection(self, profile=None):
        has_connection = self.vmax_common[profile].conn is not None
        LOG.debug('_has_connection() returns ' + unicode(self.vmax_common[profile].conn))
        return has_connection

    def get_profile_list(self):
        return self.vmax_common.keys()

    def _gather_info(self, profile):
        if profile not in self.vmax_common:
            LOG.error("_gather_info: VolumeException, unknown profile " + unicode(profile))
            raise VolumeException(profile)

        self.vmax_common[profile]._gather_info()

    def _get_volume(self, blockdevice_id):
        volume = self.dbconn.get_volume_by_uuid(blockdevice_id)
        if volume is None:
            LOG.error("_get_volume: UnknownVolume, " + unicode(blockdevice_id))
            raise UnknownVolume(unicode(blockdevice_id))
        LOG.debug(str(volume))
        profile = self.get_profile_list()[0] if 'PROFILE' not in volume else volume['PROFILE']
        return volume, profile

    def _generate_host(self, host=None, profile=None, backend='Backend', pool=None):
        if host is None:
            host = self.compute_instance.split('.')[0]
        if profile is None:
            profile = self.get_profile_list()[0]
        if pool is None:
            if self.default_pool[profile] is not None:
                pool = self.default_pool[profile]['pool_name']
            else:
                location_info = self.volume_stats[profile]['location_info']
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

    def _initial_setup(self, volume, volumeTypeId=None):
        """Necessary setup to accumulate the relevant information.

        The volume object has a host in which we can parse the
        config group name. The config group name is the key to our EMC
        configuration file. The emc configuration file contains pool name
        and array name which are mandatory fields.
        FastPolicy is optional.
        StripedMetaCount is an extra spec that determines whether
        the composite volume should be concatenated or striped.

        :param profile: volume frofile
        :returns: dict -- extra spec dict
        :raises: VolumeException
        """
        try:
            profile = volumeTypeId if volumeTypeId is not None else volume['PROFILE']
            common = self.vmax_common[profile]
            configurationFile = common.configuration.cinder_emc_config_file
            arrayInfo = common.utils.parse_file_to_get_array_map(configurationFile)

            pool = common._validate_pool(volume)
            LOG.debug("Pool returned is %(pool)s.", {'pool': pool})

            poolRecord = common.utils.extract_record(arrayInfo, pool)
            if not poolRecord:
                exceptionMessage = "Unable to get corresponding record for pool."
                raise VolumeException(exceptionMessage)

            common._set_ecom_credentials(poolRecord)
            isV3 = common.utils.isArrayV3(
                common.conn, poolRecord['SerialNumber'])

            if isV3:
                extraSpecs = common._set_v3_extra_specs({}, poolRecord)
            else:
                # V2 extra specs
                extraSpecs = common._set_v2_extra_specs({}, poolRecord)
        except Exception as e:
            raise VolumeException(e.message)

        return extraSpecs

    def _create_vmax_vomume(self, volume):
        """
        :param volume:
        :return:
        """
        profile = volume['PROFILE']
        self._gather_info(profile)

        volumeSizeGB = volume['actual_size']
        volumeName = volume['id']
        extraSpecs = self._initial_setup(volume)

        if extraSpecs['isV3']:
            rc, volumeDict, storageSystemName = (
                self.vmax_common[profile]._create_v3_volume(volume, volumeName, volumeSizeGB,
                                       extraSpecs))
        else:
            rc, volumeDict, storageSystemName = (
                self.vmax_common[profile]._create_composite_volume(volume, volumeName, volumeSizeGB,
                                              extraSpecs))

        LOG.debug('_create_vmax_vomume: rc = %s, volume = %s' % (str(rc), str(volumeDict)))
        if hasattr(self.vmax_common[profile], 'version'):
            volumeDict['version'] = self.vmax_common[profile].version

        return volumeDict

    def create_volume_with_profile(self, dataset_id, size, profile):
        """
        Create a volume on EBS. Store Flocker-specific
        {metadata version, cluster id, dataset id} for the volume
        as volume tag data.
        Open issues: https://clusterhq.atlassian.net/browse/FLOC-1792
        """
        if profile not in self.get_profile_list():
            LOG.error('Ignoring unknown profile name ' + unicode(profile))
            profile = self.get_profile_list()[0]

        volume = {'id': unicode(dataset_id),
                  'size': int(Byte(size).to_GB().value),
                  'actual_size': size,
                  'PROFILE': profile,
                  'volume_type_id': profile,
                  'host': self._generate_host(),
                  'attach_to': None}

        provider_location = self._create_vmax_vomume(volume)

        volume['name'] = provider_location['keybindings']['DeviceID']
        volume['provider_location'] = unicode(provider_location)

        blockdevice_id = self.dbconn.add_volume(volume)
        return _blockdevicevolume_from_vmax_volume(blockdevice_id, volume)

    def create_volume(self, dataset_id, size):
        """
        See ``IBlockDeviceAPI.create_volume``.
        :returns: ``BlockDeviceVolume`` when
            the volume has been created.
        """
        return self.create_volume_with_profile(dataset_id, size, self.get_profile_list()[0])

    def destroy_volume(self, blockdevice_id):
        """
        See ``IBlockDeviceAPI.destroy_volume``.
        :return:
        """
        volume, profile = self._get_volume(blockdevice_id)
        LOG.debug(str(volume) + ' ' + str(profile))
        self._gather_info(profile)

        self.dbconn.delete_volume_by_id(blockdevice_id)
        self.vmax_common[profile].delete_volume(volume)

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
        volume, profile = self._get_volume(blockdevice_id)

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
        self.vmax_common[profile].initialize_connection(volume, connector)
        return _blockdevicevolume_from_vmax_volume(blockdevice_id, volume)

    def detach_volume(self, blockdevice_id):
        """
        See ``BlockDeviceAPI.detach_volume``.
        :returns:
        """
        volume, profile = self._get_volume(blockdevice_id)
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
        self.vmax_common[profile].terminate_connection(volume, connector)

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
        volume, profile = self._get_volume(blockdevice_id)
        symm_id = self._get_symmetrix_id(profile=profile)
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

    def _get_symmetrix_id(self, profile=None):
        LOG.debug(str(profile) + ' ' + str(self.default_pool))
        if self.default_pool[profile] is not None:
            location_info = self.default_pool[profile]['location_info']
        else:
            location_info = self.volume_stats[profile]['location_info']
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


def vmax_from_configuration(cluster_id=None, protocol="iSCSI", hosts=None, compute_instance=None, dbhost='localhost'):
    CONF(default_config_files=['/etc/flocker/vmax3.conf'], args=[])
    CONF.register_opts(flocker_opts)
    oslo_logging.setup(CONF, __name__)
    LOG.info('Logging to ' + unicode(CONF.log_file))

    vmax_common = {}
    for backend in CONF.enabled_backends:
        CONF.register_group(cfg.OptGroup(backend))
        CONF.register_opts(backend_opts, group=backend)
        local_conf = conf.Configuration(flocker_opts, config_group=backend)
        local_conf.config_group = backend

        try:
            vmax_common[backend] = EMCVMAXCommon(protocol, configuration=local_conf)
        except TypeError as e:
            LOG.error(str(e))
            vmax_common[backend] = EMCVMAXCommon(protocol, '2.0.0', configuration=local_conf)

    return EMCVmaxBlockDeviceAPI(cluster_id, vmax_common=vmax_common, vmax_hosts=hosts,
                                 compute_instance=compute_instance, dbhost=dbhost, lock_path=CONF.get('lock_path'))
