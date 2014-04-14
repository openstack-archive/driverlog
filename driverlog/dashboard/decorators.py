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

import functools
import json

import flask
from werkzeug import exceptions

from driverlog.dashboard import parameters
from driverlog.dashboard import vault
from driverlog.openstack.common import log as logging
from driverlog.processor import utils


LOG = logging.getLogger(__name__)


def _get_time_filter(kwargs):
    start_date = parameters.get_single_parameter(kwargs, 'start_date')
    if start_date:
        start_date = utils.date_to_timestamp_ext(start_date)
    else:
        start_date = 0
    end_date = parameters.get_single_parameter(kwargs, 'end_date')
    if end_date:
        end_date = utils.date_to_timestamp_ext(end_date)
    else:
        end_date = utils.date_to_timestamp_ext('now')

    def time_filter(records):
        for record in records:
            if start_date <= record['date'] <= end_date:
                yield record

    return time_filter


def record_filter(ignore=None, use_default=True):
    if not ignore:
        ignore = []

    def decorator(f):
        @functools.wraps(f)
        def record_filter_decorated_function(*args, **kwargs):

            memory_storage_inst = vault.get_memory_storage()
            record_ids = set(memory_storage_inst.get_record_ids())  # a copy

            # if 'module' not in ignore:
            #     param = parameters.get_parameter(kwargs, 'module', 'modules',
            #                                      use_default)
            #     if param:
            #         record_ids &= (
            #             memory_storage_inst.get_record_ids_by_modules(
            #                 vault.resolve_modules(param)))

            time_filter = _get_time_filter(kwargs)

            kwargs['records'] = time_filter(
                memory_storage_inst.get_records(record_ids))
            return f(*args, **kwargs)

        return record_filter_decorated_function

    return decorator


def exception_handler():
    def decorator(f):
        @functools.wraps(f)
        def exception_handler_decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                if isinstance(e, exceptions.HTTPException):
                    raise  # ignore Flask exceptions
                LOG.exception(e)
                flask.abort(500)

        return exception_handler_decorated_function

    return decorator


def templated(template=None, return_code=200):
    def decorator(f):
        @functools.wraps(f)
        def templated_decorated_function(*args, **kwargs):

            # vault_inst = vault.get_vault()
            template_name = template
            if template_name is None:
                template_name = (flask.request.endpoint.replace('.', '/') +
                                 '.html')
            ctx = f(*args, **kwargs)
            if ctx is None:
                ctx = {}

            # put parameters into template
            # vault_inst = vault.get_vault()
            # ctx['projects'] = vault_inst['default_data']['projects']
            #
            # project = parameters.get_single_parameter(kwargs, 'project')
            # if project in vault_inst['projects_map']:
            #     ctx['project'] = vault_inst['projects_map'][project]
            #
            # driver = parameters.get_single_parameter(kwargs, 'driver')
            # if driver:
            #     ctx['driver'] = driver
            #     ctx['project'] = vault_inst[
            #         'driver_to_project_map'][ctx['driver']]
            #
            # date = parameters.get_single_parameter(kwargs, 'date')
            # if date:
            #     ctx['date'] = date
            # else:
            #     ctx['date'] = int(time.time())

            return flask.render_template(template_name, **ctx), return_code

        return templated_decorated_function

    return decorator


def jsonify(root='data'):
    def decorator(func):
        @functools.wraps(func)
        def jsonify_decorated_function(*args, **kwargs):
            callback = flask.app.request.args.get('callback', False)
            data = json.dumps({root: func(*args, **kwargs)})

            if callback:
                data = str(callback) + '(' + data + ')'
                mimetype = 'application/javascript'
            else:
                mimetype = 'application/json'

            return flask.current_app.response_class(data, mimetype=mimetype)

        return jsonify_decorated_function

    return decorator
