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

import json

from driverlog.processor import main

import testtools


class TestMain(testtools.TestCase):
    def setUp(self):
        super(TestMain, self).setUp()

        with open('tests/unit/test_data/sample_review.json') as fd:
            self.review = json.load(fd)

        with open('tests/unit/test_data/sample_default_data.json') as fd:
            self.default_data = json.load(fd)

    def test_build_ci_map(self):
        ci_map = main.build_ci_map(self.default_data['drivers'])
        self.assertTrue('arista-test' in ci_map)
        self.assertEqual([{
            'vendor': 'Arista',
            'driver_name': 'Arista Neutron ML2 Driver'
        }], ci_map['arista-test'])

    def test_process_reviews_ci_vote_and_comment(self):
        # check that vote and matching comment are found

        ci_ids_map = main.build_ci_map(self.default_data['drivers'])
        records = list(main.process_reviews(
            [self.review], ci_ids_map, 'openstack/neutron'))
        records = [r for r in records if r.keys()[0][1] == 'arista']

        self.assertEqual(1, len(records), 'One record is expected')

        expected_record = {
            ('openstack/neutron', 'arista', 'arista neutron ml2 driver'): {
                'os_versions_map': {
                    'master': {
                        'comment': 'Verified+1\n\n'
                                   'Arista third party testing PASSED '
                                   '[ https://arista.box.com/s/x8z0 ]',
                        'timestamp': 1399478047,
                        'review_url': 'https://review.openstack.org/92468',
                    }
                }
            }
        }
        self.assertEqual(expected_record, records[0])

    def test_process_reviews_ci_only_comments(self):
        # check that comment is found and parsed correctly

        ci_ids_map = main.build_ci_map(self.default_data['drivers'])
        records = list(main.process_reviews(
            [self.review], ci_ids_map, 'openstack/neutron'))
        records = [r for r in records if r.keys()[0][1] == 'cisco']

        self.assertEqual(1, len(records), 'One record is expected')

        expected_record = {
            (
                'openstack/neutron', 'cisco',
                'neutron ml2 driver for cisco nexus devices'
            ): {
                'os_versions_map': {
                    'master': {
                        'comment': 'Build succeeded.\n\n'
                                   '- neutron_zuul http://128.107.233.28:8080/'
                                   'job/neutron_zuul/263 : SUCCESS in 18m 52s',
                        'timestamp': 1399481091,
                        'review_url': 'https://review.openstack.org/92468',
                    }
                }
            }
        }
        self.assertEqual(expected_record, records[0])

    def test_tranform_default_data(self):
        driver = {
            "project_id": "openstack/neutron",
            "releases": ["Grizzly", "Havana", "Icehouse"], }
        dd = {'drivers': [driver]}
        main.transform_default_data(dd)
        self.assertTrue('Grizzly' in driver['os_versions_map'],
                        'Grizzly should be copied from releases into '
                        'os_version_map')
