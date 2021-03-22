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
Class for polling Gnocchi

This class provides means to requests for authentication
tokens to be used with OpenStack's Gnocchi, Nova and RabbitMQ
"""
import logging

from zcp.gnocchi_client import Client as GnocchiAPI
from zcp import utils
from zcp.task.polling import INSTANCE_METRICS, NETWORK_METRICS
from zcp.task.polling.base_handler import Handler


LOG = logging.getLogger(__name__)

METRIC_CACEHES = {}


def get_handler(*args):
    return GnocchiHandler(*args)


class GnocchiHandler(Handler):

    def __init__(self, conf,
                 ks_client, nv_client, zabbix_hdl):
        """Gnocchi polling handler

        :param conf: zcp configs
        :parms ks_client: Openstack identity service, keystone client
        :parms nv_client: Openstack compute service,nova client
        :parms zabbix_hdl:zabbix handler
        """
        super(GnocchiHandler, self).__init__(conf, zabbix_hdl)
        self.polling_interval = int(conf.read_option('zcp_configs',
                                                     'polling_interval'))
        self.ks_client = ks_client
        self.nv_client = nv_client
        self.zabbix_hdl = zabbix_hdl
        self.gnocchi_client = GnocchiAPI()

    def polling_metrics(self, hosts, hosts_map):
        """
        For ES metric collecor,
        We don't storage sample in a same collection meter(
        OpenStack community do it like this).

        Accroding to the sample period,slice the meter collection
        and collector metric
        :param hosts: a list ,record zabbix host information.
        :param hosts_cache:a dict ,record zabbix host information.
         hosts_cache, the date structure is the following:
         {"instance_id":["host_id","host_name","proxy_id"]
         }
        hosts: ['instance_id1','instance)id2',...]
        """
        def _all_instance_details():
            response = self.nv_client.instance_get_all()
            servers = [server.to_dict() for server in response]
            if not servers:
                LOG.warning("Servers list is empry,"
                            "skip to update zabbix values")
            return servers

        All_INSTANCES = _all_instance_details() or []
        for instance in All_INSTANCES:
            if instance['id'] in hosts and utils.is_active(instance):
                LOG.info("Start Checking host : %s"
                          % hosts_map[instance['id']][1])
                # Get links for instance compute metrics
                resources = self.gnocchi_client.list_resources(resource_type='instance',
                                                            resource_id=instance['id'])
                
                # Add a new instance and its metrics
                if instance['id'] not in METRIC_CACEHES.keys():
                    rs_items = {}
                    for rs_metric,data in resources["metrics"]:
                        print(rs_metric)
                        print(data)

                    # for rs in resources["metrics"]:
                    #     if rs.resource_id.startswith('instance'):
                    #         rs_items[rs.resource_id] = NETWORK_METRICS
                    #     # NOTE:remove disk metrics
                    #     elif utils.endswith_words(rs.resource_id):
                    #         pass
                    #     else:
                    #         rs_items[rs.resource_id] = INSTANCE_METRICS
                    METRIC_CACEHES[instance['id']] = rs_items
                # Update metric_caches where instance_in exists.For the case:
                # instance add/remove a nic
                # instance add/remove a volume
                else:
                    rs_items = METRIC_CACEHES[instance['id']]
                    rs_item_keys = rs_items.keys()
                    for rs in resources:
                        if rs.resource_id not in rs_item_keys and \
                           rs.resource_id.startswith('instance'):
                            rs_items[rs.resource_id] = NETWORK_METRICS
                            METRIC_CACEHES[instance['id']] = rs_items
                        # NOTE:remove disk metrics
                        elif rs.resource_id not in rs_item_keys and \
                                utils.endswith_words(rs.resource_id):
                            pass
                        else:
                            continue
                LOG.info("Starting to polling %s(%s) metric into zabbix"
                          % (instance.get('name'), instance.get('id')))
                pxy = self.zabbix_hdl.get_by_proxyid(
                                hosts_map[instance['id']][2])
                if pxy:
                    proxy_name = pxy['host']
                else:
                    LOG.warning("Can't find the proxy:%s,Skip to polling "
                                "instance_id  %s metrics."
                                % (hosts_map[instance['id']][2],
                                   instance['id']))
                    continue
                # Polling Gnocchi the latest sample into zabbix
                # CLI:Gnocchi statistics -m {...} -q resource_id={...} -p ..
                self._polling_metrics(instance['id'],
                                      proxy_name)
                LOG.debug("Finshed to polling %s(%s) metric into zabbix"
                          % (instance.get('name'), instance.get('id')))
            else:
                LOG.debug("Can't find the instance : %s(%s), "
                          "or the status of %s is not active"
                          % (instance.get('name'),
                             instance.get('id'),
                             instance.get('name'))
                          )

    def _polling_metrics(self, instance_id, proxy_name):
        """
        :param instance_id: nova instance uuid
        :param proxy_name: zabbix proxy_name
        """
        def _polling(ids, METRICS):
            for metric in METRICS:
                counter_volume = 0.0
                for rsc_id in ids:
                    query = [{'op': 'eq',
                              'value': rsc_id,
                              'field': 'resource_id'}]
                    response = self.gnocchi_client.statistics(
                                metric,
                                q=query,
                                limit=1)
                    if len(response) > 0:
                        counter_volume += response[0].avg
                    else:
                        LOG.info("The metric %s of resource_id %s statistics "
                                 "not found." % (metric, rsc_id))
                    LOG.info("Polling Gnocchi metrics into Zabbix, proxy: %s, "
                             "resource_id: %s, metric: %s, counter_name: %s"
                             % (rsc_id, metric, counter_volume, proxy_name))
                    self.zabbix_hdl.send_data_zabbix(counter_volume,
                                                     instance_id,
                                                     metric,
                                                     proxy_name)
        # Get instance all taps
        network_nics_id = []
        # Get install all volumes
        for rsc_id in METRIC_CACEHES[instance_id].keys():
            if rsc_id.startswith('instance'):
                network_nics_id.append(rsc_id)

        # network metrics
        _polling(network_nics_id, NETWORK_METRICS)

        # instance metrics
        _polling([instance_id], INSTANCE_METRICS)
