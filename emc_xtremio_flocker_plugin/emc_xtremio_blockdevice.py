# Copyright (c) 2015 -  EMC Corporation - Hybrid Logic Ltd
# See LICENSE file for details.

from blockdevice import VolumeException
from blockdevice import AlreadyAttachedVolume
from blockdevice import UnknownVolume
from blockdevice import UnattachedVolume
from blockdevice import IBlockDeviceAPI
from blockdevice import _blockdevicevolume_from_dataset_id
from blockdevice import _blockdevicevolume_from_blockdevice_id

from eliot import Message, Logger
from twisted.python.filepath import FilePath
from zope.interface import implementer
from subprocess import check_output

import base64
import urllib
import urllib2
import json
import os
import re
import socket
import pdb


class ArrayConfiguration(object):
    """
    """

    def __init__(self, login, password, host):
        self.array_login = login
        self.array_password = password
        self.array_host = host


INITIATOR_FILE = "/etc/iscsi/initiatorname.iscsi"


class VolumeStatus:
    CREATED_UNATTACHED = 1
    CREATED_ATTACHED = 2
    DESTROYED = 3

    def __init__(self):
        pass


class VolumeExists(VolumeException):
    """
    Request for creation of an existing volume
    """


class VolumeAttached(VolumeException):
    """
    Attempting to destroy an attached volume
    """


class InvalidVolumeMetadata(VolumeException):
    """
    Volume queried or supplied has invalid data
    """


class VolumeBackendAPIException(Exception):
    """
    Exception from backed mgmt server
    """


class DeviceException(Exception):
    """
    A base class for exceptions raised by  ``IBlockDeviceAPI`` operations.
    Due to backend device configuration

    :param ArrayConfiguration configuration: The configuration related to backend device.
    """

    def __init__(self, configuration):
        if not isinstance(configuration, ArrayConfiguration):
            raise TypeError(
                'Unexpected configuration type. '
                'Expected ArrayConfiguration. '
                'Got {!r}.'.format(AttributeError)
            )
        Exception.__init__(self, configuration)


class DeviceVersionMismatch(DeviceException):
    """
    The version of device not supported.
    """


class DeviceExceptionObjNotFound(Exception):
    """
    The Object not found on device
    """

# Eliot is transitioning away from the "Logger instances all over the place"
# approach.  And it's hard to put Logger instances on PRecord subclasses which
# we have a lot of.  So just use this global logger for now.
_logger = Logger()


