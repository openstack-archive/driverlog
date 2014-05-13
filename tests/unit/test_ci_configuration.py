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


class TestCIConfigValidity(testtools.TestCase):
    """
    This test verifies correctness of CI configuration in default_data.
    The test should be updated once driver name changes.
    sample_review.json needs update if a new driver is added.
    """
    def setUp(self):
        super(TestCIConfigValidity, self).setUp()

        with open('tests/unit/test_data/sample_review.json') as fd:
            self.review = json.load(fd)

        with open('etc/default_data.json') as fd:
            self.default_data = json.load(fd)

    def test_ci_config_matches_sample_review(self):
        def verify_single_driver(driver_name):
            ci_ids_map = main.build_ci_map(self.default_data['drivers'])
            records = list(main.process_reviews(
                [self.review], ci_ids_map, 'openstack/neutron'))
            records = [r for r in records
                       if r.keys()[0][2] == driver_name.lower()]
            self.assertEqual(1, len(records), '1 record is expected for '
                                              'driver %s' % driver_name)

        verify_single_driver('Cisco Nexus Plugin')
        verify_single_driver('Neutron ML2 Driver For Cisco Nexus Devices')
        verify_single_driver('Mellanox Neutron Plugin')
        verify_single_driver('Mellanox Neutron ML2 Driver')
        verify_single_driver('Big Switch Controller Plugin')
        verify_single_driver('Big Switch Neutron ML2 Driver')
        verify_single_driver('VMware NSX Network Virtualization Platform '
                             'Plugin')
        verify_single_driver('Arista Neutron ML2 Driver')
        verify_single_driver('Ryu OpenFlow Controller Plugin')
        verify_single_driver('PLUMgrid Plugin')
        verify_single_driver('NEC OpenFlow Plugin')
        verify_single_driver('Cloudbase Hyper-V Plugin')
