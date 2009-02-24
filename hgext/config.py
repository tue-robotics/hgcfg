#!/usr/bin/env python

'''config

Displays or modifies local and global configuration.
'''

from mercurial import hg
from mercurial import util
import re
import os.path


def local_rc(repo):
    return os.path.join(repo.path, 'hgrc')

def get_configs(ui, repo):
    allconfigs = util.rcpath()
    local_config = local_rc(repo)
    allconfigs += [local_config]

    configs = []

    # for all global configs
    for f in allconfigs:
        if f == local_config:
            scope = 'local'
        else:
            scope = 'global'
        if not os.path.exists(f):
            exists = False
            writeable = False
            #configs.append( {'scope': 'global', 'path': f, 'exists': False, 'writeable': False} )
        else:
            exists = True
            if os.access(f, os.W_OK):
                writeable = True
            else:
                writeable = False
        configs.append( {'scope': scope, 'path': f, 'exists': exists, 'writeable': writeable} )

    return configs

def show_configs(ui, repo, **opts):
    """Show config files used by hg"""
    configs = get_configs(ui, repo)

    for c in configs:
        if c['exists']:
            exists_str = '*'
            if c['writeable']:
                writeable_str = ''
            else:
                writeable_str = '(ro)'
        else:
            exists_str = '!'
            writeable_str = ''
        ui.status(" %s %s %s\n" % (exists_str, c['path'], writeable_str))

def show_value(ui, repo, section, key, scope = None, **opts):
    configs = get_configs(ui, repo)
    output = []
    max_value_len = 0
    for c in configs:
        if scope and scope != c['scope']: continue
        if c['exists']:
            value = get_value(ui, section, key, c['path'])
            if value != None:
                output.append( {'p': c['path'], 'v': value} )
                max_value_len = max([max_value_len, len(value)])
    if scope:
        scope_str = " in %s config" % scope
    else:
        scope_str = ''
    if len(output) > 0:
        ui.note('values found for %s.%s%s:\n' % (section, key, scope_str))
        for o in output:
            ui.note(' ')
            if o is output[-1]: ui.write(o['v'])
            else:               ui.status(o['v'])
            ui.status('%*s' % (max_value_len - len(o['v']) + 2, ''))
            ui.note('%s' % o['p'])
            if o is output[-1]: ui.write("\n")
            else:               ui.status("\n")
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
                    #ui.write("got the value: '%s'\n" % value)
                    #ui.write(value + "\n")
    return value

def get_config_choice(ui, configs, start_msg, prompt_msg, default = 0):
    i = 0
    ui.status(start_msg)
    for c in configs:
        ui.status("[%d] %s\n" % (i, c['path']))
        i += 1
    choice = int(ui.prompt("%s: [%s]" % (prompt_msg, str(default)), pat=None, default=str(default)))
    #ui.write("i got this: %s   %d\n" % (choice, int(choice)))
    if choice < 0 or choice > (len(configs) - 1):
        return False
    else:
        return choice

def get_writeable_configs(ui, repo, scope = None):
    configs = get_configs(ui, repo)
    writeable_configs = []
    for c in reversed(configs):
        if scope and scope != c['scope']: continue
        if not c['writeable']: continue
        writeable_configs.append(c)
    return writeable_configs

def write_value(ui, repo, section, key, value, scope = None):
    if scope == 'local':
        # easy one
        return write_value_to_file(ui, repo, section, key, value, local_rc(repo))
    else:
        # we are here because user chose global scope or all scopes
        # may have a choice of files to edit from, start from bottom
        configs = get_configs(ui, repo)
        writeable_configs = get_writeable_configs(ui, repo, scope)
        if len(writeable_configs) < 1:
            ui.warn("no writeable configs to write value to, run 'hg showconfigs'\n")
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
                    #if not wrote_value:
                        ## write it now underneath the one we just commented
                        #new.append("%s = %s" % (key, value))
                        #wrote_value = True
                else:
                    new += line
            else:
                new += line
    # if we haven't written the value yet it's because we never found the right
    # section, so we'll make it now
    if not wrote_value:
        new += "\n[%s]\n%s = %s\n" % (section, key, value)

    # write new file
    open(rcfile, 'w').write(new)
    return True

def edit_config_file(ui, rc_file):
    contents = open(rc_file, 'r').read()
    new_contents = ui.edit(("HG: editing hg config file: %s\n\n" % rc_file) + contents, ui.username())
    if new_contents != contents:
        open(rc_file, 'w').write(new_contents)

def edit_config(ui, repo, **opts):
    scope = 'local' # local by default
    if opts['global']: scope = 'global'
    if opts['local'] and opts['global']: scope = None # both global/local
    if scope == 'local':
        # easy only one choice
        return edit_config_file(ui, local_rc(repo))

    writeable_configs = get_writeable_configs(ui, repo, scope)
    if len(writeable_configs) < 1:
        ui.warn("no editable configs to edit, run 'hg showconfigs'\n")
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


def config(ui, repo, key, value = None, **opts):
    """View and modify local and global configuration"""
    m = re.match("([a-zA-Z_]+[a-zA-Z0-9_\-]*)\.([a-zA-Z_]+[a-zA-Z0-9\._\-]*)", key)
    if not m:
        ui.warn("invalid key syntax\n")
        return
    section = m.group(1)
    key = m.group(2)

    scope = None
    if opts['local']: scope = 'local'
    if opts['global']: scope = 'global'

    # no value given, we will show them the value
    if value == None:
        show_value(ui, repo, section, key, scope)
    # try to set a value
    else:
        # for these values, I think it's best to default to local config
        if scope == None: scope = 'local'
        write_value(ui, repo, section, key, value, scope)


cmdtable = {
        "config": (config,
            [('l', 'local', None, 'use local config file (default)'),
             ('g', 'global', None, 'use global config file(s)')],
            "")
        ,
        "editconfig": (edit_config,
            [('l', 'local', None, 'edit local config file (default)'),
             ('g', 'global', None, 'edit global config file(s)')],
            "")
        ,
        "showconfigs": (show_configs,
            [],
            "")
        }

