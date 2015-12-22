# -*- test-case-name: scaleio_flocker_driver.test_emc_sio -*-
# Copyright 2015 EMC Corporation

"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import time
from uuid import UUID
import logging
import requests
import json

from subprocess import check_output

from bitmath import Byte, GiB, MiB, KiB

from scaleiopy import ScaleIO

from eliot import Message, Logger
from zope.interface import implementer, Interface
from twisted.python.filepath import FilePath
from characteristic import attributes

from flocker.node.agents.blockdevice import (
    AlreadyAttachedVolume, IBlockDeviceAPI,
    BlockDeviceVolume, UnknownVolume, UnattachedVolume
)

# Eliot is transitioning away from the "Logger instances all over the place"
# approach.  And it's hard to put Logger instances on PRecord subclasses which
# we have a lot of.  So just use this global logger for now.
_logger = Logger()

# Multiple protection domains can exist within a ScaleIO Cluster, however
# there is awlways a default protection domain.
DEFAULT_PROTECTION_DOMAIN = "default"

# Mutiple storage pools can exist within a single ScaleIO Cluster, however
# there is a default storage pool created automatically.
DEFAULT_STORAGE_POOL = "default"

# ScaleIO's allocation granularity is 8GB
ALLOCATION_GRANULARITY = 8

# Where /dev/scni* shows up for ScaleIO in Linux
DEVICE_FILEPATH = "/dev/disk/by-id/"

# All ScaleIO volumes are prefixed with this.
DEVICE_PREFIX = "emc-vol-"

# Used in client creation
HTTP = "http"
HTTPS = "https"
DEBUG = "DEBUG"

# Default to 443
DEFAULT_PORT = 443

# TODO ScaleIO 1.30 has a minor blocker (see below)
# https://github.com/swevm/scaleio-py/issues/19

# Tested with issues
ScaleIO_1_30 = '1.0'
# Tested
ScaleIO_1_31 = '1.1'
# Version 1.1 is the response from
# both 1.31 and 1.32, other than that,
# 1.32 may have errors temporarily.
# Untested
# ScaleIO_1_32 = '1.2'
SUPPORTED_API_VERSIONS = [ScaleIO_1_31]


