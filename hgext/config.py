# Mercurial config extension
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

'''config

Displays or modifies local and global configuration.
'''
import re
import os.path

from mercurial import util, commands
from mercurial.config import config as config_file

if util.version() >= '1.9':
    from mercurial.scmutil import rcpath, userrcpath
else:
    rcpath = util.rcpath
    userrcpath = util.userrcpath


def local_rc(repo):
    if repo is None:
        return None
    return os.path.join(repo.path, 'hgrc')


def get_configs(ui, repo):
    allconfigs = rcpath()
    local_config = local_rc(repo)
    if local_config is not None:
        # rcpath() returns a reference to a global list, must not modify
        # it in place by "+=" but instead create a copy by "+".
        allconfigs = allconfigs + [local_config]
    userconfigs = set(userrcpath())

    configs = []
    paths = set()

    # for all global configs
    for f in allconfigs:
        if f in paths:
            continue
        paths.add(f)

        if f == local_config:
            scope = 'local'
        elif f in userconfigs:
            scope = 'user'
        else:
            scope = 'global'
        if not os.path.exists(f):
            exists = False
            writeable = False
        else:
            exists = True
            if os.access(f, os.W_OK):
                writeable = True
            else:
                writeable = False
        configs.append({'scope': scope, 'path': f, 'exists': exists,
            'writeable': writeable})

    return configs


def list_configs(ui, repo, **opts):
    """List all config files searched for and used by hg

    This command lists all the configuration files searched for by hg in
    order.  Each file name is preceeded by a status indicator: The status
    is '!' if the configuration file is missing. If the file is writable
    by the current user the status is 'rw', otherwise 'ro'.
    """

    configs = get_configs(ui, repo)

    for c in configs:
        if not c['exists']:
            status_str = '! '
        elif c['writeable']:
            status_str = 'rw'
        else:
            status_str = 'ro'
        ui.status(" %s %-6s %s\n" % (status_str, c['scope'], c['path']))


def show_value(ui, repo, section, key, scopes, **opts):
    configs = [
        c for c in get_configs(ui, repo)
            if c['scope'] in scopes and c['exists']
    ]
    def confs():
        for c in configs:
            conf = config_file()
            conf.read(c['path'])
            yield c, conf
    output = []
    max_value_len = 0

    if ui.quiet and section is None:
        # list unique section names
        sections = set()
        for c, conf in confs():
            sections.update(conf.sections())
        for s in sorted(sections):
            ui.write('  [%s]\n' % s)
        return

    if section is None:
        # list names of sections in each file
        for c, conf in confs():
            ui.write('scope=%s\n' % c['scope'])
            ui.write('file=%s\n' % c['path'])
            for s in conf.sections():
                ui.write('  [%s]\n' % s)
            ui.write('\n')
        return

    if key is None and ui.quiet:
        # list all unique items in section "section"
        items = dict()
        for c, conf in confs():
             items.update(conf.items(section))
        ui.write('  [%s]\n' % section)
        for item in sorted(items.iteritems()):
            ui.write('    %s=%s\n' % item)
        ui.write('\n')
        return

    if key is None:
        # list all items in section "section" in each file
        for c, conf in confs():
            if section in conf:
                ui.write('scope=%s\n' % c['scope'])
                ui.write('file=%s\n' % c['path'])
                ui.write('  [%s]\n' % section)
                for item in conf.items(section):
                    ui.write('    %s=%s\n' % item)
                ui.write('\n')
        return

    for c in configs:
        value = get_value(ui, section, key, c['path'])
        if value != None:
            output.append({'p': c['path'], 'v': value})
            max_value_len = max([max_value_len, len(value)])
    scope_str = " in %s config" % '/'.join(scopes)
    if len(output) > 0:
        ui.note('values found for %s.%s%s:\n' % (section, key, scope_str))
        for o in output:
            ui.note(' ')
            if o is output[-1]:
                ui.write(o['v'])
            else:
                ui.status(o['v'])
            ui.status('%*s' % (max_value_len - len(o['v']) + 2, ''))
            ui.note('%s' % o['p'])
            if o is output[-1]:
                ui.write("\n")
            else:
                ui.status("\n")
    else:
        ui.note('no values found for %s.%s%s\n' % (section, key, scope_str))


