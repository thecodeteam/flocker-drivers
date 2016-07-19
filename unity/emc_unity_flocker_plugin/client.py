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
from storops.unity import enums as unity_enums

import exception
import utils

LOG = logging.getLogger(__name__)


class Condition(object):
    """Defines some condition checker which are used in wait_until, .etc."""

    @staticmethod
    def is_lun_io_ready(lun):
        lun.update()
        if not lun.existed:
            return False
        lun_state = lun.health
        if not lun_state:
            return False
        if lun_state.value == unity_enums.HealthEnum.OK_BUT:
            return False
        elif lun_state.value == unity_enums.HealthEnum.OK:
            return True
        else:
            # Quick exit wait_until when the lun is other state to avoid
            # long-time timeout.
            msg = ('Volume %(name)s was created in Unity, '
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


class UnityClient(object):
    def __init__(self, ip, username, password):
        self.system = storops.UnitySystem(host=ip,
                                          username=username,
                                          password=password)

    def get_lun(self, name=None):
        try:
            return self.system.get_lun(name=name)
        except storops_ex.UnityResourceNotFoundError as ex:
            LOG.debug('Lun %(name)s is not found. Message: %(msg)s',
                      {'name': name, 'msg': ex.message})
            return None

    def get_pool(self, name=None):
        return self.system.get_pool(name=name)

    def get_target_property(self, storage_res, initiator):
        iqns = []
        portals = []
        iscsi_portals = self.system.get_iscsi_portal()
        if not iscsi_portals:
            return (iqns, portals)

        nodes = map(lambda p: p.iscsi_node, iscsi_portals)
        iqns = map(lambda n: n.name, nodes)
        portals = ["%s:3260" % portal.ip_address for
                   portal in iscsi_portals]

        return (iqns, portals)

    def create_lun(self, pool, name, size, **kwargs):
        pool = self.system.get_pool(name=pool)
        try:
            lun = pool.create_lun(lun_name=name,
                                  size_gb=size, **kwargs)
        except storops_ex.UnityLunNameInUseError:
            lun = self.system.get_lun(name=name)

        utils.wait_until(condition=Condition.is_lun_io_ready, lun=lun)
        return lun

    def create_host(self, name):
        try:
            return self.system.create_host(name)
        except storops_ex.UnityHostNameInUseError as ex:
            # Ignore the failure due to retry
            LOG.warning('Host %(name)s already exists. Message: %(msg)s',
                        {'name': name, 'msg': ex.message})
            return self.system.get_host(name=name)

    def get_iscsi_targets(self):
        return self.system.get_iscsi_portal()

    def get_fc_targets(self, sp=None, port_id=None):
        return self.system.get_fc_port(sp=sp, port_id=port_id)

    def get_host(self, name=None):
        host = []
        try:
            # It will return all existed host when name is None
            host = self.system.get_host(name=name)
        except storops_ex.UnityResourceNotFoundError as ex:
            if name:
                LOG.warning('host %s not found' % name)
        except storops_ex.UnityNameNotUniqueError as ex:
            host_ids = " ".join(map(lambda x: x.id, ex.objects))
            LOG.warning('Multiple host with %s ids found' % host_ids)
            raise exception.UnityMultipleHostError()

        return host

    def add_lun_to_host(self, host, lun):
        """Adds the `lun` to `host`. """
        try:
            return host.attach_alu(lun)
        except storops_ex.UnityAluAlreadyAttachedError:
            raise exception.UnityAluAlreadyAttachedError()
        except storops_ex.UnityAttachAluError as ex:
            msg = ('Failed to add %(lun)s into %(sg)s. Message: %(msg)s' %
                   {'lun': lun.id,
                    'sg': host.name,
                    'msg': ex.message})
            LOG.error(msg)

    def is_lun_destroyed(self, lun):
        if not lun:
            return True
        return not lun.existed

    def get_capability_profiles(self, usage_tags=None):
        return self.system.get_capability_profile(usage_tags=usage_tags)