class IScaleIOVolumeManager(Interface):
    """
    The parts of ``scaleiopy.scaleio.ScaleIO`` that we use.
    """
    def create_volume(
            self, volName, volSizeInMb, pdObj, spObj,
            thinProvision=True, **kwargs):
        """
        Creates a Volume

        :param string volName: The volume Name
        :param int volSizeInMb: the volume's size in Megabytes
        :param ``ScaleIO_Protection_Domain`` pdObj: a Protection Domain
            instance
        :param boolean thinProvision: Option to thickly provision volumes.
            Default is to Thin.
        :return Response: an HTTP response with the ID of the
            volume in the Body.
        """

    def get_pd_by_name(self, name):
        """
        Retrieves a protection domain by its Name
        :param string name: The name of the protection domain
        :param ``ScaleIO_Protection_Domain``: ``Protection Domain`` object.
        """

    def get_storage_pool_by_name(self, name):
        """
        Get ScaleIO StoragePool object by its name
        :param name: Name of StoragePool
        :return: ScaleIO StoragePool object
        :raise KeyError: No StoragePool with specified name found
        :rtype: StoragePool object
        """

    def get_volume_by_name(self, name):
        """
        Retrieves a volume by its Name
        :param string name: Name of the volume
        :return ``ScaleIO_Volume``: a ``ScaleIO_Volume`` instance.
        """

    def delete_volume(self, volObj, removeMode='ONLY_ME', **kwargs):
        """
         Deletes a volume from ScaleIO
        :param ScaleIO_Volume volObj: Scaleio Volume Object
        :param string removeMode: options to remove volumes decendents
           removeMode = 'ONLY_ME' | 'INCLUDING_DESCENDANTS' |
            'DESCENDANTS_ONLY' | 'WHOLE_VTREE'
        :param args **kwargs: makes it possible to "autoUnmap"
            volumes on deletion
            https://github.com/wallnerryan/scaleio-py/
            blob/master/scaleiopy/scaleio.py#L821
        """

    def map_volume_to_sdc(
            self, volumeObj, sdcObj=None,
            allowMultipleMappings=False, **kwargs):
        """
        Maps a Volume to an SDC

        :param ScaleIO_Volume volObj: The volume
        :param ScaleIO_SDC: the SDC
        :param boolean allowMultipleMappings: allow multiple
        :return Response: an HTTP response with the ID of the
            volume in the Body.
        """

    def unmap_volume_from_sdc(self, volObj, sdcObj=None, **kwargs):
        """
        Un-Maps a Volume to an SDC

        :param ScaleIO_Volume volObj: The volume
        :param ScaleIO_SDC: the SDC
        :return Response: an HTTP response with the ID of the
            volume in the Body.
        """

    def get_volume_by_id(self, id):
        """
        Returns a ``ScaleIO_Volume`` object by ID
        :param: unicode id: is the dataset_id
        """

    def get_sdc_for_volume(self, volObj):
        """
        Returns a ``ScaleIO_SDC`` object by IPAddress
        :param: ``ScaleIO_Volume`` volObj:  ``ScaleIO_Volume``
        :return ``ScaleIO_SDC``: an SDC Instance
        """

    def resize_volume(self, volumeObj, sizeInGb, bsize=1000):
        """
        Returns None
        :param volumeObj: ``ScaleIO_Volume`` volObj:  ``ScaleIO_Volume``
        :param int sizeInGb: new GB size
        :param int bsize: size in bytes
        :return ``ScaleIO_SDC``: an SDC Instance
        """

    def get_sdc_by_ip(self, ip):
        """
        Returns a ``ScaleIO_SDC`` object by IPAddress
        :param: string ip: is ip address of the sdc
        :return ``ScaleIO_SDC``: an SDC Instance
        """

    def get_sdc_by_id(self, id):
        """
        Returns a ``ScaleIO_SDC`` object by ID
        :param: unicode id: is the dataset_id
        """

    def get_sdc_by_guid(self, guid):
        """
        Returns a ``ScaleIO_SDC`` object by GUID
        :param: unicode guid: is the kernel module on the host id
        """

    def _login(self):
        """
        Logs in the ScaleIO instance the the MDM Gateway
        """

    def volumes(self):
        """
        Retrieves a list of all volumes from the ScaleIO cluster
        :return list volumes: A list of ``ScaleIO_Volume``'s
        """


def emc_scaleio_api(scaleio_client, cluster_id, pdomain, spool):
    """
    :param scaleiopy.sclaeio.ScaleIO scaleio_client: The ScaleIO API client
    :param UUID cluster_id: A Flocker cluster ID.
    :returns: A ``EMCScaleIOBlockDeviceAPI``.
    """
    return EMCScaleIOBlockDeviceAPI(
        scaleio_client,
        cluster_id,
        pdomain,
        spool
    )


@attributes(["protection_domain"])
class UnknownProtectionDomain(Exception):
    """
    The protection domain could not be found.
    :param str protection_domain: The pdomain
    """
    def __init__(self, protection_domain):
        if not isinstance(protection_domain, str):
            raise TypeError(
                'Unexpected protection_domain type. '
                'Expected str. '
                'Got {!r}.'.format(protection_domain)
            )
        Exception.__init__(self, protection_domain)
        self.protection_domain = protection_domain


@attributes(["storage_pool"])
class UnknownStoragePool(Exception):
    """
    The storage pool could not be found.
    :param str storage_pool: The pdomain
    """
    def __init__(self, storage_pool):
        if not isinstance(storage_pool, str):
            raise TypeError(
                'Unexpected storage_pool type. '
                'Expected str. '
                'Got {!r}.'.format(storage_pool)
            )
        Exception.__init__(self, storage_pool)
        self.storage_pool = storage_pool