def get_value(ui, section, key, rcfile):
    inside_section = False
    value = None
    for line in open(rcfile, 'r'):
        m = re.match("^\s*\[(.*)\]", line)
        if m:
            if section == m.group(1):
                inside_section = True
            else:
                inside_section = False
        else:
            if inside_section:
                m = re.match("\s*" + re.escape(key) + "\s*=(.*)", line)
                if m:
                    value = m.group(1).strip()
    return value


def get_config_choice(ui, configs, start_msg, prompt_msg, default=0):
    i = 0
    ui.status(start_msg)
    for c in configs:
        ui.status("[%d] %s\n" % (i, c['path']))
        i += 1
    choice = int(ui.prompt("%s: [%s]" % (prompt_msg, str(default)),
        default=str(default)))
    if choice < 0 or choice > (len(configs) - 1):
        return False
    else:
        return choice


def get_writeable_configs(ui, repo, scopes):
    configs = get_configs(ui, repo)
    writeable_configs = []
    for c in reversed(configs):
        if c['scope'] not in scopes:
            continue
        if not c['writeable'] and not c['scope'] == 'local':
            continue
        writeable_configs.append(c)
    return writeable_configs


def write_value(ui, repo, section, key, value, scopes):
    # may have a choice of files to edit from, start from bottom
    writeable_configs = get_writeable_configs(ui, repo, scopes)
    if len(writeable_configs) < 1:
        ui.warn("no writeable configs to write value to, run 'hg listconfigs'\n")
        return False
    if len(writeable_configs) == 1:
        return write_value_to_file(ui, repo, section, key, value,
                writeable_configs[0]['path'])
    else:
        # give them a choice
        choice = get_config_choice(ui, writeable_configs,
                "multiple config files to choose from, please select:\n",
                "which file do you want to write to")
        if choice is False:
            ui.warn("invalid choice\n")
            return False
        else:
            ui.status("writing value to config [%d]\n" % choice)
            return write_value_to_file(ui, repo, section, key, value,
                    writeable_configs[int(choice)]['path'])


def write_value_to_file_(ui, repo, section, key, value, rcfile, delete):
    inside_section = False
    wrote_value = False
    new = ''

    for line in open(rcfile, 'a+'):
        m = re.match("^\s*\[(.*)\]", line)
        if m:
            if section == m.group(1):
                inside_section = True
                new += line
                if not wrote_value and value is not None:
                    new += ("%s = %s\n" % (key, value))
                    wrote_value = True
            else:
                inside_section = False
                new += line
        else:
            if inside_section:
                m = re.match("\s*" + re.escape(key) + "\s*=(.*)", line)
                if m:
                    if not delete:
                        new += ';' + line
                else:
                    new += line
            else:
                new += line
    # if we haven't written the value yet it's because we never found the
    # right section, so we'll make it now
    if not wrote_value and value is not None:
        new += "\n[%s]\n%s = %s\n" % (section, key, value)

    # write new file
    open(rcfile, 'w').write(new)
    return True

def write_value_to_file(ui, repo, section, key, value, rcfile):
    return write_value_to_file_(ui, repo, section, key, value, rcfile, ui.configbool('config', 'delete_on_replace', False))


def edit_config_file(ui, rc_file):
    orig_contents = open(rc_file, 'a+').read()
    banner = "#HG: editing hg config file: %s\n\n" % rc_file
    contents = banner + orig_contents
    new_contents = ui.edit(contents, ui.username())
    new_contents = re.sub(r'^%s' % re.escape(banner), '', new_contents)
    if new_contents != orig_contents:
        open(rc_file, 'w').write(new_contents)


