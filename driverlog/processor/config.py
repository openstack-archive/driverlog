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

import copy

from oslo_config import cfg


OPTS = [
    cfg.StrOpt('default-data-uri',
               help='URI for default data'),
    cfg.StrOpt('listen-host', default='127.0.0.1',
               help='The address dashboard listens on'),
    cfg.IntOpt('listen-port', default=8080,
               help='The port dashboard listens on'),
    cfg.StrOpt('runtime-storage-uri', default='memcached://127.0.0.1:11211',
               help='Storage URI'),
    cfg.StrOpt('review-uri', default='gerrit://review.openstack.org',
               help='URI of review system'),
    cfg.StrOpt('ssh-key-filename', default='/home/user/.ssh/id_rsa',
               help='SSH key for gerrit review system access'),
    cfg.StrOpt('ssh-username', default='user',
               help='SSH username for gerrit review system access'),
    cfg.BoolOpt('force-update', default=False,
                help='Forcibly read default data and update records'),
]


def list_opts():
    yield (None, copy.deepcopy(OPTS))