class UnsupportedVolumeSize(Exception):
    """
    The volume size is not supported
    Needs to be 8GB allocation granularity
    :param unicode dataset_id: The volume dataset_id
    """
    def __init__(self, dataset_id):
        if not isinstance(dataset_id, UUID):
            raise TypeError(
                'Unexpected dataset_id type. '
                'Expected unicode. '
                'Got {!r}.'.format(dataset_id)
            )
        Exception.__init__(self, dataset_id)
        self.dataset_id = dataset_id


class UnsupportedAPIVersion(Exception):
    """
    The API version returned by the ScaleIO gateway
    is not supported.
    :param string api_version: the version of the API
    """
    def __init__(self, api_version):
        if not isinstance(api_version, str):
            raise TypeError(
                'Unexpected api_version type. '
                'Expected string. '
                'Got {!r}.'.format(api_version)
            )
        Exception.__init__(self, api_version)
        self.api_version = api_version


def check_supported_volume_size(
        size_in_bytes, dataset_id, alloc_granularity=8):
    """
    Checks appropriate volume size for Backend (ScaleIO)
    :param bytes size_in_bytes: size of volume in bytes
    """
    gibs = Byte(size_in_bytes).to_GiB().value
    # modulus should be 0.0 or throw unsupported volume
    if gibs % 8 != 0:
        Message.new(Error="Volume size unsupported"
                    + str(size_in_bytes)
                    + str(dataset_id)).write(_logger)
        raise UnsupportedVolumeSize(dataset_id=dataset_id)


def _check_api_version(api, usr, passw, verify_ssl=False):
    """
    Version check against supported API versions
    :param string api: the full api string
    :param string usr: The username for ScaleIO Driver, this will be used
            to login and enable requests to be made to the underlying ScaleIO
            BlockDeviceAPI
    :param string passw: The username for ScaleIO Driver, this will be
            used to login and enable requests to be made to the underlying
            ScaleIO BlockDeviceAPI
    :param bool verfy_ssl: True | False to verify SSL

    """
    # Purposely arent using scaleio-py here
    # because we want bare bones call to API with
    # user and password only. API version calls don't
    # need token auth requests.
    request = (api + "/version")
    r = requests.get(request, auth=(usr, passw),
                     verify=verify_ssl)
    version_response = json.dumps(r.json())
    # Check Version from JSON object
    api_version = version_response.strip('"')
    if api_version not in SUPPORTED_API_VERSIONS:
        raise UnsupportedAPIVersion(api_version)
    return api_version


