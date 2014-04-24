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

from driverlog.openstack.common import log as logging


LOG = logging.getLogger(__name__)


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

            template_name = template
            if template_name is None:
                template_name = (flask.request.endpoint.replace('.', '/') +
                                 '.html')
            ctx = f(*args, **kwargs)
            if ctx is None:
                ctx = {}

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