class XtremIOMgmt():
    """
    EMC XtremIO exposes management interface through XMS. This class abstracts all REST calls to be
    used by iSCSI class and the main driver class
    """

    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"

    VOL_FLOCKER = "VOL_FLOCKER"
    VOLUME_FOLDERS = "volume-folders"

    CAPTION = 'caption'
    PARENT_FOLDER_ID = 'parent-folder-id'
    BASE_PATH = '/'

    def __init__(self, configuration):

        """
        :param configuration: ArrayConfiguration, which includes Management interface hostname, username & password
        the iSCSI data address (target)
        """
        self.base64_auth = (base64.encodestring('%s:%s' %
                                                (configuration.array_login,
                                                 configuration.array_password))
                            .replace('\n', ''))
        self.base_url = ('https://%s/api/json/types' %
                         configuration.array_host)

    def request(self, object_type='volumes', request_typ='GET', data=None,
                name=None, idx=None):
        """
        :param object_type: Type of object - volumes, initiator, lun maps. Refer to EMC XtremIO REST interface guide
         for more details.
        :param request_typ: Type of request - GET, POST, DELETE
        :param data: Raw data to be passed with request, if any
        :param name: Parameter to the request
        :param idx: If not name, then index of the object at EMC XtremIO
        :return: REST Response
        """

        if name and idx:
            Message.new("Request can't handle both name and index")
            raise ValueError("can't handle both name and idx")

        url = '%s/%s' % (self.base_url, object_type)
        key = None
        if name:
            url = '%s?%s' % (url, urllib.urlencode({'name': name}))
            key = name
        elif idx:
            url = '%s/%d' % (url, idx)
            key = str(idx)
        if data and request_typ == 'GET':
            url + '?' + urllib.urlencode(data)
            request = urllib2.Request(url)
        elif data:
            Message.new(data=json.dumps(data)).write(_logger)
            request = urllib2.Request(url, json.dumps(data))
        else:
            request = urllib2.Request(url)
        Message.new(url=url).write(_logger)
        request.get_method = lambda: request_typ
        request.add_header("Authorization", "Basic %s" % (self.base64_auth,))
        try:
            response = urllib2.urlopen(request)
        except (urllib2.HTTPError) as exc:
            if exc.code == 400 and hasattr(exc, 'read'):
                error = json.load(exc)
                if error['message'].endswith('obj_not_found'):
                    Message.new(object_key=key + "of type").write(_logger)
                    Message.new(object_type=object_type + " is not found").write(_logger)
                    raise DeviceExceptionObjNotFound(Exception)
                elif error['message'] == 'vol_obj_name_not_unique':
                    Message.new(error="can't create 2 volumes with the same name").write(_logger)
                    raise (InvalidVolumeMetadata('Volume by this name already exists'))
	        raise
        if response.code >= 300:
            Message.new(Error=response.msg).write(_logger)
            raise VolumeBackendAPIException(
                data='bad response from XMS got http code %d, %s' %
                     (response.code, response.msg))
        str_result = response.read()
        if str_result:
            try:
                return json.loads(str_result)
            except Exception:
                Message.new(value="EMCXtremIOBlockDeviceAPI:XtremIOMgmt:" +
                                  "quering" + object_type + "type" +
                                  request_typ + "failed to parse result" +
                                  "return value" + str_result).write(_logger)


