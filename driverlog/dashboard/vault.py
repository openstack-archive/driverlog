# Copyright (c) 2014 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import re

import flask
import memcache

from driverlog.dashboard import memory_storage
from driverlog.openstack.common import log as logging


LOG = logging.getLogger(__name__)


LEVELS = [
    {
        'level_id': 'self_verification',
        'level_name': 'self-verification',
    },
    {
        'level_id': '3rd_party_verification',
        'level_name': '3rd-party verification',
    },
    {
        'level_id': 'external_ci_verification',
        'level_name': 'verified by external CI'
    }
]


def _build_levels_map():
    levels_map = dict()
    index = 1
    for level in LEVELS:
        level['level'] = index
        levels_map[level['level_id']] = level
        index += 1
    return levels_map


def _build_projects_map(default_data):
    projects_map = {}
    for project in default_data['projects']:
        projects_map[project['id']] = project
    return projects_map


def _build_releases_map(default_data):
    releases_map = {}
    for release in default_data['releases']:
        releases_map[release['id']] = release
    return releases_map


def _extend_drivers_info():
    for driver in get_vault()['drivers_map'].values():
        releases_info = []
        for release in driver['os_versions_map'].keys():
            release = release.lower()
            if release.find('/') > 0:
                release = release.split('/')[1]
            if release == 'master':
                release = get_vault()['default_data']['releases'][-1]['id']
            if release in get_vault()['releases_map']:
                releases_info.append(
                    {
                        'release_id': release.lower(),
                        'name': release.capitalize(),
                        'wiki': get_vault()['releases_map'][release]['wiki']
                    })
        driver['releases_info'] = sorted(releases_info,
                                         key=lambda x: x['name'])


def _build_drivers_map(default_data, levels_map, projects_map):

    driver_map = {}

    for driver in default_data['drivers']:

        driver['project_name'] = projects_map[driver['project_id']]['name']
        driver['os_versions_map'] = {}

        max_level = LEVELS[0]
        for os_version in driver['os_versions']:
            level = levels_map[os_version['verification']]
            os_version['verification_name'] = level['level_name']
            os_version['level'] = level['level']
            if 'os_version' not in os_version:
                os_version['os_version'] = 'master'

            if level['level'] > max_level['level']:
                max_level = level
                max_level['os_version'] = os_version['os_version']

            driver['os_versions_map'][os_version['os_version']] = os_version

        driver.update(max_level)

        key = (driver['project_id'].lower(),
               driver['vendor'].lower(),
               driver['name'].lower())
        driver_map[key] = driver

    return driver_map


def get_vault():
    vault = getattr(flask.current_app, 'driverlog_vault', None)
    if not vault:
        try:
            vault = {}
            vault['memory_storage'] = memory_storage.get_memory_storage(
                memory_storage.MEMORY_STORAGE_CACHED)

            if 'CONF' not in flask.current_app.config:
                LOG.critical('Configure environment variable DRIVERLOG_CONF '
                             'with path to config file')
                flask.abort(500)

            conf = flask.current_app.config['CONF']

            levels_map = _build_levels_map()
            vault['levels_map'] = levels_map

            MEMCACHED_URI_PREFIX = r'^memcached:\/\/'
            stripped = re.sub(MEMCACHED_URI_PREFIX, '',
                              conf.runtime_storage_uri)

            memcached_uri = stripped.split(',')
            memcached = memcache.Client(memcached_uri)
            vault['memcached'] = memcached

            flask.current_app.driverlog_vault = vault
        except Exception as e:
            LOG.critical('Failed to initialize application: %s', e)
            LOG.exception(e)
            flask.abort(500)

    if not getattr(flask.request, 'driverlog_updated', None):
        flask.request.driverlog_updated = True

        memcached = vault['memcached']
        hashes = memcached.get_multi(['default_data_hash', 'update_hash'],
                                     key_prefix='driverlog:')

        if vault.get('default_data_hash') != hashes.get('default_data_hash'):
            vault['default_data_hash'] = hashes['default_data_hash']
            vault['default_data'] = memcached.get('driverlog:default_data')

            projects_map = _build_projects_map(vault['default_data'])
            vault['projects_map'] = projects_map

            releases_map = _build_releases_map(vault['default_data'])
            vault['releases_map'] = releases_map

            drivers_map = _build_drivers_map(
                vault['default_data'], vault['levels_map'], projects_map)
            vault['drivers_map'] = drivers_map

            _extend_drivers_info()

        if vault.get('update_hash') != hashes.get('update_hash'):
            vault['update_hash'] = hashes['update_hash']
            update = memcached.get('driverlog:update')

            levels_map = vault['levels_map']

            for proj_vendor_driver, os_versions_map in update.iteritems():
                ovm = os_versions_map['os_versions_map']

                if proj_vendor_driver not in vault['drivers_map']:
                    LOG.info('Unknown driver %s, ignoring', proj_vendor_driver)
                else:
                    for os_version, info in ovm.iteritems():
                        level = levels_map[info['verification']]
                        info['verification_name'] = level['level_name']
                        info['level'] = level['level']

                    vault['drivers_map'][proj_vendor_driver][
                        'os_versions_map'].update(ovm)

            _extend_drivers_info()

        if not vault.get('default_data'):
            raise Exception('Memcached is not initialized. '
                            'Please run the processor')

    return vault


def get_memory_storage():
    return get_vault()['memory_storage']
