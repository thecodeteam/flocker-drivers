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
import exception


class PoolScheduler(object):
    def __init__(self, client):
        self.client = client

    def _filter_one(self, pools, filter_properties):
        selected_pool = None
        size = filter_properties.get('size')

        for pool in pools:
            if pool.size_free < size:
                continue
            if (selected_pool is not None and
                    selected_pool.size_free > pool.size_free):
                continue
            else:
                selected_pool = pool

        if selected_pool is None:
            msg = ('No available pool to create a volume which size is '
                   '%(vol_size)s. All available pools are %(pools)s'
                   % {'vol_size': size,
                      'pools': pools})

            raise exception.VolumeBackendAPIException(data=msg)

        return selected_pool


class CapacityPoolScheduler(PoolScheduler):
    def __init__(self, client):
        super(CapacityPoolScheduler, self).__init__(client)

    def filter_one(self, pools, filter_properties):
        return self._filter_one(pools, filter_properties)


class ProfileBasePoolScheduler(PoolScheduler):
    ussage_tag_map = {
        'BRONZE': 'flocker_bronze',
        'SILVER': 'flocker_silver',
        'GOLD': 'flocker_gold',
    }

    def __init__(self, client):
        super(ProfileBasePoolScheduler, self).__init__(client)

    def filter_one(self, pools, filter_properties):
        profile_name = filter_properties.get('profile_name', 'BRONZE').upper()

        profiles = self.client.get_capability_profiles(
            usage_tags=self.ussage_tag_map[profile_name])

        pool_candidates = [profile.pool for profile in profiles
                           if profile.pool.id in map(lambda x: x.id, pools)]

        return self._filter_one(pool_candidates, filter_properties)