class XtremIOiSCSIDriver():
    """Executes commands relating to ISCSI volumes.

    We make use of model provider properties as follows:
    ``provider_auth``
      if present, contains a space-separated triple:
      '<auth method> <auth username> <auth password>'.
      `CHAP` is the only auth_method in use at the moment.
    """

    def __init__(self, mgmt, compute_instance_id):
        """
        :param: mgmt - The EMC XtremIO XMS (management interface object)
        """

        self.mgmt = mgmt
        self._connector = {'initiator': None, 'ig': compute_instance_id}

    def initialize_connection(self):
        """
        The model followed with EMC XtremIO can be explained as follows:
        Each node has a initiator group created, when logged in for the first time. To this initiator group
        the initiator name is added for all the interfaces available on the node. The volumes are associated with
        the initiator group, thus making sure multipathing is established automatically.
        """

        sys = self.mgmt.request('clusters', 'GET', idx=1)['content']
        use_chap = (sys.get('chap-authentication-mode', 'disabled') !=
                    'disabled')
        dicovery_chap = (sys.get('chap-discovery-mode', 'disabled') !=
                         'disabled')
        initiator = self._get_initiator()
        try:
            # check if the IG already exists
            self.mgmt.request('initiator-groups', 'GET',
                              name=self._get_ig())['content']
        except DeviceExceptionObjNotFound:
            # create an initiator group to hold the the initiator
            data = {'ig-name': self._get_ig()}
            self.mgmt.request('initiator-groups', 'POST', data)
        try:
            init = self.mgmt.request('initiators', 'GET',
                                     name=initiator)['content']
            if use_chap:
                chap_passwd = init['chap-authentication-initiator-'
                                   'password']
                # delete the initiator to create a new one with password
                if not chap_passwd:
                    Message.new(Info='initiator has no password while using chap removing it')
                    self.mgmt.request('initiators', 'DELETE', name=initiator)
                    # check if the initiator already exists
                    raise DeviceExceptionObjNotFound
        except DeviceExceptionObjNotFound:
            # create an initiator
            data = {'initiator-name': initiator,
                    'ig-id': self._get_ig(),
                    'port-address': initiator}
            if use_chap:
                data['initiator-authentication-user-name'] = 'chap_user'
                chap_passwd = self._get_password()
                data['initiator-authentication-password'] = chap_passwd
            if dicovery_chap:
                data['initiator-discovery-user-name'] = 'chap_user'
                data['initiator-discovery-'
                     'password'] = self._get_password()
            self.mgmt.request('initiators', 'POST', data)

    def create_lun_map(self, blockdevice_id, compute_instance_id):
        """
        :param: volume id or blockdevice_id passed from flocker
        :param: hostname, we use hostname as initiator group's name. If hostname is not current host, things won't
        break
        """
        try:
            self.mgmt.request('lun-maps', 'POST', {'ig-id': compute_instance_id,
                                                   "vol-id": str(blockdevice_id)})
        except DeviceExceptionObjNotFound:
            Message.new(Error="Could not attach volume"
                              + str(blockdevice_id)
                              + "for node " + str(compute_instance_id)).write(_logger)
            raise UnknownVolume(blockdevice_id)

    def destroy_lun_map(self, blockdevice_id, compute_instance_id):
        """
        :param: volumeid or blockdevice_id passed from flocker
        :param: hostname used to identify initiator group
        """
        try:
            ig = self.mgmt.request('initiator-groups', name=compute_instance_id)['content']
            tg = self.mgmt.request('target-groups', name="Default")['content']
            vol = self.mgmt.request('volumes', name=str(blockdevice_id))['content']
            lm_name = '%s_%s_%s' % (str(vol['index']),
                                    str(ig['index']) if ig else 'any', str(tg['index']))
            Message.new(lm_name=lm_name).write(_logger)
            self.mgmt.request('lun-maps', 'DELETE', name=lm_name)
        except DeviceExceptionObjNotFound:
            Message.new(Error="destroy_lun_map: object not found for"
                              + str(blockdevice_id) + "when mapped to "
                              + str(compute_instance_id)).write(_logger)
            raise UnknownVolume(blockdevice_id)

    def get_lun_map(self, blockdevice_id):
        """
        :param blockdevice_id: Volume id
        :return:
        """
        try:
            vol = self.mgmt.request('volumes', name=str(blockdevice_id))['content']
            if int(vol['num-of-lun-mappings']) == 0:
                raise UnattachedVolume(blockdevice_id)
            else:
                lun_mapping_list = vol['lun-mapping-list']
                return lun_mapping_list[0][2]
        except DeviceExceptionObjNotFound:
            Message.new(Error="get_lun_map: could not be found for"
                              + str(blockdevice_id)).write(_logger)


    def rescan_scsi(self):
        """
        Rescan SCSI bus. This is needed in situations:
            - Resize of volumes
            - Detach of volumes
            - Possibly creation of new volumes
        :return:none
        """
        channel_number = self._get_channel_number()
        ## Check for error condition
        if channel_number < 0:
            Message.new(error="iSCSI login not done for XtremIO bailing out").write(_logger)
            raise DeviceException
        else:
            check_output(["rescan-scsi-bus", "-r", "-c", channel_number])

    def _get_channel_number(self):
        """
        Query scsi to get channel number of XtremIO devices.
        Right now it supports only one XtremIO connected array
        :return: channel number
        """
        output = check_output([b"/usr/bin/lsscsi"])
        # lsscsi gives output in the following form:
        # [0:0:0:0]    disk    ATA      ST91000640NS     SN03  /dev/sdp
        # [1:0:0:0]    disk    DGC      LUNZ             0532  /dev/sdb
        # [1:0:1:0]    disk    DGC      LUNZ             0532  /dev/sdc
        # [8:0:0:0]    disk    MSFT     Virtual HD       6.3   /dev/sdd
        # [9:0:0:0]    disk XtremIO  XtremApp         2400     /dev/sde

        # We shall parse the output above and to give out channel number
        # as 9
        for row in output.split('\n'):
           if re.search(r'XtremApp', row, re.I):
            channel_row = re.search('\d+', row)
            if channel_row:
                channel_number = channel_row.group()
                return channel_number

        ## Did not find channel number of xtremIO
        ## The number cannot be negative
        return -1

    def _get_initiator(self):
        """
        Initiator name of the current host
        """
        if self._connector['initiator'] is not None:
            return self._connector
        else:
            # TODO there couldbe multiple interfaces
            iscsin = os.popen('cat %s' % INITIATOR_FILE).read()
            match = re.search('InitiatorName=.*', iscsin)
            if len(match.group(0)) > 13:
                self._connector['initiator'] = match.group(0)[14:]
        return self._connector['initiator']

    def _get_ig(self):
        """
        Initiator group name on XtremIO
        """
        return self._connector['ig']

    def _get_password(self):
        """
        :return: Returns chap password
        """
        return 'password'