# TODO Right now the driver can only handle one protection domain
# and one storage pool. In order to take advantage of more, flocker
# would need to supply metadata about how a container wants a volume.
# E.g. Gold or "SSD" for storage pool and protection=high
# for protection domains.
def scaleio_client(usr, passw, mdm, port=DEFAULT_PORT,
                   pdomain=DEFAULT_PROTECTION_DOMAIN,
                   spool=DEFAULT_STORAGE_POOL,
                   crt=None, ssl=False, debug_level=DEBUG):
    """
    Client for calling operations on ScaleIO API.

        :param string usr: The username for ScaleIO Driver, this will be used
            to login and enable requests to be made to the underlying ScaleIO
            BlockDeviceAPI
        :param string passw: The username for ScaleIO Driver, this will be
            used to login and enable requests to be made to the underlying
            ScaleIO BlockDeviceAPI
        :param unicode mdm: The Main MDM IP address. ScaleIO Driver will
            communicate with the ScaleIO Gateway Node to issue REST API
            commands.
        :param integer port: The port
        :param string pdomain: The protection domain for this driver instance
        :param string spool: The storage pool used for this driver instance
        :param FilePath crt: An optional certificate to be used for
            optional authentication methods. The presence of this
            certificate will change verify to True inside the requests.
        :param boolean ssl: use SSL?
        :param boolean debug: verbosity
    """

    proto = HTTP
    if ssl:
        proto = HTTPS
        Message.new(Info="Using HTTPS").write(_logger)

    verify = False
    if crt is not None:
        # TODO (support for certificates)
        # 1) "Replacing the default self-signed security certificate
        # with your own trusted certificate"
        # 2) "Replacing the default self-signed security certificate
        # with your own self-signed certificate"
        verify = True

    # Log the debug level
    Message.new(Info="Debug Level: "
                + debug_level).write(_logger)

    # Check if version supported
    api = "%s://%s/api" % (proto, mdm)
    version = _check_api_version(api, usr, passw, verify_ssl=verify)
    Message.new(Info="Using API Version %s" % version).write(_logger)

    # Version checks out, get scaleio object.
    sio = ScaleIO(api, usr, passw,
                  verify_ssl=verify,
                  debugLevel=debug_level)

    # Verify login
    sio._login()
    Message.new(Info="Logged In to ScaleIO: %s://%s/api"
                % (proto, mdm)).write(_logger)

    # Check for protection domain configured.
    pdomain_found = False
    for domain in sio.protection_domains:
        if domain.name == pdomain:
            pdomain_found = True
            Message.new(Info="Protection Domain Verified "
                        + str(pdomain)).write(_logger)
            continue

    # Check for storage pool configured.
    spool_found = False
    for pool in sio.storage_pools:
        if pool.name == spool:
            spool_found = True
            Message.new(Info="Storage Pool Verified "
                        + str(spool)).write(_logger)
            continue

    if not pdomain_found:
        Message.new(Error="Protection Domain Not Found "
                    + str(pdomain)).write(_logger)
        raise UnknownProtectionDomain(pdomain)
    elif not spool_found:
        Message.new(Error="Storage Pool Not Found "
                    + str(spool)).write(_logger)
        raise UnknownStoragePool(spool)

    return sio, pdomain, spool


def bytes_to_mbytes(size):
        """
        :param bytes size: byte size of the volume
        :return size in megabytes
        """
        return int(Byte(size).to_MiB().value)


def _blockdevicevolume_from_scaleio_volume(
        scaleio_volume, attached_to=None):
    """
    :param scaleiopy.scaleio.ScaleIO_Volume scaleio_volume: a
        ScaleIO Volume
    :returns: ``BlockDeviceVolume```
    """

    # TODO only put one mapping per volume, however
    # ScaleIO can multi-map, should attached_to
    # consider being a list?

    # Return a ``BlockDeviceVolume``
    return BlockDeviceVolume(
        blockdevice_id=unicode(scaleio_volume.id),
        size=int(KiB(scaleio_volume.size_kb).to_Byte().value),
        attached_to=attached_to,
        dataset_id=UUID(bytes=(
            str(str(scaleio_volume.name)[1:23]) + '==').replace(
                '_', '/').decode('base64'))
    )


# This fixes https://github.com/ClusterHQ/flocker-emc/issues/14
# but this is hacky and redundant because it logs into the
# SIO object and the gateway before every Flocker API call
# which fixed requests getting SSL errors becuase of
# communication errors with the gateway.
def check_login(api_func):
    """
    Decorator to check local SIO object login
    status.
    """
    def wrap(self, *args, **kwargs):
        self._client._login()
        return api_func(self, *args, **kwargs)
    return wrap


