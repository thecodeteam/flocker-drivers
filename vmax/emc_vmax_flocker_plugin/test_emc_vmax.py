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
from flocker.node.agents.blockdevice import UnknownVolume

from emc_vmax_flocker_plugin.testtools_emc_vmax import tidy_vmax_client_for_test, vmax_allocation_unit
from flocker.node.agents.test.test_blockdevice import make_iblockdeviceapi_tests


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
    Interface adherence Tests for ``EMCVmaxBlockDeviceAPI``
    """


# TODO EBS and Cinder implementations move the below tests up
# into <Driver>BlockDeviceAPIInterfaceTests
# See https://github.com/ClusterHQ/flocker/blob/master
#         /flocker/node/agents/functional/test_ebs.py#L84
# as an example
class EMCVmaxBlockDeviceAPIImplementationTests(SynchronousTestCase):
    """
    Implementation specific tests for ``EMCVmaxBlockDeviceAPI``.
    """
    def test_login(self):
        """
        Test EMCVmaxBlockDeviceAPI Login
        """
        print "\ntest_login"
        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            print 'symm info = %s' % block_device_api.get_volume_stats()
            print 'symmetrix id = %s' % block_device_api._get_symmetrix_id()
            print 'allocation unit = %s' % str(block_device_api.allocation_unit())
            self.assertTrue(block_device_api._has_connection())
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)

    def test_flocker_db(self):
        """
        Test EMCVmaxBlockDeviceAPI redis db
        """
        print "\ntest_flocker_db"
        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            dbconn = block_device_api.dbconn

            volume = eval("{'name': u'FFC08', 'attach_to': None, "
                          "'provider_location': u\"{'classname': u'Symm_StorageVolume', "
                          "'keybindings': {'CreationClassName': u'Symm_StorageVolume', "
                          "'SystemName': u'SYMMETRIX+000198700440', 'DeviceID': u'FFC08', "
                          "'SystemCreationClassName': u'Symm_StorageSystem'}, 'version': '0.0.1'}\", "
                          "'host': 'rodgek-localdomain@Backend#SATA_BRONZ1+000198700440', "
                          "'id': u'cada636d-f287-44b6-8eb8-c914d37f9788', 'size': 960}")
            uuid = dbconn.add_volume(volume)
            print uuid + ' added'

            volumes = dbconn.get_all_volumes()
            for v in volumes:
                if v['uuid'] == volume['uuid']:
                    print uuid + ' found by get_all_volumes()'
                    for key in v:
                        if v[key] != volume[key]:
                            self.fail("key mismatch " + key)
                break
            else:
                self.fail(uuid + ": entry not found")

            dbconn.delete_volume_by_id(uuid)
            print uuid + ' removed'

        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)

    def test_get_vmax_hosts(self):
        print "\ntest_get_vmax_hosts"

        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            host_id = block_device_api.compute_instance_id()
            print str(host_id)
            hosts = block_device_api.get_vmax_hosts()
            for h in hosts:
                print str(h)
            print block_device_api._generate_host()
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)

    def test_simple_create(self):
        print "\ntest_simple_create"

        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            block = block_device_api.create_volume(uuid4(), block_device_api.allocation_unit())
            print 'db connection = ' + block_device_api.dbconn._show_db()
            print 'uuid = ' + block.blockdevice_id + ' size = ' + str(block.size)
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)

    def test_simple_attach(self):
        print "\ntest_simple_attach"

        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            block = block_device_api.create_volume(uuid4(), block_device_api.allocation_unit())
            print 'db connection = ' + block_device_api.dbconn._show_db()
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
        print "\ntest_inq_and_rescan"

        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            output = block_device_api._execute_inq()
            print "inq output: \n%s" % str(output)
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)

    def test_get_not_exist(self):
        print "\ntest_get_not_exist"

        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            block_device_api.get_device_path(unicode('99999'))
            self.fail('No exception thrown')
        except UnknownVolume as ue:
            print 'UnknownVolume: ' + str(ue)
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)

    def test_list_all(self):
        print "\ntest_list_all"

        try:
            block_device_api = emcvmaxblockdeviceapi_for_test(self)
            blocks = block_device_api.list_volumes()
            for b in blocks:
                print 'uuid = ' + b.blockdevice_id + ' size = ' + str(b.size)
        except Exception as e:
            traceback.print_exc()
            self.fail(e.message)