def edit_config(ui, repo, **opts):
    """Edits your local or global hg configuration file

    This command will launch an editor to modify the local .hg/hgrc config
    file by default.

    Use the --user option to edit personal config files.

    Use the --global option to edit global config files.

    If more than one writeable config file is found, you will be prompted
    as to which one you would like to edit.
    """
    scopes = set()
    if opts['local']:
        scopes.add('local')
    if opts['user']:
        scopes.add('user')
    if opts['global']:
        scopes.add('global')
    if not scopes:
        scopes.add('local')

    writeable_configs = get_writeable_configs(ui, repo, scopes)
    if len(writeable_configs) < 1:
        ui.warn("no editable configs to edit, run 'hg listconfigs'\n")
        return False
    if len(writeable_configs) == 1:
        return edit_config_file(ui, writeable_configs[0]['path'])
    else:
        # give them a choice
        choice = get_config_choice(ui, writeable_configs,
                "multiple config files to choose from, please select:\n",
                "which file do you want to edit")
        if choice is False:
            ui.warn("invalid choice\n")
            return False
        else:
            ui.status("editing config file [%d]\n" % choice)
            return edit_config_file(ui, writeable_configs[int(choice)]['path'])


def config(ui, repo, key='', value=None, **opts):
    """View or modify a configuration value

    Example of viewing a configuration section:

        hg config paths

    Example of viewing a configuration value:

        hg config ui.username

    When viewing a configuration value, all available config files will be
    queried.  To view more information about which file contains which value,
    enable verbose output by using the --verbose option.  If more than one value
    is listed, the last value is one currently used by hg.  You can verify
    this by using the builtin hg command 'showconfig'.

    Using the --quiet option shows a combined result instead of listing results
    for each config file separately.

    Example of setting a configuration value:

        hg config ui.username myname

    When modifying or setting a value, the local configuration will be used by
    default.  Use the --user option to set the value in a per-user config.
    Use the --global option to set the value in a global config.

    You will be prompted if more than one config exists and is writeable by you.
    """
    pattern = r"(?:([a-z_][a-z0-9_-]*)(?:\.([a-z_][a-z0-9._-]*))?)?$"
    m = re.match(pattern, key, re.I)
    if not m:
        ui.warn("invalid key syntax\n")
        return
    section = m.group(1)
    key = m.group(2)

    if opts['delete']:
        if value is not None:
            ui.warn('must not specify NEW_VALUE with --delete option')
            return
        if not section or not key:
            ui.warn('must specify SECTION.KEY with --delete option')
            return

    default_get_scopes = set(['local', 'user', 'global'])
    default_set_scopes = set(['local'])
    scopes = set()
    if opts['local']:
        scopes.add('local')
    if opts['user']:
        scopes.add('user')
    if opts['global']:
        scopes.add('global')

    # no value given, we will show them the value
    if value is None and not opts['delete']:
        show_value(ui, repo, section, key, scopes or default_get_scopes)
    # try to set a value
    else:
        # for these values, I think it's best to default to local config
        write_value(ui, repo, section, key, value, scopes or default_set_scopes)

cmdtable = {
        "config": (config,
            [('d', 'delete', None, 'delete KEY.NAME'),
             ('l', 'local', None, 'use local config file (default)'),
             ('u', 'user', None, 'use per-user config file(s)'),
             ('g', 'global', None, 'use global config file(s)')],
             "[KEY[.NAME]] [NEW_VALUE]"),
        "editconfig": (edit_config,
            [('l', 'local', None, 'edit local config file (default)'),
             ('u', 'user', None, 'use per-user config file(s)'),
             ('g', 'global', None, 'edit global config file(s)')],
            ""),
        "listconfigs": (list_configs,
            [],
            "")
        }
commands.optionalrepo += ' ' + ' '.join(cmdtable.keys())
