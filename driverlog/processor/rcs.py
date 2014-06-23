# Copyright (c) 2013 Mirantis Inc.
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

import json
import re

import paramiko
import six

from driverlog.openstack.common import log as logging


LOG = logging.getLogger(__name__)

DEFAULT_PORT = 29418
GERRIT_URI_PREFIX = r'^gerrit:\/\/'
PAGE_LIMIT = 5


class Rcs(object):
    def __init__(self, uri):
        pass

    def setup(self, **kwargs):
        pass

    def log(self, params):
        return []

    def close(self):
        pass


class Gerrit(Rcs):
    def __init__(self, uri):
        super(Gerrit, self).__init__(uri)

        stripped = re.sub(GERRIT_URI_PREFIX, '', uri)
        if stripped:
            self.hostname, semicolon, self.port = stripped.partition(':')
            if not self.port:
                self.port = DEFAULT_PORT
        else:
            raise Exception('Invalid rcs uri %s' % uri)

        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def setup(self, **kwargs):
        if 'key_filename' in kwargs:
            self.key_filename = kwargs['key_filename']
        else:
            self.key_filename = None

        if 'username' in kwargs:
            self.username = kwargs['username']
        else:
            self.username = None

        return self._connect()

    def _connect(self):
        try:
            self.client.connect(self.hostname, port=self.port,
                                key_filename=self.key_filename,
                                username=self.username)
            LOG.debug('Successfully connected to gerrit')
            return True
        except Exception as e:
            LOG.error('Failed to connect to gerrit %(host)s:%(port)s. '
                      'Error: %(err)s', {'host': self.hostname,
                                         'port': self.port, 'err': e})
            LOG.exception(e)
            return False

    def _get_cmd(self, params, sort_key=None):
        params['limit'] = params.get('limit', PAGE_LIMIT)
        params_str = ' '.join([('%s:\'%s\'' % (k, v))
                               for k, v in six.iteritems(params)])

        cmd = ('gerrit query --format JSON '
               '%(params)s '
               '--current-patch-set --patch-sets --comments ' %
               {'params': params_str})
        if sort_key:
            cmd += ' resume_sortkey:%016x' % sort_key
        return cmd

    def _exec_command(self, cmd):
        try:
            return self.client.exec_command(cmd)
        except Exception as e:
            LOG.error('Error %(error)s while execute command %(cmd)s',
                      {'error': e, 'cmd': cmd})
            LOG.exception(e)
            return False

    def log(self, params):
        sort_key = None

        while True:
            cmd = self._get_cmd(params, sort_key=sort_key)
            LOG.debug('Executing command: %s', cmd)
            exec_result = self._exec_command(cmd)
            if not exec_result:
                break
            stdin, stdout, stderr = exec_result

            proceed = False
            for line in stdout:
                review = json.loads(line)

                if 'sortKey' in review:
                    sort_key = int(review['sortKey'], 16)
                    proceed = True
                    yield review

            if not proceed:
                break

    def close(self):
        self.client.close()


def get_rcs(uri):
    LOG.debug('Review control system is requested for uri %s' % uri)
    match = re.search(GERRIT_URI_PREFIX, uri)
    if match:
        return Gerrit(uri)
    else:
        LOG.warning('Unsupported review control system, fallback to dummy')
        return Rcs(uri)
