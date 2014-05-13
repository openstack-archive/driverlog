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
import memcache
import mock

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

        self.assertEqual(2, len(records), '2 records are expected '
                                          '(since there are 2 cisco entries)')

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

    def _make_test_memcached(self, storage=None):
        storage = storage or {}

        def _memcache_get(key):
            return storage.get(key)

        def _memcache_set(key, value):
            storage[key] = value

        memcached_inst = mock.Mock(memcache.Client)
        memcached_inst.get.side_effect = _memcache_get
        memcached_inst.set.side_effect = _memcache_set
        return memcached_inst

    def _patch_rcs(self, rcs_getter):
        def _get_rcs(project_id, review_uri):
            rcs_inst = mock.Mock()
            if project_id == 'openstack/neutron':
                rcs_inst.log.return_value = [self.review]
            else:
                rcs_inst.log.return_value = []
            return rcs_inst

        rcs_getter.side_effect = _get_rcs

    @mock.patch('oslo.config.cfg.CONF')
    @mock.patch('driverlog.processor.rcs.get_rcs')
    def test_calculate_update(self, rcs_getter, conf):
        memcached_inst = self._make_test_memcached()
        self._patch_rcs(rcs_getter)

        # run!
        main.calculate_update(memcached_inst, self.default_data, False)

        # verify
        update = memcached_inst.get('driverlog:update')

        driver_key = ('openstack/neutron', 'cisco', 'cisco nexus plugin')
        self.assertIn(driver_key, update)
        self.assertIn('master', update[driver_key]['os_versions_map'])
        self.assertEqual('https://review.openstack.org/92468',
                         (update[driver_key]['os_versions_map']['master']
                          ['review_url']))

    @mock.patch('oslo.config.cfg.CONF')
    @mock.patch('driverlog.processor.rcs.get_rcs')
    def test_calculate_update_existing_version_data(self, rcs_getter, conf):
        # checks that existing data will be overwritten with update
        # preserving data for other versions

        memcached_inst = self._make_test_memcached({
            'driverlog:update': {
                ('openstack/neutron', 'cisco', 'cisco nexus plugin'): {
                    'os_versions_map': {
                        'master': {
                            'comment': 'Build succeeded.',
                            'timestamp': 1234567890,
                            'review_url': 'https://review.openstack.org/11111'
                        },
                        'stable/havana': {
                            'comment': 'Build succeeded.',
                            'timestamp': 1234567890,
                            'review_url': 'https://review.openstack.org/22222'
                        }
                    }}}})
        self._patch_rcs(rcs_getter)

        # run!
        main.calculate_update(memcached_inst, self.default_data, False)

        # verify
        update = memcached_inst.get('driverlog:update')

        driver_key = ('openstack/neutron', 'cisco', 'cisco nexus plugin')
        self.assertIn(driver_key, update)
        self.assertIn('master', update[driver_key]['os_versions_map'])
        self.assertEqual('https://review.openstack.org/92468',
                         (update[driver_key]['os_versions_map']['master']
                          ['review_url']))

        self.assertIn('stable/havana', update[driver_key]['os_versions_map'])
        self.assertEqual('https://review.openstack.org/22222',
                         (update[driver_key]['os_versions_map']
                          ['stable/havana']['review_url']))

    @mock.patch('oslo.config.cfg.CONF')
    @mock.patch('driverlog.processor.rcs.get_rcs')
    def test_calculate_update_insert_version_data(self, rcs_getter, conf):
        # checks that existing data will be overwritten with update

        memcached_inst = self._make_test_memcached({
            'driverlog:update': {
                ('openstack/neutron', 'cisco', 'cisco nexus plugin'): {
                    'os_versions_map': {
                        'stable/havana': {
                            'comment': 'Build succeeded.',
                            'timestamp': 1234567890,
                            'review_url': 'https://review.openstack.org/22222'
                        }
                    }}}})
        self._patch_rcs(rcs_getter)

        # run!
        main.calculate_update(memcached_inst, self.default_data, False)

        # verify
        update = memcached_inst.get('driverlog:update')

        driver_key = ('openstack/neutron', 'cisco', 'cisco nexus plugin')
        self.assertIn(driver_key, update)
        self.assertIn('master', update[driver_key]['os_versions_map'])
        self.assertEqual('https://review.openstack.org/92468',
                         (update[driver_key]['os_versions_map']['master']
                          ['review_url']))

        self.assertIn('stable/havana', update[driver_key]['os_versions_map'])
        self.assertEqual('https://review.openstack.org/22222',
                         (update[driver_key]['os_versions_map']
                          ['stable/havana']['review_url']))