@implementer(IBlockDeviceAPI)
class EMCXtremIOBlockDeviceAPI(object):
    """
    A simulated ``IBlockDeviceAPI`` which creates volumes (devices) with EMC XtremIO Flash array.
    """

    VERSION = '0.1'
    driver_name = 'XtremIO'
    MIN_XMS_VERSION = [2, 4, 0]

    def __init__(self, configuration, cluster_id, compute_instance_id=socket.gethostname(), allocation_unit=None):
        """

       :param configuration: Arrayconfiguration
       """
        self._cluster_id = cluster_id
        self._compute_instance_id = compute_instance_id
        self.volume_list = {}
        if allocation_unit is None:
            allocation_unit = 1
        self._allocation_unit = allocation_unit
        self.mgmt = XtremIOMgmt(configuration)
        self.data = XtremIOiSCSIDriver(self.mgmt, self._compute_instance_id)
        self._initialize_setup()

    def _check_for_volume_folder(self):

        """
        :param: the flocker dataset_id
        :return: True if volume folder exists. For each dataset_id a new volume is created.
        """
        try:
           vol_folders = self.mgmt.request(XtremIOMgmt.VOLUME_FOLDERS)
           vol_folder = vol_folders['folders']
           Message.new(folders=vol_folder).write(_logger)
           for folder in vol_folder:
               Message.new(folder_name=folder['name']).write(_logger)
               ## Folder name comes with a "/" as absolute path
               if folder['name'] == (str(XtremIOMgmt.BASE_PATH) + str(self._cluster_id)):
                   Message.new(Debug="Volume folder found").write(_logger)
                   return True

        except DeviceExceptionObjNotFound as exc:
            Message.new(value="Volume folder not found").write(_logger)
        except:
            Message.new(value="All Exception caught").write(_logger)

        return  False

    def _create_volume_folder(self):

        """
        :param: the flocker dataset_id
        """
        try:
            data = {self.mgmt.CAPTION: str(self._cluster_id),
                    self.mgmt.PARENT_FOLDER_ID: self.mgmt.BASE_PATH}
            self.mgmt.request(self.mgmt.VOLUME_FOLDERS, self.mgmt.POST, data)
        except DeviceExceptionObjNotFound as exe:
            #Message.new(Error="Failed to create volume folder").write(_logger)
            raise exe

    def _check_version(self):

        """
        Checks version of EMC XtremIO
        """
        sys = self.mgmt.request('clusters', idx=1)['content']
        ver = [int(n) for n in sys['sys-sw-version'].split('-')[0].split('.')]
        if ver < self.MIN_XMS_VERSION:
            Message.new(Error='Invalid XtremIO version ' + sys['sys-sw-version'])
            raise (DeviceVersionMismatch
                   ('Invalid XtremIO version, version 2.4 or up is required'))
        else:
            msg = "EMCXtremIO SW version " + sys['sys-sw-version']
            Message.new(version=msg).write(_logger)

    def _convert_size(self, size, to='BYTES'):
        """
        :param size: size to convert to or from
        :param to: type of coversion
        :return: converted size
        """
        if to == 'MB':
            size = (size / 1048576)
        else:
            size *= 1024

        return size

    def _get(self, blockdevice_id):
        """
        :param blockdevice_id: - volume id
        :return:
        """
        try:
            volume = self.volume_list[str(blockdevice_id)]
            if volume is not None:
                return volume
            else:
                raise UnknownVolume(blockdevice_id)
        except:
            raise UnknownVolume(blockdevice_id)

    def _get_vol_details(self, blockdevice_id):
        """
        :param blockdevice_id - volume id
        :return:volume details
        """
        try:
            vol = self.mgmt.request('volumes', 'GET', name=blockdevice_id)
            vol_content = vol['content']

            if int(vol_content['num-of-lun-mappings']) == 0:
                is_attached_to = None
            else:
                is_attached_to = unicode(vol_content['lun-mapping-list'][0][0][1])

            volume = _blockdevicevolume_from_blockdevice_id(
                blockdevice_id=blockdevice_id,
                size=self._convert_size(int(vol_content['vol-size'])),
                attached_to=is_attached_to
            )
            return volume
        except DeviceExceptionObjNotFound as exc:
            #Message.new(Error=exc).write(_logger)
            raise UnknownVolume(blockdevice_id)

    def compute_instance_id(self):
        """
        :return:
        """
        return self._compute_instance_id

    def _initialize_setup(self):
        """
        Initialize setup with EMC XtremIO
        - Check of the right version
        - Create Initiator group for the current host
        """

        try:
            self._check_version()
            self.data.initialize_connection()
            if not self._check_for_volume_folder():
                self._create_volume_folder()
        except DeviceVersionMismatch as exc:
            #Message.new(Error=exc).write(_logger)
            raise
        except """catch all other exception""":
            Message.new(Error="Unknown Exception occurred in last call")

    def allocation_unit(self):
        """
        Return allocation unit
        """
        return self._allocation_unit

    def create_volume(self, dataset_id, size):
        """
        Create a volume of specified size on the EMC XtremeIO Array.
        The size shall be rounded off to 1BM, as EMC XtremeIO creates
        volumes of these sizes.

        See ``IBlockDeviceAPI.create_volume`` for parameter and return type
        documentation.
        """
        if not self._check_for_volume_folder():
            self._create_volume_folder()

        # Round up to 1MB boundaries
        size_mb = self._convert_size(size, 'MB')

        volume = _blockdevicevolume_from_dataset_id(
            size=size, dataset_id=dataset_id,
        )
        data = {'vol-name': str(volume.blockdevice_id),
                'vol-size': str(size_mb) + 'm',
                'parent-folder-id': XtremIOMgmt.BASE_PATH + str(self._cluster_id)}
        self.mgmt.request('volumes', 'POST', data)
        self.volume_list[str(volume.blockdevice_id)] = volume
        return volume

    def destroy_volume(self, blockdevice_id):
        """
        Destroy the storage for the given unattached volume.
        :param: blockdevice_id - the volume id
        :raise: UnknownVolume is not found
        """
        try:
            Message.new(Info="Destroying Volume" + str(blockdevice_id)).write(_logger)
            self.mgmt.request('volumes', 'DELETE', name=blockdevice_id)
        except DeviceExceptionObjNotFound as exc:
            #Message.new(Error=exc).write(_logger)
            raise UnknownVolume(blockdevice_id)

    def attach_volume(self, blockdevice_id, attach_to):
        """
        Attach volume associates a volume with to a initiator group. The resultant of this is a
        LUN - Logical Unit Number. This association can be made to any number of initiator groups. Post of this
        attachment, the device shall appear in /dev/sd<1>.
        See ``IBlockDeviceAPI.attach_volume`` for parameter and return type
        documentation.
        """

        volume = self._get_vol_details(blockdevice_id)

        if volume.attached_to is None:
            self.data.create_lun_map(str(blockdevice_id), str(attach_to))
        else:
            raise AlreadyAttachedVolume(blockdevice_id)

        attached_volume = volume.set(attached_to=unicode(attach_to))
        self.volume_list[str(blockdevice_id)] = attached_volume
        Message.new(attached_to=attached_volume.attached_to).write(_logger)
        self.data.rescan_scsi()
        return attached_volume

    def resize_volume(self, blockdevice_id, size):
        """
        Change the size of the EMX XtremIO device.
        This implementation is limited to being able to resize volumes only if
        they are unattached.
        """
        # Raise unknown volume
        volume = self._get_vol_details(blockdevice_id)

        # Round up to 1MB boundaries
        size_mb = self._convert_size(size, 'MB')

        data = {
            'vol-size': str(size_mb) + 'm'
        }

        self.mgmt.request('volumes', 'PUT', data, name=str(volume.blockdevice_id))
        self.data.rescan_scsi()

    def detach_volume(self, blockdevice_id):
        """
        :param: volume id = blockdevice_id
        :raises: unknownvolume exception if not found
        """
        vol = self._get_vol_details(blockdevice_id)
        if vol.attached_to is not None:
            self.data.destroy_lun_map(blockdevice_id, self._compute_instance_id)
            self.data.rescan_scsi()
        else:
            Message.new(Info="Volume" + blockdevice_id + "not attached").write(_logger)
            raise UnattachedVolume(blockdevice_id)

    def list_volumes(self):
        """
        Return ``BlockDeviceVolume`` instances for all the files in the
        ``unattached`` directory and all per-host directories.

        See ``IBlockDeviceAPI.list_volumes`` for parameter and return type
        documentation.
        """
        volumes = []
        try:
            ## Query for volume folder by name VOL_FLOCKER
            ## and get list of volumes. The array may have
            ## other volumes not owned by Flocker
            vol_folder = self.mgmt.request(XtremIOMgmt.VOLUME_FOLDERS,
                                           name=XtremIOMgmt.BASE_PATH + str(self._cluster_id))['content']
            ## Get the number of volumes
            Message.new(NoOfVolumesFound=vol_folder['num-of-vols']).write(_logger)
            if int(vol_folder['num-of-vols']) > 0:
                for vol in vol_folder['direct-list']:
                    #Message.new(VolumeName=vol[1]).write(_logger)
                    volume = self._get_vol_details(vol[1])
                    volumes.append(volume)
                    #Message.new(volume=volume).write(_logger)
        except Exception as exe:
            pass
            #Message.new(Error=exe).write(_logger)

        return volumes

    def get_device_path(self, blockdevice_id):
        """
        :param blockdevice_id:
        :return:the device path
        """
        # Query LunID from XtremIO
        lunid = self.data.get_lun_map(blockdevice_id)
        output = check_output([b"/usr/bin/lsscsi"])
        # lsscsi gives output in the following form:
        # [0:0:0:0]    disk    ATA      ST91000640NS     SN03  /dev/sdp
        # [1:0:0:0]    disk    DGC      LUNZ             0532  /dev/sdb
        # [1:0:1:0]    disk    DGC      LUNZ             0532  /dev/sdc
        # [8:0:0:0]    disk    MSFT     Virtual HD       6.3   /dev/sdd
        # [9:0:0:0]    disk XtremIO  XtremApp         2400     /dev/sde

        # We shall parse the output above and give out path /dev/sde as in
        # this case
        for row in output.split('\n'):
           if re.search(r'XtremApp', row, re.I):
              if re.search(r'\d:\d:\d:' + str(lunid), row, re.I):
                device_name = re.findall(r'/\w+', row, re.I)
                if device_name:
                    return FilePath(device_name[0] + device_name[1])


        raise UnknownVolume(blockdevice_id)


def xio_from_configuration(cluster_id, xms_user, xms_password, xms_ip):
    """

    :param xms_ip:
    :param xms_user:
    :param xms_password:
    :return:
    """
    return EMCXtremIOBlockDeviceAPI(
        configuration=ArrayConfiguration(xms_user, xms_password, xms_ip),
        cluster_id=cluster_id,
        compute_instance_id=unicode(socket.gethostname()),
        allocation_unit=1
    )
