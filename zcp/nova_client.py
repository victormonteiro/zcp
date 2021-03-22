#    Copyright  2017 EasyStack, Inc
#    Authors: Claudio Marques,
#             David Palma,
#             Luis Cordeiro,
#             Branty <jun.wang@easystack.cn>
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

from novaclient import client as nova_client
from novaclient import exceptions
from keystoneauth1 import loading
from keystoneauth1 import session


LOG = logging.getLogger(__name__)


def logged(func):

    @functools.wraps(func)
    def with_logging(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exceptions.Unauthorized, e:
            msg = "Error... \nToken refused! " \
                  "The request you have made requires authentication."
            LOG.error(msg)
            raise
        except exceptions.NotFound, e:
            LOG.error("Not Found Nova Resource")
            raise
        except Exception, ex:
            msg = getattr(ex, 'message', None) or \
                  getattr(ex, 'msg', '')
            LOG.error(msg)
            raise
    return with_logging


class Client(object):
    def __init__(self, conf):

        v3_kwargs = {
                "username": conf.read_option('keystone_authtoken',
                                             'username'),
                "password": conf.read_option('keystone_authtoken',
                                             'password'),
                "project_name": conf.read_option(
                                             'keystone_authtoken',
                                             'project_name'),
                "user_domain_name": conf.read_option(
                                             'keystone_authtoken',
                                             'user_domain_name'),
                "project_domain_name": conf.read_option(
                                             'keystone_authtoken',
                                             'project_domain_name'),
                "auth_url": conf.read_option('keystone_authtoken',
                                             'auth_url'),
                "region_name": conf.read_option(
                                             'keystone_authtoken',
                                             'region_name'),
        }

        auth = v3.Password(auth_url=v3_kwargs['auth_url'],
                            username=v3_kwargs['username'],
                            password=v3_kwargs['password'],
                            project_name=v3_kwargs['project_name'],
                            project_domain_id=v3_kwargs['project_domain_name'],
                            user_domain_name=v3_kwargs['user_domain_name'])

        sess = session.Session(auth=auth)
        self.nv_client = clienova_clientnt.Client(2.1, session=sess)

    @logged
    def instance_get_all(self, since=None):
        """Returns list of all instances.
        If since is supplied, it will return the instances changes since that
        datetime. since should be in ISO Format '%Y-%m-%dT%H:%M:%SZ'
        """
        search_opts = {'all_tenants': True}
        if since:
            search_opts['changes-since'] = since
        return self.nv_client.servers.list(
            detailed=True,
            search_opts=search_opts)
