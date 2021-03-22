#    Copyright  2017 EasyStack, Inc
#    Authors: Branty <jun.wang@easystack.cn>
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import logging
import functools

from gnocchiclient import auth
from gnocchiclient.v1 import client as gn_client
from oslo_config import cfg
from keystoneauth1 import loading
from keystoneauth1 import session as keystone_session
from keystoneauth1.identity import v3

from zcp.common import conf

CONF = conf.Conf()
LOG = logging.getLogger(__name__)


def logged(func):

    @functools.wraps(func)
    def with_logging(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, ex:
            msg = getattr(ex, 'message', None) or \
                  getattr(ex, 'msg', '')
            LOG.error(msg)
            raise
    return with_logging


class Client(object):
    def __init__(self):
        v3_kwargs = {
                "username": CONF.read_option('keystone_authtoken',
                                             'username'),
                "password": CONF.read_option('keystone_authtoken',
                                             'password'),
                "project_name": CONF.read_option(
                                             'keystone_authtoken',
                                             'project_name'),
                "user_domain_name": CONF.read_option(
                                             'keystone_authtoken',
                                             'user_domain_name'),
                "project_domain_name": CONF.read_option(
                                             'keystone_authtoken',
                                             'project_domain_name'),
                "auth_url": CONF.read_option('keystone_authtoken',
                                             'auth_url'),
                "region_name": CONF.read_option(
                                             'keystone_authtoken',
                                             'region_name'),
        }
        auth = v3.Password(auth_url=v3_kwargs['auth_url'],
                            username=v3_kwargs['username'],
                            password=v3_kwargs['password'],
                            project_name=v3_kwargs['project_name'],
                            project_domain_id=v3_kwargs['project_domain_name'],
                            user_domain_name=v3_kwargs['user_domain_name'])

        sess = keystone_session.Session(auth=auth)

        self.gn_client = gn_client.Client(session=sess)

    @logged
    def list_resources(self, q=None, limit=None):
        if not isinstance(q, list):
            # TO DO
            # add something warning
            raise
        print(q)
        return self.gn_client.resource.search(query=q,
                                              limit=limit)

    @logged
    def statistics(self, meter_name, q=None, limit=None):
        if not isinstance(q, list):
            LOG.error("Invalid query param q: %s,q must be a list" % q)
            raise
        return self.gn_client.statistics.list(meter_name,
                                               q=q,
                                               limit=limit
                                               )
