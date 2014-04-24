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

import jsonschema
import testtools


def _compare_drivers(x, y):
    if x['project_id'] != y['project_id']:
        return ((x['project_id'] > y['project_id']) -
                (x['project_id'] < y['project_id']))

    return (x['vendor'] > y['vendor']) - (x['vendor'] < y['vendor'])


class TestConfigFiles(testtools.TestCase):
    def setUp(self):
        super(TestConfigFiles, self).setUp()

    def _read_file(self, file_name):
        with open(file_name, 'r') as content_file:
            content = content_file.read()
            return json.loads(content)

    def _verify_ordering(self, array,
                         comparator=lambda x, y: (x > y) - (x < y), msg=''):
        diff_msg = ''
        for i in range(len(array) - 1):
            if comparator(array[i], array[i + 1]) > 0:
                diff_msg = ('Order fails at index %(index)s, '
                            'elements:\n%(first)s:\n%(second)s' %
                            {'index': i, 'first': array[i],
                             'second': array[i + 1]})
                break
        if diff_msg:
            self.fail(msg + '\n' + diff_msg)

    def _verify_default_data_by_schema(self, file_name):
        default_data = self._read_file(file_name)
        schema = self._read_file('etc/default_data.schema.json')
        try:
            jsonschema.validate(default_data, schema)
        except Exception as e:
            self.fail(e)

    def test_default_data_schema_conformance(self):
        self._verify_default_data_by_schema('etc/default_data.json')

    def test_projects_in_alphabetical_order(self):
        projects = self._read_file('etc/default_data.json')['projects']
        self._verify_ordering(
            projects,
            comparator=lambda x, y: (x['id'] > y['id']) - (x['id'] < y['id']),
            msg='List of projects should be ordered by their ids')

    def test_drivers_in_alphabetical_order(self):
        drivers = self._read_file('etc/default_data.json')['drivers']
        self._verify_ordering(
            drivers,
            comparator=_compare_drivers,
            msg='List of drivers should be ordered by project_id, vendor '
                'and name')
