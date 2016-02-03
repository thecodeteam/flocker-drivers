# Copyright Hybrid Logic Ltd.
# Copyright 2015 EMC Corporation
# See LICENSE file for details.

"""
Functional tests for
``flocker.node.agents.blockdevice.EMCXtremIOBlockDeviceAPI``
"""

import os
import socket
from uuid import uuid4

import functools

XIO_ALLOCATION_UNIT = int(1024 * 1024)

from twisted.trial.unittest import SynchronousTestCase, SkipTest

from flocker.node.agents.test.test_blockdevice import make_iblockdeviceapi_tests

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
