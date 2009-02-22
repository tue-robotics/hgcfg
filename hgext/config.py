#!/usr/bin/env python

'''config

Displays or modifies local and global configuration.
'''

from mercurial import hg
from mercurial import util
import re
import os.path


# every command must take a ui and and repo as arguments.
# opts is a dict where you can find other command line flags
#
# Other parameters are taken in order from items on the command line that
# don't start with a dash.  If no default value is given in the parameter list,
# they are required.
# 
# For experimenting with Mercurial in the python interpreter: 
# Getting the repository of the current dir: 
#    >>> from mercurial import hg, ui
#    >>> repo = hg.repository(ui.ui(), path = ".")

def local_rc(repo):
    return os.path.join(repo.path, 'hgrc')

def getconfigs(ui, repo):
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

def showconfigs(ui, repo, **opts):
    """Show config files used by hg"""
    configs = getconfigs(ui, repo)

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
        ui.write(" %s %s %s\n" % (exists_str, c['path'], writeable_str))

def show_value(ui, repo, section, key, scope = None):
    configs = getconfigs(ui, repo)
    output = []
    max_path_len = 0
    for c in configs:
        if scope and scope != c['scope']: continue
        if c['exists']:
            value = get_value(ui, section, key, c['path'])
            if value:
                output.append( {'p': c['path'], 'v': value} )
                max_path_len = max([max_path_len, len(c['path'])])
    if scope:
        scope_str = " in %s config" % scope
    else:
        scope_str = ''
    if len(output) > 0:
        ui.write('values found for %s.%s%s:\n' % (section, key, scope_str))
        for o in output:
            ui.write(' %-*s  %s\n' % (max_path_len, o['p'], o['v']))
    else:
        ui.write('no values found for %s.%s%s\n' % (section, key, scope_str))

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

def write_value(ui, repo, section, key, value, scope = None):
    if scope == 'local':
        # easy one
        write_value_tofile(ui, repo, section, key, value, local_rc(repo))
        return
    else:
        # we are here because user chose global scope or all scopes
        # may have a choice of files to edit from, start from bottom
        configs = getconfigs(ui, repo)
        usable_configs = []
        for c in reversed(configs):
            if scope and scope != c['scope']: continue
            if not c['writeable']: continue
            usable_configs.append(c)
        if len(usable_configs) < 1:
            ui.write("no usable configs to write value to, run 'hg showconfigs'\n")
            return False
        if len(usable_configs) == 1:
            write_value_tofile(ui, repo, section, key, value, configs[0]['path'])
        else:
            # give them a choice
            ui.write("multiple config files to choose from, please select:\n")
            i = 0
            for c in usable_configs:
                ui.write("[%d] %s\n" % (i, c['path']))
                i += 1
            ui.prompt("which file do you want to write to: [0]", pat=None, default="0")


def write_value_tofile(ui, repo, section, key, value, rcfile):
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
    return value

def config(ui, repo, key, value = None, **opts):
    """View and modify local and global configuration"""
    m = re.match("([a-zA-Z_]+[a-zA-Z0-9_])*\.([a-zA-Z_]+[a-zA-Z0-9\._]*)", key)
    if not m:
        ui.write("invalid key syntax\n")
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
            "[options]")
        ,
        "showconfigs": (showconfigs,
            [],
            "")
  }

