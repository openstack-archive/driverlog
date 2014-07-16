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
from driverlog.processor import utils

import memcache
import mock
import testtools


def _read_sample_review():
    with open('tests/unit/test_data/sample_review.json') as fd:
        return json.load(fd)


def _read_sample_default_data():
    with open('tests/unit/test_data/sample_default_data.json') as fd:
        return json.load(fd)


class TestMain(testtools.TestCase):
    def setUp(self):
        super(TestMain, self).setUp()

    def test_process_reviews_ci_vote_and_comment(self):
        # check that vote and matching comment are found

        result = main.find_ci_result([_read_sample_review()],
                                     {'id': 'arista-test'})

        self.assertIsNotNone(result, 'CI result should be found')

        expected_record = {
            'ci_result': True,
            'comment': 'Verified+1\n\nArista third party testing PASSED '
                       '[ https://arista.box.com/s/x8z0 ]',
            'timestamp': 1399478047,
            'review_url': 'https://review.openstack.org/92468',
        }
        self.assertEqual(expected_record, result)

    def test_process_reviews_ci_only_comments(self):
        # check that comment is found and parsed correctly

        result = main.find_ci_result([_read_sample_review()], {
            'id': 'cisco_neutron_ci',
            'success_pattern': 'neutron_zuul \\S+ : SUCCESS',
            'failure_pattern': 'neutron_zuul \\S+ : FAILURE',
        })

        self.assertIsNotNone(result, 'CI result should be found')

        expected_record = {
            'ci_result': True,
            'comment': 'Build succeeded.\n\n- neutron_zuul '
                       'http://128.107.233.28:8080/job/neutron_zuul/263 : '
                       'SUCCESS in 18m 52s',
            'timestamp': 1399481091,
            'review_url': 'https://review.openstack.org/92468',
        }
        self.assertEqual(expected_record, result)

    def test_transform_default_data(self):
        driver = {
            'project_id': 'openstack/neutron',
            'vendor': 'Cisco',
            'name': 'Cisco Nexus Plugin',
            'releases': ['Grizzly', 'Havana', 'Icehouse'], }
        dd = {'drivers': [driver]}

        main.transform_default_data(dd)

        self.assertIn(('openstack/neutron', 'Cisco', 'Cisco Nexus Plugin'),
                      dd['drivers'].keys())
        driver = dd['drivers'][
            ('openstack/neutron', 'Cisco', 'Cisco Nexus Plugin')]
        self.assertTrue('grizzly' in driver['releases'],
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
        def _patch_log(**kwargs):
            if (kwargs['project'] == 'openstack/neutron' and
                    kwargs['branch'] == 'master'):
                return [_read_sample_review()]
            return []

        def _get_rcs(review_uri):
            rcs_inst = mock.Mock()
            rcs_inst.log.side_effect = _patch_log
            return rcs_inst

        rcs_getter.side_effect = _get_rcs

    @mock.patch('oslo.config.cfg.CONF')
    @mock.patch('driverlog.processor.rcs.get_rcs')
    def test_calculate_update(self, rcs_getter, conf):
        memcached_inst = self._make_test_memcached()
        self._patch_rcs(rcs_getter)

        # run!
        main.process(memcached_inst, _read_sample_default_data(), False)

        # verify
        update = memcached_inst.get('driverlog:default_data')['drivers']

        driver_key = ('openstack/neutron', 'Cisco', 'Cisco Nexus Plugin')
        self.assertIn(driver_key, update.keys())
        self.assertIn('havana', update[driver_key]['releases'].keys())
        self.assertEqual('https://review.openstack.org/92468',
                         (update[driver_key]['releases']['juno']
                          ['review_url']))

    @mock.patch('oslo.config.cfg.CONF')
    @mock.patch('driverlog.processor.rcs.get_rcs')
    def test_calculate_update_existing_version_data(self, rcs_getter, conf):
        # checks that existing data will be overwritten with update
        # preserving data for other versions

        # put default data with some updates into memory storage
        dd = _read_sample_default_data()
        main.transform_default_data(dd)
        key = ('openstack/neutron', 'Cisco', 'Cisco Nexus Plugin')
        dd['drivers'][key]['releases'].update({
            'juno': {
                'comment': 'Build succeeded.',
                'timestamp': 1234567890,
                'review_url': 'https://review.openstack.org/11111'
            },
            'havana': {
                'comment': 'Build succeeded.',
                'timestamp': 1234567890,
                'review_url': 'https://review.openstack.org/22222'
            }})

        # put hash from default data to emulate that file is not changed
        default_data_from_file = _read_sample_default_data()

        memcached_inst = self._make_test_memcached({
            'driverlog:default_data': dd,
            'driverlog:default_data_hash': utils.calc_hash(
                default_data_from_file)})
        self._patch_rcs(rcs_getter)

        # run!
        main.process(memcached_inst, default_data_from_file, False)

        # verify
        update = memcached_inst.get('driverlog:default_data')['drivers']

        driver_key = ('openstack/neutron', 'Cisco', 'Cisco Nexus Plugin')
        self.assertIn(driver_key, update.keys())
        self.assertIn('juno', update[driver_key]['releases'])
        self.assertEqual('https://review.openstack.org/92468',
                         (update[driver_key]['releases']['juno']
                          ['review_url']))

        self.assertIn('havana', update[driver_key]['releases'])
        self.assertEqual('https://review.openstack.org/22222',
                         (update[driver_key]['releases']
                          ['havana']['review_url']))