@implementer(IBlockDeviceAPI)
class EMCScaleIOBlockDeviceAPI(object):
    """
    A ``IBlockDeviceAPI`` which uses EMC ScaleIO block devices
    Current Support: ScaleIO 1.31 +
    """

    def __init__(self, sio_client, cluster_id,
                 pdomain, spool):
        """
        :param ScaleIO sio_client: An instance of ScaleIO requests
            client.
        :param UUID cluster_id: An ID that will be included in the
            names of ScaleIO volumes to identify cluster
        :returns: A ``BlockDeviceVolume``.
        """
        self._client = sio_client
        self._cluster_id = cluster_id
        self._pdomain = pdomain
        self._spool = spool
        self._instance_id = self.compute_instance_id()

    def allocation_unit(self):
        """
        8GiB is the minimum allocation unit described by the ScaelIO Guide
        https://community.emc.com/docs/DOC-43968 for ScaleIO v1.31
        return int: 8 GiB
        """
        return int(GiB(8).to_Byte().value)

    # TODO should we keep is as class attr?
    @staticmethod
    def id_to_short(_id):
        """
        :param UUID _id: UUID dataset_id of the volume
        :return encoded hash of the dataset_id
        """
        return _id.bytes.encode(
            'base64').rstrip('=\n').replace('/', '_')

    @staticmethod
    def volumename_to_datasetid(volume_name):
        """
        :param string volume_name: Name of the volume
        :return str: Slice of the volume which is the
            hashed dataset_id
        """
        # The SIO name does not have many chars to work
        # with so we need to chop. Not be best in terms of
        # collision consistency.
        return volume_name[23:]

    @staticmethod
    def to_scaleio_size(size_mb):
        """
        :param int size_mb: The size of the volume in megabytes
            that has not been reduced to ScaleIO restrictions.
        :return int: A granularity of ALLOCATION_GRANULARITY in MBytes
        """
        # Should we use self.allocation_unit()
        # instead of ALLOCATION_GRANULARITY?
        div = round(int(MiB(size_mb).to_GiB().value) / ALLOCATION_GRANULARITY)
        if div > 0:
            return size_mb
        else:
            # Minimum is 8GB
            # should we use self.allocation_unit()?
            return int(GiB(8).to_MiB().value)

    @classmethod
    def _is_cluster_volume(cls, cluster_id, scaleio_volume):
        """
        :param UUID cluster_id: UUID of the flocker cluster
        :param scaleiopy.scaleio.ScaleIO_Volume scaleio_volume: a
            ScaleIO Volume
        :return boolean
        """
        # TODO it would be nice to be able to store metadata
        # in flocker in some k/v store or database so we can
        # name volumes and take our cluster/datase IDs that are
        # in the name seperate.
        if scaleio_volume.name.startswith("f"):
            actual_clusterid = cls.volumename_to_datasetid(
                str(scaleio_volume.name))
            if actual_clusterid is not None:
                if actual_clusterid in str(cluster_id):
                    return True
        return False

    def compute_instance_id(self):
        """
        ScaleIO Stored a UUID in the SDC kernel module.
        """
        return unicode(check_output(
            ["/bin/emc/scaleio/drv_cfg",
             "--query_guid"]).rstrip('\r\n')).lower()

    @check_login
    def create_volume(self, dataset_id, size):
        """
        Create a new volume.

        :param UUID dataset_id: The Flocker dataset ID of the dataset on this
            volume.
        :param int size: The size of the new volume in bytes.
        :returns: A ``BlockDeviceVolume``.
        """

        # Convert dataset_id into base64 so we can
        # store it as part of the name.
        slug = self.id_to_short(dataset_id)

        # Addresses volumes for ScaleIO that will
        # be the incorrect size and therefore cause
        # flocker to twerk. Throws UnsupportedVolumeSize
        # see https://clusterhq.atlassian.net/browse/FLOC-1874
        check_supported_volume_size(size, dataset_id)

        # Convert bytes to megabytes for API
        mb_size = bytes_to_mbytes(size)
        scaleio_size = self.to_scaleio_size(mb_size)

        # Flocker volumes start with and f again,
        # we only have 32 chars to work with in the ```name```
        volume_name = 'f%s%s' % (slug, str(self._cluster_id)[:8])
        volume = self._client.create_volume(
            volume_name,
            scaleio_size,
            self._client.get_pd_by_name(self._pdomain),
            self._client.get_storage_pool_by_name(self._spool))

        siovolume = self._client.get_volume_by_name(
            volume_name)
        Message.new(Info="Created Volume "
                    + siovolume.name).write(_logger)
        Message.new(vol=siovolume.id,
                    size=siovolume.size_kb).write(_logger)

        return _blockdevicevolume_from_scaleio_volume(
            self._client.get_volume_by_name(volume_name))

    @check_login
    def destroy_volume(self, blockdevice_id):
        """
        Destroy an existing volume.

        :param unicode blockdevice_id: The unique identifier for the volume to
            destroy.

        :raises UnknownVolume: If the supplied ``blockdevice_id`` does not
            exist.

        :return: ``None``
        """
        # Check if the volume exists, this snippet
        # was taken from blockdevice.LoopBackBlockDeviceAPI
        # should this be a common/reusable function?
        volume = self._get(blockdevice_id)

        # remove the volume if everything is good.
        self._client.delete_volume(
            self._client.get_volume_by_id(str(blockdevice_id)))

    @check_login
    def _get(self, blockdevice_id):
        for volume in self.list_volumes():
            if volume.blockdevice_id == blockdevice_id:
                return volume
        Message.new(Error="Could Not Find Volume "
                    + str(blockdevice_id)).write(_logger)
        raise UnknownVolume(blockdevice_id)

    @check_login
    def attach_volume(self, blockdevice_id, attach_to):
        """
        Attach ``blockdevice_id`` to ``host``.

        :param unicode blockdevice_id: The unique identifier for the block
            device being attached.
        :param unicode attach_to: An identifier like the one returned by the
            ``compute_instance_id`` method indicating the node to which to
            attach the volume.
        :raises UnknownVolume: If the supplied ``blockdevice_id`` does not
            exist.
        :raises AlreadyAttachedVolume: If the supplied ``blockdevice_id`` is
            already attached.
        :returns: A ``BlockDeviceVolume`` with a ``host`` attribute set to
            ``host``.
        """
        # Raises UnknownVolume
        volume = self._get(blockdevice_id)
        # raises AlreadyAttachedVolume
        if volume.attached_to is not None:
            Message.new(Error="Could Not Destroy Volume "
                        + str(blockdevice_id)
                        + "is already attached").write(_logger)
            raise AlreadyAttachedVolume(blockdevice_id)

        # Get the SDC Object by the GUID of the host.
        sdc = self._client.get_sdc_by_guid(
            self._instance_id.upper())

        # Try mapping volumes

        # TODO errors are currently hard to get from sclaeio-py
        # https://github.com/swevm/scaleio-py/issues/6
        # ultimately we should be able to get more specific
        # errors about why the failure happened such as
        # ``{"message":"Only a single SDC may be mapped to this
        # volume at a time","httpStatusCode":500,"errorCode":306}``
        try:
            self._client.map_volume_to_sdc(
                self._client.get_volume_by_id(
                    str(blockdevice_id)), sdcObj=sdc,
                allowMultipleMappings=False)
        except Exception as e:
            # TODO real errors need to be returned by scaleio-py
            Message.new(Error=str(blockdevice_id) + " "
                        + str(e)).write(_logger)
            raise AlreadyAttachedVolume(blockdevice_id)

        attached_volume = volume.set(
            attached_to=self._instance_id)
        return attached_volume

    @check_login
    def detach_volume(self, blockdevice_id):
        """
        Detach ``blockdevice_id`` from whatever host it is attached to.

        :param unicode blockdevice_id: The unique identifier for the block
            device being detached.

        :raises UnknownVolume: If the supplied ``blockdevice_id`` does not
            exist.
        :raises UnattachedVolume: If the supplied ``blockdevice_id`` is
            not attached to anything.
        :returns: ``None``
        """
        # raises UnknownVolume
        volume = self._get(blockdevice_id)
        # raises UnattachedVolume
        if volume.attached_to is None:
            Message.new(Error="Could Not Attach Volume "
                        + str(blockdevice_id)
                        + "is unattached").write(_logger)
            raise UnattachedVolume(blockdevice_id)

        # This list should consist of only one SDC, however
        # future versions of this may use mappingToAllSdcsEnabled
        # or ``allowMultipleMappings`` in the above function
        # which we would need to remove potentially all SDC mappings
        # if we initially map a volume to all SDCs
        sio_volume = self._client.get_volume_by_id(str(blockdevice_id))
        sdcs = self._client.get_sdc_for_volume(sio_volume)
        if len(sdcs) > 0:
            for sdc in sdcs:
                sdc = self._client.get_sdc_by_id(sdc['sdcId'])
                self._client.unmap_volume_from_sdc(sio_volume, sdcObj=sdc)
        else:
            # raises UnattachedVolume (is this needed?)
            raise UnattachedVolume(blockdevice_id)
        volume.set(attached_to=None)

    @check_login
    def resize_volume(self, blockdevice_id, size):
        """
        Resize an unattached ``blockdevice_id``.

        This changes the amount of storage available.  It does not change the
        data on the volume (including the filesystem).

        :param unicode blockdevice_id: The unique identifier for the block
            device being detached.
        :param int size: The required size, in bytes, of the volume.

        :raises UnknownVolume: If the supplied ``blockdevice_id`` does not
            exist.

        :returns: ``None``
        """
        # raises UnknownVolume
        volume = self._get(blockdevice_id)

        # raises AlreadyAttachedVolume, do we want this?
        # is says only an unattached volume, if it is attached
        # do we detach and then resize thenr reattach? Or should we
        # just assume that all things that call this function know
        # that the volume is detached already?
        if volume.attached_to is not None:
            Message.new(Error="Cannot Resize Volume "
                        + str(blockdevice_id)
                        + "is attached").write(_logger)
            raise AlreadyAttachedVolume(blockdevice_id)

        sio_volume = self._client.get_volume_by_id(str(blockdevice_id))

        size_in_gb = int(Byte(size).to_GiB().value)
        self._client.resize_volume(sio_volume, size_in_gb)

    @check_login
    def list_volumes(self):
        """
        List all the block devices available via the back end API.

        :returns: A ``list`` of ``BlockDeviceVolume``s.
        """
        volumes = []
        for scaleio_volume in self._client.volumes:
            guid = None
            if scaleio_volume.mapped_sdcs is not None:
                # Flocker assumes one attachment, even though
                # scaleio can multi-map to SDC's lets assume its 1
                sdc_id = scaleio_volume.mapped_sdcs[0]["sdcId"]
                guid = self._client.get_sdc_by_id(sdc_id).guid.lower()
            if self._is_cluster_volume(self._cluster_id, scaleio_volume):
                volumes.append(
                    _blockdevicevolume_from_scaleio_volume(
                        scaleio_volume, attached_to=guid)
                )
        return volumes

    @classmethod
    def _get_dev_from_blockdeviceid(cls, blockdevice_id):
        """
        Get the real device path from blockdevice_id
        """
        # get the devices path for linux
        devs_path = FilePath(DEVICE_FILEPATH)

        cls.wait_for_volume(blockdevice_id)
        devs = devs_path.globChildren("%s*" % DEVICE_PREFIX)
        for dev in devs:
            if str(blockdevice_id) in dev.path:
                return dev.realpath()

    @staticmethod
    def _dev_exists_from_blockdeviceid(blockdevice_id):
        """
        Check if the device exists before continuing
        """
        # get the devices path for linux
        devs_path = FilePath(DEVICE_FILEPATH)
        devs = devs_path.globChildren("%s*" % DEVICE_PREFIX)
        for dev in devs:
            if str(blockdevice_id) in dev.path:
                return True
        return False

    @classmethod
    def wait_for_volume(cls, blockdevice_id, time_limit=60):
        """
        Wait for a ``Volume`` with the same ``id`` as ``expected_volume`` to be
        listed

        :param Volume expected_volume: The ``Volume`` to wait for.
        :param int time_limit: The maximum time, in seconds, to wait for the
            ``expected_volume`` to have ``expected_status``.
        :raises Exception: If ``expected_volume`` is not
            listed within ``time_limit``.
        :returns: The listed ``Volume`` that matches ``expected_volume``.
        """
        start_time = time.time()
        while True:
            exists = cls._dev_exists_from_blockdeviceid(
                blockdevice_id)
            if exists:
                return

            elapsed_time = time.time() - start_time
            if elapsed_time < time_limit:
                time.sleep(0.1)
            else:
                Message.new(Error="Could Find Device for Volume "
                            + "Timeout on: "
                            + str(blockdevice_id)).write(_logger)
                raise Exception(
                    'Timed out while waiting for volume. '
                    'Expected Volume: {!r}, '
                    'Elapsed Time: {!r}, '
                    'Time Limit: {!r}.'.format(
                        blockdevice_id, elapsed_time, time_limit
                    )
                )

    @check_login
    def get_device_path(self, blockdevice_id):
        """
        Return the device path that has been allocated to the block device on
        the host to which it is currently attached.

        :param unicode blockdevice_id: The unique identifier for the block
            device.
        :raises UnknownVolume: If the supplied ``blockdevice_id`` does not
            exist.
        :raises UnattachedVolume: If the supplied ``blockdevice_id`` is
            not attached to a host.
        :returns: A ``FilePath`` for the device.
        """
        # raises UnknownVolume
        volume = self._get(blockdevice_id)

        # raises UnattachedVolume
        if volume.attached_to is None:
            Message.new(Error="Could get Device Path "
                        + str(blockdevice_id)
                        + "is not attached").write(_logger)
            raise UnattachedVolume(blockdevice_id)

        # Check the "actual volume" for attachment
        sio_volume = self._client.get_volume_by_id(
            str(blockdevice_id))
        sdcs = self._client.get_sdc_for_volume(sio_volume)
        if len(sdcs) == 0:
            Message.new(Error="Could get Device Path "
                        + str(blockdevice_id)
                        + "is not attached").write(_logger)
            raise UnattachedVolume(blockdevice_id)

        # return the real path of the device
        return self._get_dev_from_blockdeviceid(volume.blockdevice_id)


