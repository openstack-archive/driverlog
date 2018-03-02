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
from driverlog.dashboard import parameters
from driverlog.dashboard import vault


blueprint = flask.Blueprint('api', __name__, url_prefix='/api/1.0')


def get_drivers_internal(**params):
    drivers = vault.get_vault()['drivers_map']
    filtered_drivers = []

    # when release_id is not set return only drivers from active releases
    if 'release_id' not in params:
        all_releases = vault.get_vault()['releases_map']
        active_releases = ','.join(sorted(
            r['id'].lower() for r in all_releases.values() if r.get('active')))
        params['release_id'] = active_releases

    for driver in drivers.values():
        include = True
        for param, value in params.iteritems():
            value = value.lower()
            if param == 'release_id' and value:
                query_releases = set(value.split(','))
                found = False
                for release in driver['releases_info']:
                    if release['release_id'] in query_releases:
                        found = True
                        break

                if not found:
                    include = False
                    break

            elif value and (driver.get(param) or '').lower() != value:
                include = False
                break

        if include:
            filtered_drivers.append(driver)

    return filtered_drivers


@blueprint.route('/drivers')
@decorators.jsonify('drivers')
@decorators.exception_handler()
def get_drivers():
    selected_project_id = (parameters.get_single_parameter({}, 'project_id') or
                           parameters.get_single_parameter({}, 'project_id'))
    selected_vendor = parameters.get_single_parameter({}, 'vendor')
    selected_release = (parameters.get_single_parameter({}, 'release_id') or
                        parameters.get_single_parameter({}, 'release'))

    return get_drivers_internal(project_id=selected_project_id,
                                vendor=selected_vendor,
                                release_id=selected_release)


@blueprint.route('/list/releases')
@decorators.jsonify('releases')
@decorators.exception_handler()
def get_releases():
    selected_vendor = parameters.get_single_parameter({}, 'vendor')
    selected_project_id = parameters.get_single_parameter({}, 'project_id')
    query = (parameters.get_single_parameter({}, 'query') or '').lower()

    releases = set()
    for driver in get_drivers_internal(vendor=selected_vendor,
                                       project_id=selected_project_id):
        for release in driver['releases_info']:
            if release['name'].lower().find(query) >= 0:
                releases.add(release['name'])

    releases = [{'id': release.lower(), 'text': release.capitalize()}
                for release in releases]

    return sorted(releases, key=lambda x: x['text'], reverse=True)


@blueprint.route('/list/releases/<release>')
@decorators.jsonify('release')
@decorators.exception_handler()
def get_release(release):
    return {'id': release.lower(), 'text': release.capitalize()}


@blueprint.route('/list/project_ids')
@decorators.jsonify('project_ids')
@decorators.exception_handler()
def get_project_ids():
    selected_vendor = parameters.get_single_parameter({}, 'vendor')
    selected_release_id = parameters.get_single_parameter({}, 'release_id')
    query = (parameters.get_single_parameter({}, 'query') or '').lower()

    projects_map = vault.get_vault()['projects_map']
    project_ids = set()
    for driver in get_drivers_internal(vendor=selected_vendor,
                                       release_id=selected_release_id):
        if projects_map[driver['project_id']]['name'].lower().find(query) >= 0:
            project_ids.add(driver['project_id'])

    projects = [{'id': project_id,
                 'text': projects_map[project_id]['name']}
                for project_id in project_ids]

    return sorted(projects, key=lambda x: x['text'])


@blueprint.route('/list/project_ids/<path:project_id>')
@decorators.jsonify('project_id')
@decorators.exception_handler()
def get_project_id(project_id):
    projects_map = vault.get_vault()['projects_map']
    if project_id in projects_map:
        return {'id': project_id, 'text': projects_map[project_id]['name']}
    else:
        flask.abort(404)


@blueprint.route('/list/vendors')
@decorators.jsonify('vendors')
@decorators.exception_handler()
def get_vendors():
    selected_project_id = parameters.get_single_parameter({}, 'project_id')
    selected_release_id = parameters.get_single_parameter({}, 'release_id')
    query = (parameters.get_single_parameter({}, 'query') or '').lower()

    vendors = set()
    for driver in get_drivers_internal(project_id=selected_project_id,
                                       release_id=selected_release_id):
        if driver['vendor'].lower().find(query) >= 0:
            vendors.add(driver['vendor'])

    vendors = [{'id': vendor, 'text': vendor} for vendor in vendors]
    return sorted(vendors, key=lambda x: x['text'])


@blueprint.route('/list/vendors/<path:vendor>')
@decorators.jsonify('vendor')
@decorators.exception_handler()
def get_vendor(vendor):
    return {'id': vendor, 'text': vendor}
