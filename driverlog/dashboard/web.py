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

import flask
from oslo_config import cfg
from oslo_log import log as logging

from driverlog.dashboard import api
from driverlog.processor import config


# Application objects ---------

app = flask.Flask(__name__)
app.register_blueprint(api.blueprint)

LOG = logging.getLogger(__name__)

conf = cfg.CONF
conf.register_opts(config.OPTS)


def main():
    logging.register_options(conf)
    logging.set_defaults()

    conf_file = os.getenv('DRIVERLOG_CONF')
    if conf_file and os.path.isfile(conf_file):
        conf(default_config_files=[conf_file])
        app.config['DEBUG'] = cfg.CONF.debug
        LOG.info('DriverLog.dashboard is configured via "%s"', conf_file)
    else:
        conf(project='driverlog')

    logging.setup(conf, 'driverlog')

    app.run(cfg.CONF.listen_host, cfg.CONF.listen_port)

if __name__ == '__main__':
    main()
