#!/usr/bin/env python
import utils
import sys
#from himlarcli.nova import Nova
from himlarcli.keystone import Keystone
#import himlarcli.foremanclient as foreman
from himlarcli.foremanclient import Client
from himlarcli import utils as himutils

desc = 'Setup compute resources and profiles'
options = utils.get_options(desc, hosts=False, dry_run=True)
keystone = Keystone(options.config, debug=options.debug)
logger = keystone.get_logger()

client = Client(options.config, options.debug, log=logger)
foreman = client.get_client()

node_config = himutils.load_config('config/install_nodes.yaml')

if keystone.region not in node_config:
    nodes = node_config['default']
else:
    nodes = node_config[keystone.region]

# Available compute resources
resources = foreman.index_computeresources()
found_resources = dict({})
for r in resources['results']:
    found_resources[r['name']] = r['id']


# Crate nodes
for name, node_data in nodes.iteritems():
    if client.get_host(name):
        logger.debug('=> node %s found' % name)
        continue
    host = dict()
    host['name'] = '%s-%s' % (keystone.region, name)
    if 'mac' in node_data:
        host['mac'] = node_data['mac']
    if 'compute_resource' in node_data:
        compute_resource = '%s-%s' % (keystone.region, node_data['compute_resource'])
        if compute_resource in found_resources:
            host['compute_resource_id'] = found_resources[compute_resource]
        else:
            logger.debug('=> compute resource %s not found' % compute_resource)
    else:
        logger.critical('=> missing compute resource for %s' % name)
    if 'profile' in node_data:
        host['compute_profile_id'] = node_data['profile']
    if 'hostgroup' in node_data:
        host['hostgroup_id'] = node_data['hostgroup_id']
    else:
        host['hostgroup_id'] = '1' #default hostgrup base
    if not options.dry_run:
        foreman.create_hosts(host)
    else:
        print host
