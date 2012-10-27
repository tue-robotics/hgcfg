# Mercurial config extension
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

'''config

Displays or modifies local and global configuration.
'''
import re
import os.path

from mercurial import util
if util.version() >= '1.9':
    from mercurial.scmutil import rcpath, userrcpath
else:
    rcpath = util.rcpath
    userrcpath = util.userrcpath


def local_rc(repo):
    return os.path.join(repo.path, 'hgrc')


def get_configs(ui, repo):
    allconfigs = rcpath()
    local_config = local_rc(repo)
    allconfigs += [local_config]
    userconfigs = set(userrcpath())

    configs = []

    # for all global configs
    for f in allconfigs:
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
    configs = get_configs(ui, repo)
    output = []
    max_value_len = 0
    for c in configs:
        if c['scope'] not in scopes:
            continue
        if c['exists']:
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
    choice = int(ui.prompt("%s: [%s]" % (prompt_msg, str(default)), pat=None,
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
        if not c['writeable']:
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


def write_value_to_file(ui, repo, section, key, value, rcfile):
    inside_section = False
    wrote_value = False
    new = ''

    for line in open(rcfile, 'r'):
        m = re.match("^\s*\[(.*)\]", line)
        if m:
            if section == m.group(1):
                inside_section = True
                new += line
                if not wrote_value:
                    new += ("%s = %s\n" % (key, value))
                    wrote_value = True
            else:
                inside_section = False
                new += line
        else:
            if inside_section:
                m = re.match("\s*" + re.escape(key) + "\s*=(.*)", line)
                if m:
                    if not ui.configbool('config', 'delete_on_replace', False):
                        new += ';' + line
                else:
                    new += line
            else:
                new += line
    # if we haven't written the value yet it's because we never found the
    # right section, so we'll make it now
    if not wrote_value:
        new += "\n[%s]\n%s = %s\n" % (section, key, value)

    # write new file
    open(rcfile, 'w').write(new)
    return True


def edit_config_file(ui, rc_file):
    contents = open(rc_file, 'r').read()
    new_contents = ui.edit(("HG: editing hg config file: %s\n\n" % rc_file) +
        contents, ui.username())
    if new_contents != contents:
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


def config(ui, repo, key, value=None, **opts):
    """View or modify a configuration value

    Example of viewing a configuration value:

        hg config ui.username

    When viewing a configuration value, all available config files will be
    queried.  To view more information about which file contains which value,
    enable verbose output by using the --debug option.  If more than one value
    is listed, the last value is one currently used by hg.  You can verify
    this by using the builtin hg command 'showconfig'.

    Example of setting a configuration value:

        hg config ui.username myname

    When modifying or setting a value, the local configuration will be used by
    default.  Use the --user option to set the value in a per-user config.
    Use the --global option to set the value in a global config.

    You will be prompted if more than one config exists and is writeable by you.
    """
    pattern = "([a-zA-Z_]+[a-zA-Z0-9_\-]*)\.([a-zA-Z_]+[a-zA-Z0-9\._\-]*)"
    m = re.match(pattern, key)
    if not m:
        ui.warn("invalid key syntax\n")
        return
    section = m.group(1)
    key = m.group(2)

    scopes = set()
    if opts['local']:
        scopes.add('local')
    if opts['user']:
        scopes.add('user')
    if opts['global']:
        scopes.add('global')
    if not scopes:
        scopes.add('local')

    # no value given, we will show them the value
    if value == None:
        show_value(ui, repo, section, key, scopes)
    # try to set a value
    else:
        # for these values, I think it's best to default to local config
        write_value(ui, repo, section, key, value, scopes)


cmdtable = {
        "config": (config,
            [('l', 'local', None, 'use local config file (default)'),
             ('u', 'user', None, 'use per-user config file(s)'),
             ('g', 'global', None, 'use global config file(s)')],
             "KEY.NAME [NEW_VALUE]"),
        "editconfig": (edit_config,
            [('l', 'local', None, 'edit local config file (default)'),
             ('u', 'user', None, 'use per-user config file(s)'),
             ('g', 'global', None, 'edit global config file(s)')],
            ""),
        "listconfigs": (list_configs,
            [],
            "")
        }
