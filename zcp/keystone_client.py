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

"""
Class for requesting authentication tokens to Keystone

This class provides means to requests for authentication

tokens to be used with OpenStack's Ceilometer, Nova and RabbitMQ

and query requirements for keystone projects and domains
"""

import functools
import logging
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client

LOG = logging.getLogger(__name__)


def logged(func):

    @functools.wraps(func)
    def with_logging(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            LOG.error(e)
            raise e
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

        self.domain_keystone = client.Client(session=sess)

    @logged
    def get_domains(self):
        return self.domain_keystone.domains.list()

    @logged
    def show_domain(self, domain_id_or_name):
        return self.domain_keystone.domains.get(domain_id_or_name)

    @logged
    def get_projects(self, domain_id=None):
        if domain_id:
            return self.domain_keystone.projects.list(domain=domain_id)
        else:
            return self.domain_keystone.projects.list()

    @logged
    def get_project(self, project_id):
        return self.domain_keystone.projects.get(project_id)
