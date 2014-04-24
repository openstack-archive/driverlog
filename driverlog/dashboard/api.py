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

import flask

from driverlog.dashboard import decorators
from driverlog.dashboard import vault


blueprint = flask.Blueprint('api', __name__, url_prefix='/api/1.0')


@blueprint.route('/records')
@decorators.jsonify()
@decorators.exception_handler()
def get_records():
    return [
        {
            'driver': 'SolidFire',
            'project': 'openstack/cinder',
            'branch': 'master',
            'timestamp': 1234567890,
            'success': True,
            'endpoint': 'create_volume',
            'passed_tests': [
                'test_volume_create'
            ],
            'failed_tests': [
            ]
        },
        {
            'driver': 'SolidFire',
            'project': 'openstack/cinder',
            'branch': 'master',
            'timestamp': 1234567890,
            'success': True,
            'endpoint': 'list_volume',
            'passed_tests': [
                'test_volume_list', 'test_volume_list_with_paging'
            ],
            'failed_tests': [
            ]
        },
        {
            'driver': 'Ceph',
            'project': 'openstack/cinder',
            'branch': 'stable/havana',
            'timestamp': 1234567890,
            'success': False,
            'endpoint': 'create_volume',
            'passed_tests': [
            ],
            'failed_tests': [
                'test_volume_create'
            ]
        }
    ]


def _extend_driver_info(driver):
    releases_info = []
    for release in driver['os_versions_map'].keys():
        release = release.lower()
        if release.find('/') > 0:
            release = release.split('/')[1]
        if release == 'master':
            release = vault.get_vault()['default_data']['releases'][-1]['id']
        if release in vault.get_vault()['releases_map']:
            releases_info.append(
                {
                    'name': release.capitalize(),
                    'wiki': vault.get_vault()['releases_map'][release]['wiki']
                })
    driver['releases_info'] = sorted(releases_info, key=lambda x: x['name'])


def get_drivers_internal(**params):
    drivers = vault.get_vault()['drivers_map']
    filtered_drivers = []

    for driver in drivers.values():
        include = True
        for param, value in params.iteritems():
            if param == 'release_id' and value:
                found = False
                for release in driver['releases_info']:
                    if release['release_id'] == value:
                        found = True
                        break

                if not found:
                    include = False
                    break

            elif value and driver.get(param) != value:
                include = False
                break

        if include:
            filtered_drivers.append(driver)

    return filtered_drivers


@blueprint.route('/drivers')
@decorators.jsonify('drivers')
@decorators.exception_handler()
def get_drivers():
    return get_drivers_internal()
