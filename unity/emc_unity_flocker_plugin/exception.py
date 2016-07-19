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
import six
import sys

LOG = logging.getLogger(__name__)


class BaseException(Exception):
    """Base Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = "An unknown exception occurred."
    code = 500
    headers = {}
    safe = False

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs
        self.kwargs['message'] = message

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        for k, v in self.kwargs.items():
            if isinstance(v, Exception):
                self.kwargs[k] = six.text_type(v)

        if self._should_format():
            try:
                message = self.message % kwargs

            except Exception:
                exc_info = sys.exc_info()
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception('Exception in string format operation')
                for name, value in kwargs.items():
                    LOG.error("%(name)s: %(value)s",
                              {'name': name, 'value': value})
                # at least get the core message out if something happened
                message = self.message
        elif isinstance(message, Exception):
            message = six.text_type(message)

        self.msg = message
        super(BaseException, self).__init__(message)

    def _should_format(self):
        return self.kwargs['message'] is None or '%(message)' in self.message

    def __unicode__(self):
        return six.text_type(self.msg)


class VolumeBackendAPIException(BaseException):
    message = ("Bad or unexpected response from the storage volume "
               "backend API: %(data)s")


class InvalidParameterValue(BaseException):
    message = "Invalid parameter value."


class WaitUtilTimeoutException(VolumeBackendAPIException):
    """Raised when timeout occurs in wait_until."""
    pass


class LunNotAvailableException(VolumeBackendAPIException):
    message = 'Lun %(lun_id)s is not available'


class PoolNotAvailableException(VolumeBackendAPIException):
    message = 'Pool %(lun_id)s is not available'


class InvalidProtocol(VolumeBackendAPIException):
    message = 'Invalid protocol %(proto)s'


class NoFibreChannelHostsFound(VolumeBackendAPIException):
    message = "Unable to locate any Fibre Channel devices."


class NoFibreChannelVolumeDeviceFound(VolumeBackendAPIException):
    message = "Unable to find a Fibre Channel volume device."


class VolumeDeviceNotFound(VolumeBackendAPIException):
    message = "Volume device not found at %(device)s."


class VolumePathNotRemoved(VolumeBackendAPIException):
    message = "Volume path %(volume_path)s was not removed in time."


class UnityAluAlreadyAttachedError(VolumeBackendAPIException):
    message = ("LUN already exists in the specified host. "
               "Requested LUN has already been added to this host")


class UnityMultipleHostError(VolumeBackendAPIException):
    message = "Multiple host with same name found in system."
