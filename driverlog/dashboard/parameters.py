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

import flask
from six.moves.urllib import parse

from driverlog.openstack.common import log as logging


LOG = logging.getLogger(__name__)


def get_parameter(kwargs, singular_name, plural_name=None):
    if singular_name in kwargs:
        p = kwargs[singular_name]
    else:
        p = flask.request.args.get(singular_name)
        if (not p) and plural_name:
            p = flask.request.args.get(plural_name)
    if p:
        return parse.unquote_plus(p).split(',')
    else:
        return []


def get_single_parameter(kwargs, singular_name, use_default=True):
    param = get_parameter(kwargs, singular_name, use_default)
    if param:
        return param[0]
    else:
        return ''