def scaleio_from_configuration(cluster_id, username, password, mdm_ip, port,
                               protection_domain, storage_pool,
                               certificate, ssl, debug):
    """
    Returns Flocker ScaleIO BlockDeviceAPI from plugin config yml.
        :param uuid cluster_id: The UUID of the cluster
        :param string username: The username for ScaleIO Driver,
            this will be used to login and enable requests to
            be made to the underlying ScaleIO BlockDeviceAPI
        :param string password: The username for ScaleIO Driver,
            this will be used to login and enable requests to be
            made to the underlying ScaleIO BlockDeviceAPI
        :param unicode mdm_ip: The Main MDM IP address. ScaleIO
            Driver will communicate with the ScaleIO Gateway
            Node to issue REST API commands.
        :param integer port: MDM Gateway The port
        :param string protection_domain: The protection domain
            for this driver instance
        :param string storage_pool: The storage pool used for
            this driver instance
        :param FilePath certificate: An optional certificate
            to be used for optional authentication methods.
            The presence of this certificate will change verify
            to True inside the requests.
        :param boolean ssl: use SSL?
        :param boolean debug: verbosity
    """
    client, pd, sp = scaleio_client(
        username, password, mdm_ip, port, pdomain=protection_domain,
        spool=storage_pool, crt=certificate, ssl=ssl, debug_level=debug
    )
    return emc_scaleio_api(
        client,
        cluster_id,
        pd,
        sp
    )
