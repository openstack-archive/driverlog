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

import os
import urllib

import flask
from flask.ext import gravatar as gravatar_ext
from oslo.config import cfg
import six

from driverlog.dashboard import api
from driverlog.dashboard import decorators
from driverlog.dashboard import parameters
from driverlog.dashboard import vault
from driverlog.openstack.common import log as logging
from driverlog.processor import config


# Application objects ---------

app = flask.Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('DASHBOARD_CONF', silent=True)
app.config['APPLICATION_ROOT'] = '/myapp'
app.register_blueprint(api.blueprint)

LOG = logging.getLogger(__name__)

conf = cfg.CONF
conf.register_opts(config.OPTS)
logging.setup('dashboard')
LOG.info('Logging enabled')

conf_file = os.getenv('DRIVERLOG_CONF')
if conf_file and os.path.isfile(conf_file):
    conf(default_config_files=[conf_file])
    app.config['DEBUG'] = cfg.CONF.debug
    app.config['CONF'] = cfg.CONF
else:
    LOG.info('Conf file is empty or not exist')


# Handlers ---------

@app.route('/')
@decorators.templated()
def summary():
    selected_project_id = parameters.get_single_parameter({}, 'project_id')
    selected_vendor = parameters.get_single_parameter({}, 'vendor')
    selected_level_id = parameters.get_single_parameter({}, 'level_id')

    drivers = api.get_drivers_internal(project_id=selected_project_id,
                                       vendor=selected_vendor,
                                       level_id=selected_level_id)
    vendors = set()
    levels_id = set()
    projects_id = set()

    for driver in api.get_drivers_internal(project_id=selected_project_id,
                                           level_id=selected_level_id):
        vendors.add(driver['vendor'])

    for driver in api.get_drivers_internal(project_id=selected_project_id,
                                           vendor=selected_vendor):
        levels_id.add(driver['level_id'])

    for driver in api.get_drivers_internal(vendor=selected_vendor,
                                           level_id=selected_level_id):
        projects_id.add(driver['project_id'])

    projects_map = vault.get_vault()['projects_map']
    projects = [{'project_id': project_id,
                 'project_name': projects_map[project_id]['name']}
                for project_id in projects_id]

    levels_map = vault.get_vault()['levels_map']
    levels = [{'level_id': level_id,
               'level_name': levels_map[level_id]['level_name']}
              for level_id in levels_id]

    if selected_project_id not in projects_map:
        selected_project_id = None

    if selected_vendor not in vendors:
        selected_vendor = None

    if selected_level_id not in levels_map:
        selected_level_id = None

    return {
        'drivers': drivers,
        'vendors': sorted(vendors),
        'levels': sorted(levels, key=lambda x: x['level_name']),
        'projects': sorted(projects, key=lambda x: x['project_name']),
        'project_id': selected_project_id,
        'vendor': selected_vendor,
        'level_id': selected_level_id,
    }


@app.route('/details')
@decorators.templated()
def details():

    project_id = flask.request.args.get('project_id') or ''
    vendor = flask.request.args.get('vendor') or ''
    driver_name = flask.request.args.get('driver_name') or ''

    drivers_map = vault.get_vault()['drivers_map']
    key = (urllib.unquote_plus(project_id).lower(),
           urllib.unquote_plus(vendor).lower(),
           urllib.unquote_plus(driver_name).lower())
    if key not in drivers_map:
        flask.abort(404)

    driver = drivers_map[key]
    os_versions_list = []
    for os_version, os_version_info in driver['os_versions_map'].iteritems():
        os_version_info['os_version'] = os_version
        os_versions_list.append(os_version_info)

    sorted(os_versions_list, key=lambda x: x['os_version'])
    driver['os_versions'] = os_versions_list

    return {
        'driver': driver,
    }


@app.errorhandler(404)
@decorators.templated('404.html', 404)
def page_not_found(e):
    pass


# AJAX Handlers ---------


gravatar = gravatar_ext.Gravatar(app, size=64, rating='g', default='wavatar')


@app.template_filter('make_url')
def to_url_params(dict_params, base_url):
    return base_url + '?' + '&'.join(
        ['%s=%s' % (k, v) for k, v in six.iteritems(dict_params)])


@app.template_filter('join_plus')
def filter_join_plus(value, separator, field=None):
    if field:
        return separator.join([item[field] for item in value])
    else:
        return separator.join(value)


def main():
    app.run(cfg.CONF.listen_host, cfg.CONF.listen_port)

if __name__ == '__main__':
    main()
