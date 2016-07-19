# Copyright (c) 2016 EMC Corporation, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

import storops
from storops import exception as storops_ex
from storops.vnx import enums as vnx_enums

import common
import exception
import utils

LOG = logging.getLogger(__name__)


class Condition(object):
    """Defines some condition checker which are used in wait_until, .etc."""

    @staticmethod
    def is_lun_io_ready(lun):
        utils.update_res_without_poll(lun)
        if not lun.existed:
            return False
        lun_state = lun.state
        if lun_state == common.LUNState.INITIALIZING:
            return False
        elif lun_state in [common.LUNState.READY,
                           common.LUNState.FAULTED]:
            return lun.operation == 'None'
        else:
            # Quick exit wait_until when the lun is other state to avoid
            # long-time timeout.
            msg = ('Volume %(name)s was created in VNX, '
                   'but in %(state)s state.'
                   % {'name': lun.name,
                      'state': lun_state})
            raise exception.VolumeBackendAPIException(data=msg)

    @staticmethod
    def is_object_existed(obj):
        utils.update_res_without_poll(obj)
        return obj.existed

    @staticmethod
    def is_lun_ops_ready(lun):
        utils.update_res_without_poll(lun)
        return 'None' == lun.operation

    @staticmethod
    def is_lun_expanded(lun, new_size):
        utils.update_res_without_poll(lun)
        return new_size == lun.total_capacity_gb


class VNXClient(object):
    def __init__(self, ip, username, password, scope=0,
                 naviseccli=None, sec_file=None):
        self.system = storops.VNXSystem(ip=ip,
                                        username=username,
                                        password=password,
                                        scope=scope,
                                        naviseccli=naviseccli,
                                        sec_file=sec_file)

    def get_target_property(self, storage_res, initiator):
        available_targets = self.system.get_iscsi_port()
        registered_ports = utils.get_registered_ports(
            available_targets, storage_res.get_ports(initiator))

        iqns = []
        portals = []
        if registered_ports:
            iqns = [port.wwn for port in registered_ports]
            portals = ["%s:3260" % port.ip_address
                       for port in registered_ports]
        else:
            LOG.warning('Failed to find available iSCSI targets for %s.',
                        storage_res.name)

        return iqns, portals

    def get_lun(self, name=None):
        return self.system.get_lun(name=name)

    def get_pool(self, name=None):
        return self.system.get_pool(name=name)

    def get_iscsi_targets(self, sp=None, port_id=None, vport_id=None):
        return self.system.get_iscsi_port(sp=sp, port_id=port_id,
                                          vport_id=vport_id,
                                          has_ip=True)

    def get_fc_targets(self, sp=None, port_id=None):
        return self.system.get_fc_port(sp=sp, port_id=port_id)

    def create_lun(self, pool, name, size, provision=None,
                   tier=None, cg_name=None, ignore_thresholds=False):
        pool = self.system.get_pool(name=pool)
        try:
            lun = pool.create_lun(lun_name=name,
                                  size_gb=size,
                                  provision=provision,
                                  tier=tier,
                                  ignore_thresholds=ignore_thresholds)
        except storops_ex.VNXLunNameInUseError:
            lun = self.system.get_lun(name=name)

        utils.wait_until(condition=Condition.is_lun_io_ready, lun=lun)
        if cg_name:
            cg = self.system.get_cg(name=cg_name)
            cg.add_member(lun)
        if provision is vnx_enums.VNXProvisionEnum.COMPRESSED:
            lun.enable_compression()
        return lun

    def create_storage_group(self, name):
        try:
            return self.system.create_sg(name)
        except storops_ex.VNXStorageGroupNameInUseError as ex:
            # Ignore the failure due to retry
            LOG.warning('Storage group %(name)s already exists. '
                        'Message: %(msg)s',
                        {'name': name, 'msg': ex.message})
            return self.system.get_sg(name=name)

    def get_storage_group(self, name=None):
        return self.system.get_sg(name)

    def register_initiator(self, storage_group, host_info, initiator_port_map):
        """Registers the initiators of `host` to the `storage_group`.

        :param storage_group: the storage group object.
        :param host_info: the ip and name information of the initiator.
        :param initiator_port_map: the dict specifying which initiators are
                                   bound to which ports.
        """
        for (initiator_id, ports_to_bind) in initiator_port_map.iteritems():
            for port in ports_to_bind:
                try:
                    storage_group.connect_hba(port, initiator_id,
                                              host_info.name,
                                              host_ip=host_info.ip)
                except storops_ex.VNXStorageGroupError as ex:
                    msg = ('Failed to set path to port %(port)s for '
                           'initiator %(hba_id)s. Message: %(msg)s' %
                           {'port': port,
                            'hba_id': initiator_id,
                            'msg': ex.message})
                    LOG.warning(msg)
                    pass  # Ignore the failure, just write a warning.
        if initiator_port_map:
            utils.update_res_with_poll(storage_group)

    def add_lun_to_sg(self, storage_group, lun, max_retries):
        """Adds the `lun` to `storage_group`."""
        try:
            return storage_group.attach_alu(lun, max_retries)
        except storops_ex.VNXAluAlreadyAttachedError:
            raise exception.VNXAluAlreadyAttachedError()
        except storops_ex.VNXNoHluAvailableError as ex:
            msg = ('Failed to add %(lun)s into %(sg)s after %(tried)s '
                   'tries. Reach the max retry times. Message: %(msg)s' %
                   {'lun': lun.lun_id,
                    'sg': storage_group.name,
                    'tried': max_retries,
                    'msg': ex.message})
            LOG.error(msg)
            raise ex

    def is_lun_destroyed(self, lun):
        return not lun.existed or lun.state in [common.LUNState.DESTROYING]
