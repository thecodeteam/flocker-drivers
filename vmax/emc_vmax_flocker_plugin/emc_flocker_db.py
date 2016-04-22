# Copyright Hybrid Logic Ltd.
# Copyright 2015 EMC Corporation
# See LICENSE file for details.

import redis
from uuid import uuid4


class EmcFlockerDb(object):
    def __init__(self, host, port=6379, key="emc_flocker_hash"):
        """

        :param host: database host
        :param port: database port default 6397
        :param key: hash set name default emc_flocker_hash
        """
        self.host = host
        self.port = port
        self.key = key
        self.redis = None

    def __del__(self):
        """
        Close database on delete of object
        :return:
        """
        self._close_db()

    def _show_db(self):
        """
        Returns string representation of redis database connection
        :return:
        """
        return unicode(self.redis)

    def _open_db(self):
        """
        Opens/reopens database if necessary
        :return:
        """
        if self.redis is None:
            self.redis = redis.Redis(connection_pool=redis.ConnectionPool(host=self.host, port=self.port, db=0))

    def _close_db(self):
        """
        Closes database
        :return:
        """
        if self.redis is not None:
            self.redis = None

    def _clear_all(self):
        """
        Removes all keys from hash set
        :return:
        """
        self._open_db()
        uuids = self.redis.hkeys(self.key)
        for u in uuids:
            self.redis.hdel(self.key, u)

    def _get_uuid(self, volume_name):
        """
        Returns UUID corresponding to specified volume name
        :param volume_name:
        :return:
        UUID for volume name or None if not found
        """
        self._open_db()

        row_uuid = None
        uuids = self.redis.hkeys(self.key)
        for u in uuids:
            volstr = self.redis.hget(self.key, u)
            if volstr is not None:
                volume = eval(volstr)
                if volume['name'] == volume_name:
                    row_uuid = u
                    break
        return row_uuid

    def get_volume_by_uuid(self, row_uuid):
        """
        Return volume dictionary for specified UUID
        :param row_uuid:
        :return:
        volume dictionary or None if not found
        """
        self._open_db()

        volstr = self.redis.hget(self.key, row_uuid)
        if volstr is not None:
            volume = eval(volstr)
        else:
            volume = None
        return volume

    def get_volume_by_name(self, volume_name):
        """
        Return volume dictionary for specified volume name
        :param volume_name:
        :return:
        volume dictionary or None if not found
        """
        return self.get_volume_by_uuid(self._get_uuid(volume_name))

    def get_all_volumes(self):
        """
        Return a list of all volume dictionaries
        :return:
        list of all volume dictionaries
        """
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
        """
        Add a volume dictionary to the hash set, auto generate UUID
        :param volume: volume dictionary
        :return:
        hash set key or UUID generated for volume dictionary
        """
        self._open_db()

        volume['uuid'] = unicode(uuid4())
        self.redis.hset(self.key, volume['uuid'], unicode(volume))
        return volume['uuid']

    def delete_volume_by_id(self, row_uuid):
        """
        Delete volume from hash set by UUID
        :param row_uuid:
        :return:
        """
        self._open_db()
        self.redis.hdel(self.key, row_uuid)

    def delete_volume_by_name(self, volume_name):
        """
        Delete volume from hash set by volume name
        :param volume_name:
        :return:
        """
        return self.delete_volume_by_id(self._get_uuid(volume_name))

    def update_volume_by_id(self, row_uuid, volume):
        """
        Update/replace volume dictionary by UUID
        :param row_uuid: UUID
        :param volume: volume dictionary
        :return:
        """
        self._open_db()
        self.redis.hset(self.key, row_uuid, unicode(volume))

    def update_volume_by_name(self, volume_name, volume):
        """
        Update/replace volume dictionary by volume name
        :param volume_name: volume name
        :param volume: volume dictionary
        :return:
        """
        self.update_volume_by_id(self._get_uuid(volume_name), volume)
