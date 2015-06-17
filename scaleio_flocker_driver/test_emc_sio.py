# Copyright Hybrid Logic Ltd. and EMC Corporation.
# See LICENSE file for details.

"""
Functional tests for
``flocker.node.agents.blockdevice.EMCScaleIOBlockDeviceAPI``
using a real Scaleio cluster.

Ideally emc drivers should be seperate like cinder driver,
we may change thay in the future.
"""

from uuid import uuid4

from bitmath import Byte, GiB

from twisted.trial.unittest import SynchronousTestCase

from flocker.testtools import skip_except

from .testtools_emc_sio import tidy_scaleio_client_for_test
from .emc_sio import (
    scaleio_client, emc_scaleio_api
)

from flocker.node.agents.test.test_blockdevice import (
    make_iblockdeviceapi_tests
)


def emcsioblockdeviceapi_for_test(cluster_id, test_case):
    """
    Create a ``EMCScaleIOBlockDeviceAPI`` instance for use in tests.

    :returns: A ``EMCCinderBlockDeviceAPI`` instance
    """

    client, pd, sp = tidy_scaleio_client_for_test(test_case)
    return emc_scaleio_api(
        client,
        cluster_id,
        pd,
        sp
    )


# We could remove this, all tests are covered
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
        'test_list_attached_and_unattached',
        'test_multiple_volumes_attached_to_host',
        'test_detach_unknown_volume',
        'test_detach_detached_volume',
        'test_detach_volume',
        'test_reattach_detached_volume',
        'test_attach_destroyed_volume',
        'test_get_device_path_unknown_volume',
        'test_get_device_path_unattached_volume',
        'test_get_device_path_device',
        'test_get_device_path_device_repeatable_results',
        'test_device_size',
        'test_resize_unknown_volume',
        'test_resize_volume_listed',
        'test_resize_destroyed_volume',
        'test_compute_instance_id_nonempty',
        'test_compute_instance_id_unicode'
    ]
)
class EMCScaleIOBlockDeviceAPIInterfaceTests(
        make_iblockdeviceapi_tests(
            blockdevice_api_factory=(
                lambda test_case: emcsioblockdeviceapi_for_test(
                    uuid4(),
                    test_case)
            ),
            minimum_allocatable_size=int(GiB(8).to_Byte().value),
            device_allocation_unit=int(GiB(8).to_Byte().value),
            unknown_blockdevice_id_factory=lambda test: unicode(uuid4())
        )
):
    """
    Interface adherence Tests for ``EMCScaleIOBlockDeviceAPI``
    """


# TODO EBS and Cinder implementations move the below tests up
# into <Driver>BlockDeviceAPIInterfaceTests
# See https://github.com/ClusterHQ/flocker/blob/master
#         /flocker/node/agents/functional/test_ebs.py#L84
# as an example
class EMCScaleIOBlockDeviceAPIImplementationTests(SynchronousTestCase):
    """
    Implementation specific tests for ``EMCScaleIOBlockDeviceAPI``.
    """
    def test_mdm_login(self):
        """
        Test EMCScaleIOBlockDeviceAPI Login
        """
        block_device_api = emcsioblockdeviceapi_for_test(uuid4(), self)

        self.assertTrue(block_device_api._client._logged_in is True)

    # TODO add other ScaleIO Specific tests, like protection domain,
    # storage pools and other cluster information ??
