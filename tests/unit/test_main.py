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

from driverlog.processor import main

import testtools


class TestMain(testtools.TestCase):
    def setUp(self):
        super(TestMain, self).setUp()

    def test_process_reviews_ci_vote(self):
        review = {
            "project": "openstack/neutron",
            "branch": "master",
            "url": "https://review.openstack.org/92468",
            "currentPatchSet": {
                "number": "2",
                "approvals": [
                    {
                        "type": "Verified",
                        "description": "Verified",
                        "value": "1",
                        "grantedOn": 1399478047,
                        "by": {
                            "name": "Arista Testing",
                            "username": "arista-test"
                        }
                    }]}
        }

        ci_ids_map = {'arista-test': [('Arista', 'Arista Neutron ML2 Driver')]}
        records = list(main.process_reviews(
            [review], ci_ids_map, 'openstack/neutron'))

        self.assertEqual(1, len(records), 'One record is expected')

        expected_record = {
            ('openstack/neutron', 'arista', 'arista neutron ml2 driver'): {
                'os_versions_map': {
                    'master': {
                        'comment': None,
                        'timestamp': 1399478047,
                        'review_url': 'https://review.openstack.org/92468',
                    }
                }
            }
        }
        self.assertEqual(expected_record, records[0])

    def test_process_reviews_ci_vote_and_comment(self):
        review = {
            "project": "openstack/neutron",
            "branch": "master",
            "url": "https://review.openstack.org/92468",
            "comments": [
                {
                    "timestamp": 1399411839,
                    "reviewer": {
                        "name": "Arista Testing",
                        "email": "arista-openstack-test@aristanetworks.com",
                        "username": "arista-test"
                    },
                    "message": "Patch Set 2: Verified+1\n\n"
                               "Arista third party testing PASSED"
                },
            ],
            "currentPatchSet": {
                "number": "2",
                "approvals": [
                    {
                        "type": "Verified",
                        "description": "Verified",
                        "value": "1",
                        "grantedOn": 1399478047,
                        "by": {
                            "name": "Arista Testing",
                            "username": "arista-test"
                        }
                    }]}
        }

        ci_ids_map = {'arista-test': [('Arista', 'Arista Neutron ML2 Driver')]}
        records = list(main.process_reviews(
            [review], ci_ids_map, 'openstack/neutron'))

        self.assertEqual(1, len(records), 'One record is expected')

        expected_record = {
            ('openstack/neutron', 'arista', 'arista neutron ml2 driver'): {
                'os_versions_map': {
                    'master': {
                        'comment': 'Verified+1\n\n'
                                   'Arista third party testing PASSED',
                        'timestamp': 1399478047,
                        'review_url': 'https://review.openstack.org/92468',
                    }
                }
            }
        }
        self.assertEqual(expected_record, records[0])
