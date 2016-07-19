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
"""
Unity Common Utils
"""

DEFAULT_TIMEOUT = 60 * 24 * 365

INTERVAL_5_SEC = 5
INTERVAL_20_SEC = 20
INTERVAL_30_SEC = 30
INTERVAL_60_SEC = 60

PROTOCOL_FC = 'FC'
PROTOCOL_ISCSI = 'iSCSI'


class LUNState(object):
    INITIALIZING = 'Initializing'
    READY = 'Ready'
    FAULTED = 'Faulted'
    DESTROYING = 'Destroying'


class UnityEnablerStatus(object):
    def __init__(self, fast=False, thin=False, snap=False):
        self.fast_enabled = fast
        self.thin_enabled = thin
        self.snap_enabled = snap


class Host(object):
    """The model of a host which acts as an initiator to access the storage."""

    def __init__(self, name, initiators, ip=None, initiator_type='iSCSI'):

        if not name:
            raise ValueError('Name of host cannot be empty.')
        self.name = name

        if not initiators:
            raise ValueError('Initiators of host cannot be empty.')
        self.initiators = initiators

        self.ip = ip
        self.initiator_type = initiator_type
        super(Host, self).__init__()

    def to_dict(self):
        """Converts to the dict.

        It helps serialize and deserialize the data before returning to nova.
        """
        return {key: value for (key, value) in self.__dict__.items()}


class ISCSITargetData(dict):
    def __init__(self, iqn=None, iqns=None, portal=None, portals=None,
                 lun=None, luns=None):
        data = dict()
        data['target_iqn'] = iqn
        data['target_portal'] = portal
        data['target_lun'] = lun
        data['target_iqns'] = iqns
        data['target_portals'] = portals
        data['target_luns'] = luns

        self['data'] = data
        self['driver_volume_type'] = 'iscsi'
        super(ISCSITargetData, self).__init__()

    def to_dict(self):
        """Converts to the dict.

        It helps serialize and deserialize the data before returning to nova.
        """
        return {key: value for (key, value) in self.iteritems()}


class FCTargetData(dict):
    def __init__(self, wwn=None, hlu=None):
        data = dict()
        data['target_lun'] = hlu
        data['target_wwn'] = wwn

        self['driver_volume_type'] = 'fibre_channel'
        self['data'] = data
        super(FCTargetData, self).__init__()

    def to_dict(self):
        """Converts to the dict.

        It helps serialize and deserialize the data before returning to nova.
        """
        return {key: value for (key, value) in self.iteritems()}
