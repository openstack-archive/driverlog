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

import hashlib
import json

import collections
import re

import memcache
from oslo.config import cfg
from six.moves.urllib import parse
import time

from driverlog.openstack.common import log as logging
from driverlog.processor import config
from driverlog.processor import rcs
from driverlog.processor import utils


LOG = logging.getLogger(__name__)


def find_comment(review, ci):
    patch_number = review['currentPatchSet']['number']

    for comment in reversed(review.get('comments') or []):
        prefix = 'Patch Set %s:' % patch_number
        if ((comment['reviewer'].get('username') == ci) and
                (comment['message'].find(prefix) == 0)):
            return comment['message'][len(prefix):].strip()

    return None


def find_vote(review, ci_id):
    for approval in (review['currentPatchSet'].get('approvals') or []):
        if approval['type'] not in ['Verified', 'VRIF']:
            continue

        if approval['by'].get('username') == ci_id:
            return approval['value'] in ['1', '2']

    return None


def process_reviews(review_iterator, ci_ids_map, project_id):
    branch_ci_set = set()

    for review in review_iterator:
        review_url = review['url']
        branch = review['branch']

        for comment in reversed(review.get('comments') or []):
            ci_id = comment['reviewer'].get('username')
            if ci_id not in ci_ids_map:
                continue

            branch_ci = (branch, ci_id)
            if branch_ci in branch_ci_set:
                continue  # already seen, ignore

            branch_ci_set.add(branch_ci)

            message = comment['message']
            prefix = 'Patch Set %s:' % review['currentPatchSet']['number']
            if comment['message'].find(prefix) != 0:
                break  # all comments from the latest patch set passed

            message = message[len(prefix):].strip()

            for one_ci in ci_ids_map[ci_id]:
                result = None

                # try to get result by parsing comment message
                success_pattern = one_ci.get('success_pattern')
                failure_pattern = one_ci.get('failure_pattern')
                if success_pattern and re.search(success_pattern, message):
                    result = True
                elif failure_pattern and re.search(failure_pattern, message):
                    result = False

                # try to get result from vote
                if not result:
                    result = find_vote(review, ci_id)

                if result:
                    yield {
                        (project_id,
                         one_ci['vendor'].lower(),
                         one_ci['driver_name'].lower()): {
                             'os_versions_map': {
                                 branch: {
                                     'comment': message,
                                     'timestamp': comment['timestamp'],
                                     'review_url': review_url
                                 }
                             }
                         }
                    }


def update_generator(memcached, default_data, ci_ids_map, force_update=False):
    for project in default_data['projects']:
        project_id = project['id'].lower()
        rcs_inst = rcs.get_rcs(project_id, cfg.CONF.review_uri)
        rcs_inst.setup(key_filename=cfg.CONF.ssh_key_filename,
                       username=cfg.CONF.ssh_username)

        LOG.debug('Processing reviews for project: %s', project_id)

        rcs_key = 'driverlog:rcs:' + parse.quote_plus(project_id)
        last_id = None
        if not force_update:
            last_id = memcached.get(rcs_key)

        review_iterator = rcs_inst.log(last_id)
        for item in process_reviews(review_iterator, ci_ids_map, project_id):
            yield item

        last_id = rcs_inst.get_last_id()
        LOG.debug('RCS last id is: %s', last_id)
        memcached.set(rcs_key, last_id)


def _get_hash(data):
    h = hashlib.new('sha1')
    h.update(json.dumps(data))
    return h.hexdigest()


def build_ci_map(drivers):
    ci_map = collections.defaultdict(list)
    for driver in drivers:
        if 'ci' in driver:
            value = {
                'vendor': driver['vendor'],
                'driver_name': driver['name'],
            }
            ci = driver['ci']
            if 'success_pattern' in ci:
                value['success_pattern'] = ci['success_pattern']
            if 'failure_pattern' in ci:
                value['failure_pattern'] = ci['failure_pattern']

            ci_map[ci['id']].append(value)
    return ci_map


def transform_default_data(default_data):
    for driver in default_data['drivers']:
        driver['os_versions_map'] = {}
        if 'releases' in driver:
            for release in driver['releases']:
                driver['os_versions_map'][release] = {
                    'success': True,
                    'comment': 'self-tested verification'
                }


def main():
    # init conf and logging
    conf = cfg.CONF
    conf.register_cli_opts(config.OPTS)
    conf.register_opts(config.OPTS)
    conf()

    logging.setup('driverlog')
    LOG.info('Logging enabled')

    MEMCACHED_URI_PREFIX = r'^memcached:\/\/'
    stripped = re.sub(MEMCACHED_URI_PREFIX, '', cfg.CONF.runtime_storage_uri)
    if not stripped:
        exit(1)

    memcached_uri = stripped.split(',')
    memcache_inst = memcache.Client(memcached_uri)

    default_data = utils.read_json_from_uri(cfg.CONF.default_data_uri)
    if not default_data:
        LOG.critical('Unable to load default data')
        return not 0

    ci_ids_map = build_ci_map(default_data['drivers'])

    update = {}
    if not cfg.CONF.force_update:
        update = memcache_inst.get('driverlog:update') or {}

    has_update = False

    for record in update_generator(memcache_inst, default_data, ci_ids_map,
                                   force_update=cfg.CONF.force_update):
        LOG.info('Got new record from Gerrit: %s', record)
        has_update = True

        key = record.keys()[0]
        if key not in update:
            update.update(record)
        else:
            os_version = record[key]['os_versions_map'].keys()[0]
            info = record[key]['os_versions_map'].values()[0]
            if os_version in update[key]['os_versions_map']:
                update[key]['os_versions_map'][os_version].update(info)
            else:
                update[key]['os_versions_map'][os_version] = info

    # write default data into memcache
    transform_default_data(default_data)
    memcache_inst.set('driverlog:default_data', default_data)

    old_dd_hash = memcache_inst.get('driverlog:default_data_hash')
    new_dd_hash = _get_hash(default_data)
    memcache_inst.set('driverlog:default_data_hash', new_dd_hash)

    # write update into memcache
    memcache_inst.set('driverlog:update', update)

    if has_update or old_dd_hash != new_dd_hash:
        memcache_inst.set('driverlog:update_hash', time.time())


if __name__ == '__main__':
    main()
