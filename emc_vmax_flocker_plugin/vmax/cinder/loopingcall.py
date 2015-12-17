# Copyright Hybrid Logic Ltd.
# Copyright 2015 EMC Corporation
# See LICENSE file for details.

from threading import Event, Thread
import time
import calendar


class LoopingCallDone(Exception):
    def __init__(self, retvalue=True):
        self.retvalue = retvalue


class LoopingCallBase(object):
    def __init__(self, f=None, *args, **kw):
        self.args = args
        self.kw = kw
        self.f = f
        self._running = False
        self.retcode = None
        self.thread = None
        self.event = Event()

    def stop(self):
        self._running = False
        self.event.set()

    def wait(self):
        self.event.wait()
        return self.retcode


class FixedIntervalLoopingCall(LoopingCallBase):
    def start(self, interval, initial_delay=1):
        self._running = True
        self.event.clear()

        def _inner():
            time.sleep(initial_delay)

            try:
                while self._running:
                    start = calendar.timegm(time.gmtime())
                    self.f(*self.args, **self.kw)
                    end = calendar.timegm(time.gmtime())
                    if not self._running:
                        break
                    delay = interval - (end - start)
                    time.sleep(delay if delay > 0 else 0)
            except LoopingCallDone as e:
                self.retcode = e.retvalue
            except Exception as e:
                self.exception = e.message
                self.retcode = -1

            self.stop()

        self.thread = Thread(name='worker', target=_inner)
        self.thread.start()
        return self.thread
