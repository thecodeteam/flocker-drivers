# Copyright Hybrid Logic Ltd. and EMC Corporation.
# See LICENSE file for details.

"""
EMC Test helpers for ``flocker.node.agents``.
"""

import os
import yaml

from zope.interface.verify import verifyObject
from zope.interface import implementer

from twisted.trial.unittest import SynchronousTestCase, SkipTest
from twisted.python.components import proxyForInterface

from .emc_sio import (
    IScaleIOVolumeManager, scaleio_client
)
from scaleiopy import ScaleIO


@implementer(IScaleIOVolumeManager)
class TidyScaleIOVolumeManager(
        proxyForInterface(IScaleIOVolumeManager, 'original')
):
    def __init__(self, original):
        """
        :param IScaleIOVolumeManager original: An instance of
            ``scaleiopy.scaleio.ScaleIO``.
        """
        self.original = original
        self.original._login()
        self._logged_in = self.original._logged_in

    def _cleanup(self):
        """
        Remove all the volumes that have been created by this VolumeManager
        wrapper.
        """
        # This deletes all flocker volumes from ScaleIO
        # TODO this doesnt take into account if it belongs to
        # flocker cluster, nore if it doesn't belong to testing.
        # So all flocker volumes will be deleted. Need to optimimize
        for volume in self.original.volumes:
            if volume.name.startswith('f'):
                siovolume = self.original.get_volume_by_name(
                    volume.name)
                sdcs = self.original.get_sdc_for_volume(
                    siovolume)
                if len(sdcs) > 0:
                    for sdc in sdcs:
                        sdc = self.original.get_sdc_by_id(sdc['sdcId'])
                        self.original.unmap_volume_from_sdc(
                            siovolume, sdcObj=sdc)
                else:
                    self.original.delete_volume(volume)


class IScaleIOVolumeManagerTestsMixin(object):
    """
    """
    def test_interface(self):
        """
        ``client`` provides ``IScaleIOVolumeManager``.
        """
        self.assertTrue(verifyObject(IScaleIOVolumeManager, self.client))


def make_iscaleiovolumemanager_tests(client_factory):
    """
    Build a ``TestCase`` for verifying that an implementation of
    ``IScaleIOVolumeManager`` adheres to that interface.
    """
    class Tests(IScaleIOVolumeManagerTestsMixin, SynchronousTestCase):
        def setUp(self):
            self.client = client_factory(test_case=self)

    return Tests


def scaleio_client_from_environment():
    """
    Create a ``scaleiopy.scaleio.ScaleIO`` using credentials from a
    test_emc_sio.py (TODO move these to config file)

    :returns: An instance of ``scaleiopy.scaleio.ScaleIO`` authenticated
    """
    config_file_path = os.environ.get('SCALEIO_CONFIG_FILE')
    if config_file_path is not None:
        config_file = open(config_file_path)
    else:
        raise SkipTest(
            'Supply the path to a scaleio config file '
            'using the SCALEIO_CONFIG_FILE environment variable. '
            'See: '
            'https://docs.clusterhq.com/en/latest/gettinginvolved/acceptance-testing.html '  # noqa
            'for details of the expected format.'
        )

    config = yaml.load(config_file.read())
    scaleio_config = config['scaleio']
    SCALEIO_USERNAME = scaleio_config['username']
    SCALEIO_PASSWORD = scaleio_config['password']
    MDM_GW_IP = scaleio_config['mdm']
    PROTECTION_DOMAIN = scaleio_config['pdomain']
    STORAGE_POOL = scaleio_config['storage_pool']
    SSL = scaleio_config['ssl']
    DEBUG = scaleio_config['debug']
    sio, pd, sp = scaleio_client(
        SCALEIO_USERNAME, SCALEIO_PASSWORD,
        MDM_GW_IP, pdomain=PROTECTION_DOMAIN, 
        spool=STORAGE_POOL, ssl=SSL,
        debug_level=DEBUG
    )
    return sio, pd, sp


def tidy_scaleio_client_for_test(test_case):
    """
    Return a ``scaleiopy.scaleio.ScaleIO`` whose ScaleIO API is a
    wrapped by a ``TidyScaleIOVolumeManager`` and register a ``test_case``
    cleanup callback to remove any volumes that are created during each test.
    """
    client, pd, sp = scaleio_client_from_environment()
    client = TidyScaleIOVolumeManager(client)
    test_case.addCleanup(client._cleanup)
    return client, pd, sp
