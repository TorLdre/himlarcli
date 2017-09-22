#!/usr/bin/env python
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.cinder import Cinder
from himlarcli.neutron import Neutron
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_dry_run(options.dry_run)
logger = ksclient.get_logger()
#novaclient = Nova(options.config, debug=options.debug, log=logger)
if hasattr(options, 'region'):
    regions = ksclient.find_regions(region_name=options.region)
else:
    regions = ksclient.find_regions()

if not regions:
    himutils.sys_error('no regions found!')

def action_create():
    quota = himutils.load_config('config/quotas/%s.yaml' % options.quota)
    if options.quota and not quota:
        himutils.sys_error('Could not find quota in config/quotas/%s.yaml' % options.quota)
    test = 1 if options.type == 'test' else 0
    project = ksclient.create_project(domain=options.domain,
                                      project=options.project,
                                      admin=options.admin.lower(),
                                      test=test,
                                      type=options.type,
                                      description=options.desc,
                                      quota={})
    if project:
        output = project.to_dict() if not isinstance(project, dict) else project
        output['header'] = "Show information for %s" % options.project
        printer.output_dict(output)
    if project and ksclient.is_valid_user(email=options.admin, domain=options.domain):
        role = ksclient.grant_role(project_name=options.project,
                                   email=options.admin,
                                   domain=options.domain)
        if role:
            output = role.to_dict() if not isinstance(role, dict) else role
            output['header'] = "Roles for %s" % options.project
            printer.output_dict(output)
    elif project:
        himutils.sys_error("admin %s not found as a user. no access granted!" % options.admin, 0)

    # Quotas
    for region in regions:
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        cinderclient = Cinder(options.config, debug=options.debug, log=logger, region=region)
        neutronclient = Neutron(options.config, debug=options.debug, log=logger, region=region)
        cinderclient.set_dry_run(options.dry_run)
        novaclient.set_dry_run(options.dry_run)
        neutronclient.set_dry_run(options.dry_run)
        if project and not isinstance(project, dict):
            project_id = project.id
        elif project and isinstance(project, dict) and 'id' in project:
            project_id = project['id']
        else:
            project_id = None
        if 'cinder' in quota and project:
            cinderclient.update_quota(project_id=project_id, updates=quota['cinder'])
        if 'nova' in quota and project:
            novaclient.update_quota(project_id=project_id, updates=quota['nova'])
        if 'neutron' in quota and project:
            neutronclient.update_quota(project_id=project_id, updates=quota['neutron'])

def action_grant():
    if not ksclient.is_valid_user(email=options.user, domain=options.domain):
        himutils.sys_error('User %s not found as a valid user.' % options.user)
    project = ksclient.get_project_by_name(project_name=options.project, domain=options.domain)
    if not project:
        himutils.sys_error('No project found with name %s' % options.project)
    if hasattr(project, 'type') and (project.type == 'demo' or project.type == 'personal'):
        himutils.sys_error('Project are %s. User access not allowed!' % project.type)
    role = ksclient.grant_role(project_name=options.project,
                               email=options.user,
                               domain=options.domain)
    if role:
        output = role.to_dict() if not isinstance(role, dict) else role
        output['header'] = "Roles for %s" % options.project
        printer.output_dict(output)

def action_delete():
    question = 'Delete project %s and all resources' % options.project
    if not options.force and not himutils.confirm_action(question):
        return
    ksclient.delete_project(options.project, domain=options.domain)

def action_list():
    search_filter = dict()
    if options.filter and options.filter != 'all':
        search_filter['type'] = options.filter
    projects = ksclient.get_projects(domain=options.domain, **search_filter)
    count = 0
    printer.output_dict({'header': 'Project list (id, name, type)'})
    for project in projects:
        project_type = project.type if hasattr(project, 'type') else '(unknown)'
        output_project = {
            'id': project.id,
            'name': project.name,
            'type': project_type,
        }
        count += 1
        printer.output_dict(output_project, sort=True, one_line=True)
    printer.output_dict({'header': 'Project list count', 'count': count})

def action_show():
    project = ksclient.get_project_by_name(project_name=options.project, domain=options.domain)
    if not project:
        himutils.sys_error('No project found with name %s' % options.project)
    output_project = project.to_dict()
    output_project['header'] = "Show information for %s" % project.name
    printer.output_dict(output_project)
    roles = ksclient.list_roles(project_name=options.project)
    printer.output_dict({'header': 'Roles in project %s' % options.project})
    for role in roles:
        printer.output_dict(role, sort=True, one_line=True)
    for region in regions:
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        cinderclient = Cinder(options.config, debug=options.debug, log=logger, region=region)
        neutronclient = Neutron(options.config, debug=options.debug, log=logger, region=region)
        components = {'nova': novaclient, 'cinder': cinderclient, 'neutron': neutronclient}
        for comp, client in components.iteritems():
            quota = dict()
            if hasattr(client, 'get_quota_class'):
                quota = getattr(client, 'list_quota')(project.id)
            else:
                logger.debug('=> function get_quota_class not found for %s' % comp)
                continue
            if quota:
                quota.update({'header': '%s quota in %s' % (comp, region)})
                #printer.output_dict({'header': 'Roles in project %s' % options.project})
                printer.output_dict(quota)

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
