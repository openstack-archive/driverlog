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
@decorators.exception_handler()
@decorators.templated()
def summary():
    pass


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
