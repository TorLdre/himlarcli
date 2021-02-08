#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as utils
from datetime import date

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

regions = kc.find_regions()

def action_count():
    projects = kc.get_projects(type='demo')
    count_all = count_60 = 0
    for project in projects:
        for region in regions:
            nc = utils.get_client(Nova, options, logger, region)
            instances = nc.get_project_instances(project_id=project.id)
            if not instances:
                continue
            count_all += 1
            for i in instances:
                created_at = utils.get_date(i.created_a, None, '%Y-%m-%d')
                if date.today() - created_at >= 60:
                    count_60 += 1
    printer.output_dict({'header': 'count', 'all': count_all, '>60': count_60})
    #print count

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
