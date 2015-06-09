
"""
Functional tests for
``flocker.node.agents.blockdevice.EMCXtremIOBlockDeviceAPI``
"""

import os
import socket
from uuid import uuid4

import functools

XIO_ALLOCATION_UNIT = int(1024*1024)

from twisted.trial.unittest import SynchronousTestCase, SkipTest


from flocker.node.agents.test.test_blockdevice import make_iblockdeviceapi_tests
from flocker.testtools import (
	skip_except
)


from testtools_emc_xio import (
    tidy_xio_client_for_test
)

def emcxtremioblockdeviceapi_for_test(test_case):
    """
    Create a ``EMCXtremIOBlockDeviceAPI`` instance for use in tests.
    :returns: A ``EMCCinderBlockDeviceAPI`` instance
    """
    user_id = os.getuid()
    if user_id != 0:
        raise SkipTest(
            "``EMCXtremIOBlockDeviceAPI`` queries for iSCSI initiator name which is owned by root, "
            "Required UID: 0, Found UID: {!r}".format(user_id)
        )
    xio = tidy_xio_client_for_test(test_case)
    return xio


# `EMCXtremIOBlockDeviceAPI`` doesnt implement any parts of
# ``IBlockDeviceAPI`` yet. Skip the tests for now.
@skip_except(
    supported_tests=[
        'test_interface',
        'test_list_volume_empty',
        'test_listed_volume_attributes',
        'test_created_is_listed',
        'test_created_volume_attributes',
        'test_destroy_unknown_volume',
        'test_destroy_volume',
        'test_destroy_destroyed_volume',
        'test_attach_unknown_volume',
        'test_attach_attached_volume',
        'test_attach_elsewhere_attached_volume',
        'test_attach_unattached_volume',
        'test_attached_volume_listed',
        'test_attach_volume_validate_size',
        'test_multiple_volumes_attached_to_host',
        'test_detach_unknown_volume',
        'test_detach_detached_volume',
        'test_reattach_detached_volume',
        'test_attach_destroyed_volume',
        'test_list_attached_and_unattached',
        'test_compute_instance_id_nonempty',
        'test_compute_instance_id_unicode',
        'test_resize_volume_listed',
        'test_resize_unknown_volume',
        'test_resize_destroyed_volume',
        'test_get_device_path_device',
        'test_get_device_path_unknown_volume',
        'test_get_device_path_unattached_volume',
        'test_detach_volume',
        'test_get_device_path_device_repeatable_results',
        'test_device_size'
        ]
)

class EMCXtremIOBlockDeviceAPIInterfaceTests(
        make_iblockdeviceapi_tests(
            blockdevice_api_factory=functools.partial(emcxtremioblockdeviceapi_for_test),
            minimum_allocatable_size=XIO_ALLOCATION_UNIT,
            device_allocation_unit=None,
	    unknown_blockdevice_id_factory=lambda test: u"vol-00000000"
        )
):
	"""
	Interface adherence Tests for ``EMCXtremIOBlockDeviceAPI``
	"""
