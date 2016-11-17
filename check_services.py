#!/usr/bin/env python
import utils
import sys
import httplib
import statsd
from himlarcli import utils as himutils

desc = 'Do a remote check of web services'
options = utils.get_options(desc, hosts=False)

# Himmlar config
config = himutils.get_config(options.config)
region = config.get('openstack', 'region')
logger = himutils.get_logger(__name__, config, options.debug)

# statsd
statsd_server = config.get('statsd', 'server')
statsd_port = config.get('statsd', 'port')
prefix = 'uh-iaas.%s.checks' % region
statsd = statsd.StatsClient(statsd_server, statsd_port, prefix=prefix)

# Services to check
services = himutils.load_region_config('config/checks', region=region, log=logger)

for name, check in sorted(services['checks'].iteritems()):
    if 'timeout' in check:
        timeout = check['timeout']
    else:
        timeout = 10
    if (check['ssl']):
        c = httplib.HTTPSConnection(check['host'], timeout=timeout)
    else:
        c = httplib.HTTPConnection(check['host'], timeout=timeout)
    c.request("HEAD", check['url'])
    response = c.getresponse()
    #print response.status
    #print response.getheaders()
    statsd.gauge(name, response.status)
    if response.status == check['code']:
        statsd.gauge(name, 1)
        print '%s -> ok' % check['host']
    else:
        statsd.gauge(name, 0)
        logger.debug('=> %s = %s' % (name, response.status))
        print '%s -> failed' % check['host']

    logger.debug('=> headers for %s: %s' % (name, response.getheaders()))
