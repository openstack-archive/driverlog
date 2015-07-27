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
from oslo_log import log as logging
from werkzeug import exceptions


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
