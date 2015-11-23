# Copyright 2015 EMC Corporation

import redis
from uuid import uuid4


class EmcFlockerDb(object):
    def __init__(self, host, port=6379, db=0, key="emc_flocker_hash"):
        self.host = host
        self.port = port
        self.db = db
        self.key = key
        self.redis = None

    def __del__(self):
        self._close_db()

    def _show_db(self):
        return unicode(self.redis)

    def _open_db(self):
        if self.redis is None:
            self.redis = redis.Redis(connection_pool=redis.ConnectionPool(host=self.host, port=self.port, db=self.db))

    def _close_db(self):
        if self.redis is not None:
            self.redis = None

    def _clear_all(self):
        self._open_db()
        uuids = self.redis.hkeys(self.key)
        for u in uuids:
            self.redis.hdel(self.key, u)

    def _get_uuid(self, name):
        self._open_db()

        row_uuid = None
        uuids = self.redis.hkeys(self.key)
        for u in uuids:
            volstr = self.redis.hget(self.key, u)
            if volstr is not None:
                volume = eval(volstr)
                if volume['name'] == name:
                    row_uuid = u
                    break
        return row_uuid

    def get_volume_by_uuid(self, row_uuid):
        self._open_db()

        volstr = self.redis.hget(self.key, row_uuid)
        if volstr is not None:
            volume = eval(volstr)
        else:
            volume = None
        return volume

    def get_volume_by_name(self, name):
        return self.get_volume_by_uuid(self._get_uuid(name))

    def get_all_volumes(self):
        self._open_db()

        volumes = []
        uuids = self.redis.hkeys(self.key)
        for u in uuids:
            volstr = self.redis.hget(self.key, u)
            if volstr is not None:
                volume = eval(volstr)
                volumes.append(volume)
        return volumes

    def add_volume(self, volume):
        self._open_db()

        volume['uuid'] = unicode(uuid4())
        self.redis.hset(self.key, volume['uuid'], unicode(volume))
        return volume['uuid']

    def delete_volume_by_id(self, row_uuid):
        self._open_db()
        self.redis.hdel(self.key, row_uuid)

    def delete_volume_by_name(self, name):
        return self.delete_volume_by_id(self._get_uuid(name))

    def update_volume_by_id(self, row_uuid, volume):
        self._open_db()
        self.redis.hset(self.key, row_uuid, unicode(volume))

    def update_volume_by_name(self, name, volume):
        self.update_volume_by_id(self._get_uuid(name), volume)
