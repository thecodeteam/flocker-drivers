# Copyright Hybrid Logic Ltd.
# Copyright 2015 EMC Corporation
# See LICENSE file for details.

"""
Functional tests for
``flocker.node.agents.blockdevice.EMCVmaxBlockDeviceAPI``
using a real VMAX cluster.

Ideally emc drivers should be seperate like cinder driver,
we may change thay in the future.
"""
import functools
import traceback
from uuid import uuid4

from twisted.trial.unittest import SynchronousTestCase
from flocker.node.agents.blockdevice import UnknownVolume, MandatoryProfiles

from testtools_emc_vmax import tidy_vmax_client_for_test, vmax_allocation_unit
from flocker.node.agents.test.test_blockdevice import make_iblockdeviceapi_tests, make_iprofiledblockdeviceapi_tests


def emcvmaxblockdeviceapi_for_test(test_case=None):
    """
    Create a ``EMCvmaxBlockDeviceAPI`` instance for use in tests.

    :returns: A ``EMCCinderBlockDeviceAPI`` instance
    """
    return tidy_vmax_client_for_test(test_case)


class EMCVmaxBlockDeviceAPIInterfaceTests(
    make_iblockdeviceapi_tests(
        blockdevice_api_factory=functools.partial(emcvmaxblockdeviceapi_for_test),
        minimum_allocatable_size=vmax_allocation_unit(1),
        device_allocation_unit=vmax_allocation_unit(1),
        unknown_blockdevice_id_factory=lambda test: unicode(uuid4())
    )
):
    """
    Interface adherence Tests for ``EMCVmaxBlockDeviceAPIInterfaceTests``
    """


class EMCVmaxIProfiledBlockDeviceAPITestsMixin(
    make_iprofiledblockdeviceapi_tests(
        profiled_blockdevice_api_factory=functools.partial(emcvmaxblockdeviceapi_for_test),
        dataset_size=vmax_allocation_unit(1)
    )
):
    """
    Interface adherence Tests for ``EMCVmaxIProfiledBlockDeviceAPITestsMixin``
    """


# TODO EBS and Cinder implementations move the below tests up
# into <Driver>BlockDeviceAPIInterfaceTests
# See https://github.com/ClusterHQ/flocker/blob/master
#         /flocker/node/agents/functional/test_ebs.py#L84
# as an example
class EMCVmaxBlockDeviceAPIImplementationTests(SynchronousTestCase):
    """
    Implementation specific tests for ``EMCVmaxBlockDeviceAPIImplementationTests``.
    """
    def test_login(self):
        """
        Test EMCVmaxBlockDeviceAPI Login
        """
        print "\ntest_login"
        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            print 'allocation unit = %s' % str(block_device_api.allocation_unit())
            for profile in block_device_api.get_profile_list():
                print 'profile = %s symmetrix id = %s' % (profile, block_device_api._get_symmetrix_id(profile=profile))
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)

    def test_list_profiles(self):
        """
        Test EMCVmaxBlockDeviceAPI List Profiles
        """
        print "\ntest_list_profiles"
        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            print 'profiles = %s' % str(block_device_api.get_profile_list())
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)

    def test_unknown_blockdevice_id(self):
        """
        Test EMCVmaxBlockDeviceAPI Test bogus device id
        """
        print "\ntest_unknown_blockdevice_id"
        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            blockdevice_id = unicode(uuid4())
            block_device_api.destroy_volume(blockdevice_id)
            self.fail('block device found!, %s' % blockdevice_id)
        except UnknownVolume as e:
            traceback.print_exc()

    def test_ecom_list_volumes(self):
        """
        Test EMCVmaxBlockDeviceAPI ecom
        """
        print "\ntest_ecom_list_volumes"
        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)

            volumes = block_device_api.list_flocker_volumes()
            for v in volumes:
                print str(v)
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)

    def test_get_vmax_hosts(self):
        """
        Test EMCVmaxBlockDeviceAPI list hosts in agent.yml
        """
        print "\ntest_get_vmax_hosts"

        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            host_id = block_device_api.compute_instance_id()
            print str(host_id)
            hosts = block_device_api.get_vmax_hosts()
            for h in hosts:
                print str(h)
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)

    def test_simple_create(self):
        """
        Test EMCVmaxBlockDeviceAPI create a volume
        """
        print "\ntest_simple_create"

        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            block = block_device_api.create_volume(uuid4(), block_device_api.allocation_unit())
            print 'uuid = ' + block.blockdevice_id + ' size = ' + str(block.size)
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)

    def test_create_with_profile(self):
        """
        Test EMCVmaxBlockDeviceAPI create a volume for each defined profile
        """
        print "\ntest_create_with_profile"

        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            for profile in (c.value for c in MandatoryProfiles.iterconstants()):
                block = block_device_api.create_volume_with_profile(uuid4(),
                                                                    block_device_api.allocation_unit(), profile)
                print 'uuid = ' + block.blockdevice_id + ' profile = ' + str(profile) \
                      + ' size = ' + str(block.size)
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)

    def test_simple_attach(self):
        """
        Test EMCVmaxBlockDeviceAPI attach a volume to this host, this host
        must be in agent.yml
        """
        print "\ntest_simple_attach"

        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            block = block_device_api.create_volume(uuid4(), block_device_api.allocation_unit())
            print 'uuid = ' + block.blockdevice_id + ' size = ' + str(block.size)
            vmax_host = block_device_api.compute_instance_id()
            block = block_device_api.attach_volume(block.blockdevice_id, vmax_host)
            print 'volume attached to = ' + str(block.attached_to)
            path = block_device_api.get_device_path(block.blockdevice_id)
            print 'device path is ' + str(path)
            output = block_device_api._execute_inq()
            print "inq output: \n%s" % str(output)
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)

    def test_inq_and_rescan(self):
        """
        Test EMCVmaxBlockDeviceAPI Test inquiry and rescan commands
        """
        print "\ntest_inq_and_rescan"

        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            output = block_device_api._execute_inq()
            print "inq output: \n%s" % str(output)
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)

    def test_get_not_exist(self):
        """
        Test EMCVmaxBlockDeviceAPI Test getting a non existent volume fails
        """
        print "\ntest_get_not_exist"

        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            block_device_api.get_device_path(u'99999')
            self.fail('No exception thrown')
        except UnknownVolume as ue:
            print 'UnknownVolume: ' + str(ue)
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)

    def test_list_all(self):
        """
        Test EMCVmaxBlockDeviceAPI List all volumes in database
        """
        print "\ntest_list_all"

        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            blocks = block_device_api.list_volumes()
            for b in blocks:
                print 'uuid = ' + b.blockdevice_id + ' size = ' + str(b.size)
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)
