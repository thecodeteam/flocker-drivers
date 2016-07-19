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
import time

import common
import exception
from lib import loopingcall

LOG = logging.getLogger(__name__)


def wait_until(condition, timeout=None, interval=common.INTERVAL_5_SEC,
               reraise_arbiter=lambda ex: True, *args, **kwargs):
    start_time = time.time()
    if not timeout:
        timeout = common.DEFAULT_TIMEOUT

    def _inner():
        try:
            ret = condition(*args, **kwargs)
        except Exception as ex:
            msg = ('Exception raised when executing %(condition_name)s '
                   'in wait_until. Message: %(msg)s' %
                   {'condition_name': condition.__name__,
                    'msg': ex.message})
            LOG.debug(msg)
            raise ex
        if ret:
            raise loopingcall.LoopingCallDone()

        if int(time.time()) - start_time > timeout:
            msg = ('Timeout waiting for %(condition_name)s in wait_until.'
                   % {'condition_name': condition.__name__})
            LOG.error(msg)
            raise exception.WaitUtilTimeoutException(msg)

    timer = loopingcall.FixedIntervalLoopingCall(_inner)
    timer.start(interval=interval).wait()


def update_res_without_poll(res):
    with res.with_no_poll():
        res.update()


def update_res_with_poll(res):
    with res.with_poll():
        res.update()


def get_registered_ports(available_ports, registered_ports):
    """Filters out the unregistered ports.

    Goes through the `available_ports`, and filters out the ones not
    registered (that is not in `registered_io_ports`).
    :param available_ports
    :param registered_ports
    return registered ports
    """
    valid_port_list = []
    for io_port in available_ports:
        if io_port not in registered_ports:
            msg = ('Skipped SP port %(port)s due to it is not registered. '
                   'The registered IO ports: %(reg_ports)s.' %
                   {'port': io_port,
                    'reg_ports': registered_ports})
            LOG.debug(msg)
        else:
            valid_port_list.append(io_port)
    return valid_port_list
