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

import re
import time

import memcache
from oslo_config import cfg
from oslo_log import log as logging

from driverlog.processor import config
from driverlog.processor import rcs
from driverlog.processor import utils


LOG = logging.getLogger(__name__)


def _find_vote(review, ci_id):
    """Finds vote corresponding to ci_id."""
    for approval in (review['currentPatchSet'].get('approvals') or []):
        if approval['type'] not in ['Verified', 'VRIF']:
            continue

        if approval['by'].get('username') == ci_id:
            return approval['value'] in ['1', '2']

    return None


def find_ci_result(review_iterator, ci):
    """For a given stream of reviews finds result left by specified ci."""

    for review in review_iterator:
        review_url = review['url']

        for comment in reversed(review.get('comments') or []):
            if comment['reviewer'].get('username') != ci['id']:
                continue

            message = comment['message']
            prefix = 'Patch Set %s:' % review['currentPatchSet']['number']
            if comment['message'].find(prefix) != 0:
                break  # all comments from the latest patch set passed
            message = message[len(prefix):].strip()

            result = None

            # try to get result by parsing comment message
            success_pattern = ci.get('success_pattern')
            failure_pattern = ci.get('failure_pattern')

            if success_pattern and re.search(success_pattern, message):
                result = True
            elif failure_pattern and re.search(failure_pattern, message):
                result = False

            # try to get result from vote
            if result is None:
                result = _find_vote(review, ci['id'])

            if result is not None:
                return {
                    'ci_result': result,
                    'comment': message,
                    'timestamp': comment['timestamp'],
                    'review_url': review_url,
                }


def _get_release_by_branch(releases, branch):
    """Translates branch name into release_id."""
    release = branch.lower()
    if release.find('/') > 0:
        return release.split('/')[1]
    elif release == 'master':
        return releases[-1]['id'].lower()


def update_drivers(drivers, releases):
    """Iterates all drivers and searches for results produced by their CIs.

    Returns True if info was updated
    """
    branches = [('stable/' + r['id'].lower()) for r in releases] + ['master']

    rcs_inst = rcs.get_rcs(cfg.CONF.review_uri)
    rcs_inst.setup(key_filename=cfg.CONF.ssh_key_filename,
                   username=cfg.CONF.ssh_username)

    has_updates = False

    for driver in drivers.values():
        if 'ci' not in driver:
            continue

        project_id = driver['project_id']
        ci_id = driver['ci']['id']

        for branch in branches:
            LOG.debug('Searching reviews for project: %(project_id)s, branch: '
                      '%(branch)s, ci_id: %(ci_id)s',
                      {'project_id': project_id, 'branch': branch,
                       'ci_id': ci_id})

            review_iterator = rcs_inst.log(project=project_id, branch=branch,
                                           reviewer=ci_id)
            ci_result = find_ci_result(review_iterator, driver['ci'])
            if ci_result:
                LOG.debug('Found CI result: %s', ci_result)
                has_updates = True

                key = (project_id, driver['vendor'], driver['name'])
                os_version = _get_release_by_branch(releases, branch)
                ci_result['ci_tested'] = True
                drivers[key]['releases'][os_version] = ci_result

    rcs_inst.close()

    return has_updates


def transform_default_data(default_data):
    transformed_drivers = {}

    for driver in default_data['drivers']:
        transformed_releases = {}
        if 'releases' in driver:
            for release in driver['releases']:
                transformed_releases[release.lower()] = {
                    'ci_tested': False,
                }
        driver['releases'] = transformed_releases

        key = (driver['project_id'], driver['vendor'], driver['name'])
        transformed_drivers[key] = driver

    default_data['drivers'] = transformed_drivers


def process(memcached_inst, default_data, force_update):

    old_dd_hash = memcached_inst.get('driverlog:default_data_hash')
    new_dd_hash = utils.calc_hash(default_data)

    need_update = False

    if (new_dd_hash != old_dd_hash) or force_update:
        transform_default_data(default_data)
        need_update = True
    else:
        default_data = memcached_inst.get('driverlog:default_data')

    need_update |= update_drivers(default_data['drivers'],
                                  default_data['releases'])

    if need_update:
        # write default data into memcache
        memcached_inst.set('driverlog:default_data', default_data)
        memcached_inst.set('driverlog:default_data_hash', new_dd_hash)
        memcached_inst.set('driverlog:update_time', time.time())


def main():
    # init conf and logging
    conf = cfg.CONF
    conf.register_cli_opts(config.OPTS)
    conf.register_opts(config.OPTS)
    logging.register_options(conf)
    logging.set_defaults()

    conf(project='driverlog')

    logging.setup(conf, 'driverlog')
    LOG.info('Logging enabled')
    conf.log_opt_values(LOG, logging.DEBUG)

    MEMCACHED_URI_PREFIX = r'^memcached:\/\/'
    stripped = re.sub(MEMCACHED_URI_PREFIX, '', cfg.CONF.runtime_storage_uri)
    if not stripped:
        exit(1)

    memcached_uri = stripped.split(',')
    memcached_inst = memcache.Client(memcached_uri)

    default_data = utils.read_json_from_uri(cfg.CONF.default_data_uri)
    if not default_data:
        LOG.critical('Unable to load default data')
        return not 0

    process(memcached_inst, default_data, cfg.CONF.force_update)


if __name__ == '__main__':
    main()
