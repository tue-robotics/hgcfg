# Mercurial "hgcfg" extension
#
#
# Copyright 2013 Brian Mearns ("Maytag Metalark"), Risto Kankkunen, and
# Alex "alu@zpuppet.org"
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
#
# This extension is derived from the "config" extension originally written by
# bitbucket user "alu". That extensions webpage is 
# <http://mercurial.selenic.com/wiki/ConfigExtensionCommandLine>, and the
# extension repository is hosted at: <https://bitbucket.org/alu/hgconfig>.
#
# The extension was subsequently forked and modified by Risto Kankkunen. This
# fork is hosted at <https://bitbucket.org/kankri/hgconfig>.
#
# The version of the extension you're currently viewing is another fork by Brian
# Mearns. It incorporates the changes made by Risto Kankkunen up through 2 Dec
# 2012, revision 6526e84, as well as a number of other changes.
#
# This version of the extension is named "hgcfg" and is hosted at
# <https://bitbucket.org/bmearns/hgconfig>.
#
'''hgcfg

Displays or modifies local, user, and global configuration.
'''

VERSION = [0, 1, 0, 0, 'dev']


##############################################################################


import re
import os.path
import sys

from mercurial import util, commands
from mercurial.config import config as config_file
from mercurial.i18n import _

sys.path.append(os.path.dirname(__file__))
from deprecate import replace_deprecated, deprecated

if util.version() >= '1.9':
    from mercurial.scmutil import rcpath, userrcpath
else:
    rcpath = util.rcpath
    userrcpath = util.userrcpath

def hgcmd(func):
    """
    function decorator, but it doesn't do anything, it's just a convenient
    label.
    """
    return func

@replace_deprecated("local_rc")
def localrc(repo=None):
    """
    Return the filesystem path to the repository's hgrc config file
    as a `str`, or `None` if the given `repo` is None.
    """
    if repo is None:
        return None
    return os.path.join(repo.path, 'hgrc')

@replace_deprecated("get_configs")
def getconfigs(ui, repo):
    """
    Get a sequence of possible configuration files, including local
    (repository), user, and global.

    Each item in the returned sequence is a dictionary with the following keys:

    `scope`
        One of 'local', 'user', or 'global'.

    `path`
        The filesystem path to the config file.

    `exists`
        A `bool` indicating whether or not the file currently exists on the
        filesystem.

    `writeable`
        A `bool` indicating whether or not the file is writeable by the
        current user.
            
    """
    allconfigs = rcpath()
    local_config = localrc(repo)
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


@hgcmd
@deprecated("Use 'listcfgs' instead")
@replace_deprecated("list_configs")
def listconfigs(*args, **kwargs):
    """ deprecated alias for `listcfgs`.
    """
    return listcfgs(*args, **kwargs)

@hgcmd
def listcfgs(ui, repo, **opts):
    """list all config files searched for and used by hg

    This command lists all the configuration files searched for by hg in
    order.  Each file name is preceeded by a status indicator: The status
    is '!' if the configuration file is missing. If the file is writable
    by the current user the status is 'rw', otherwise 'ro'.
    """

    configs = getconfigs(ui, repo)

    for c in configs:
        label = "hgcfg.file." + c['scope']

        if not c['exists']:
            status_str = '! '
            label += ".missing"
        elif c['writeable']:
            status_str = 'rw'
            label += ".writeable"
        else:
            status_str = 'ro'
            label += ".readonly"

        ui.status(_(" %s %-6s " % (status_str, c['scope'])), label=label)
        ui.write(c['path'], label=label)
        ui.write(_("\n"))


@replace_deprecated("show_value")
def showvalue(ui, repo, section, key, scopes, **opts):
    """
    Shows values for specified configuration keys, or lists all
    keys and there values in the specified section, or lists all sections
    in the specified scope.
    """

    #Get a list of config files which exist and are in scope.
    configs = [
        c for c in getconfigs(ui, repo)
            if c['scope'] in scopes and c['exists']
    ]
    def confs():
        for c in configs:
            conf = config_file()
            conf.read(c['path'])
            yield c, conf

    #If it's quiet, then we aren't indicating which file it came from,
    # so we may as well make it a unique list.
    if ui.quiet and section is None:
        sections = set()
        for c, conf in confs():
            sections.update(conf.sections())
        for s in sorted(sections):
            uiwritesection(ui, s)
        return

    #Similar, but if it's not quiet, then we indicate which file each
    # section comes from, and don't make it unique.
    if section is None:
        for c, conf in confs():
            uiwritescope(ui, c, ui.status)
            uiwritefile(ui, c, ui.status)
            for s in conf.sections():
                uiwritesection(ui, s)
            ui.status('\n')
        return

    #List all unique items in the named section
    if ui.quiet and key is None:
        items = dict()
        for c, conf in confs():
             items.update(conf.items(section))
        uiwritesection(ui, section)

        actvals = {}
        for k, v in sorted(items.iteritems()):
            key = "%s.%s" % (section.replace(".", ".."),
                k.replace(".", ".."))
            if key not in actvals:
                actvals[key] = ui.config(section, k)
            uiwriteitem(ui, k, v, c, active = (v == actvals[key]))
        ui.write('\n')
        return

    #Same, but if not quiet, don't make it unique.
    if key is None:
        actvals = {}
        for c, conf in confs():
            if section in conf:
                uiwritescope(ui, c, ui.status)
                uiwritefile(ui, c, ui.status)
                uiwritesection(ui, section, c)
                for k, v in conf.items(section):
                    key = "%s.%s" % (section.replace(".", ".."),
                        k.replace(".", ".."))
                    if key not in actvals:
                        actvals[key] = ui.config(section, k)
                    uiwriteitem(ui, k, v, c, active = (v == actvals[key]))
                ui.status('\n')
        return

    #They specified both a section and a key, so find all values of it.
    output = []
    max_value_len = 0
    for c in configs:
        value = getvalue(ui, section, key, c['path'])
        if value != None:
            output.append({'p': c['path'], 'v': value, 's': c['scope']})
            max_value_len = max([max_value_len, len(value)])

    maxscopelen = 0
    i18nscopes = {}
    for scope in scopes:
        s = _(scope)
        i18nscopes[scope] = s
        maxscopelen = max([maxscopelen, len(s)])

    actualval = ui.config(section, key)
    actualfound = False

    scope_str = " in %s config" % '/'.join(scopes)
    if len(output) > 0:
        ui.note(_('values found for '))
        ui.note('%s.%s' % (section, key), label='hgcfg.keyname')
        ui.note(_(scope_str + ":\n") )
        for o in output:

            #Fore --quiet, only show the correct value.
            if o['v'] == actualval:
                selected = '.selected'
                write = ui.write
                prefix = '* '
                actualfound = True
            else:
                selected = ''
                write = ui.status
                prefix = '  '
            label = 'hgcfg.item.value' + selected
            write(prefix, label=label)
            write(o['v'], label=label)

            # Fill space before writing the scope and path.
            ui.note('%*s' % (max_value_len - len(o['v']) + 2, ''))

            #Write the scope and path
            scope = i18nscopes[o['s']]
            ui.note(_('('))
            ui.note(scope, label='hgcfg.scope.' + o['s'])
            ui.note(_(')'))
            ui.note('%*s' % (maxscopelen - len(scope) + 1, ''))
            ui.note(o['p'], label='hgcfg.file.' + o['s'])

            write("\n")

        if not actualfound:
            ui.note(_("\ncurrent active value not in scope ("))
            ui.note(str(actualval), label='hgcfg.item.value.selected')
            ui.note(_(")\n"))
    else:
        ui.note(_('no values found for '))
        ui.note('%s.%s' % (section, key), label='hgcfg.keyname')
        ui.note(_(scope_str + ":\n") )


@replace_deprecated("get_value")
def getvalue(ui, section, key, rcfile):
    """
    Returns the value of the specified key from the specified config file.
    """
    values = getvalues(ui, section, key, rcfile)
    if len(values) == 0:
        return None
    else:
        return values[0]

def getvalues(ui, section, key, rcfile):
    """
    Returns all values of the specified key found in the specified file.
    """
    inside_section = False
    values = []
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
                    values.append(m.group(1).strip())
    return values


@replace_deprecated("get_config_choice")
def getconfigchoice(ui, configs, start_msg, prompt_msg, default=0):
    """
    Ask the user which of the given configs they want to act on.
    The `configs` parameter should come from `getconfigs` or similar.
    """
    i = 0
    ui.status(start_msg)
    for c in configs:
        ui.status(_("[%d] " % i))
        ui.status(c['path'], label='hgcfg.file.' + c['scope'])
        ui.status(_("\n"))
        i += 1

    choice = ui.prompt(prompt_msg + _(": [%s]" % (str(default))),
        default=str(default))

    try:
        choice = int(choice)
    except ValueError:
        return False

    if choice < 0 or choice > (len(configs) - 1):
        return False
    else:
        return choice


@replace_deprecated("get_writeable_configs")
def getwriteableconfigs(ui, repo, scopes):
    """
    Returns a sequence of config that are writeable by the current user and
    which fall within the given scopes. Note that the local config is always
    considered writeable.

    Returned elements are like those returned by `getconfigs`.
    """
    configs = getconfigs(ui, repo)
    writeable_configs = []
    for c in reversed(configs):
        if c['scope'] not in scopes:
            continue
        if not c['writeable'] and not c['scope'] == 'local':
            continue
        writeable_configs.append(c)
    return writeable_configs


@replace_deprecated("write_value")
def writevalue(ui, repo, section, key, value, scopes):

    # may have a choice of files to edit from, start from bottom
    writeable_configs = getwriteableconfigs(ui, repo, scopes)
    if len(writeable_configs) < 1:
        ui.warn(_("no writeable configs to write value to, "
            "try 'hg listconfigs'\n"))
        return False

    if len(writeable_configs) == 1:
        return writevaluetofile(ui, repo, section, key, value,
                writeable_configs[0]['path'])
    else:
        # give them a choice
        choice = getconfigchoice(ui, writeable_configs,
                _("multiple config files to choose from, please select:\n"),
                _("which file do you want to write to"))
        if choice is False:
            ui.warn(_("invalid choice\n"))
            return False
        else:
            ui.status(_("writing value to config [%d]\n" % choice))
            return writevaluetofile(ui, repo, section, key, value,
                    writeable_configs[int(choice)]['path'])



@replace_deprecated("write_value_to_file_")
def writevaluetofile_(ui, repo, section, key, value, rcfile, delete):
    """
    Updates the given config file to assign the specified value to the specified
    key. If the key already exists in the file, then it is either overwritten
    (if `delete` is True), or it is commented out and the new value is written
    before it.
    """

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

@replace_deprecated("write_value_to_file")
def writevaluetofile(ui, repo, section, key, value, rcfile):
    """
    Simple delegte to `writevaluetofile_`, but gets the `delete` parameter from
    the `hgcfg.delete_on_replace` configuration value.
    """
    delete = ui.configbool("hgcfg", "delete_on_replace", None)
    if delete is None:
        delete = ui.configbool("config", "delete_on_replace", False)
    return writevaluetofile_(ui, repo, section, key, value, rcfile, delete)


@replace_deprecated("edit_config_file")
def editconfigfile(ui, rc_file):
    """
    Allows the user to edit the specified config file. This uses the
    `ui.edit` function, similar to the one used for editing commit
    messages.
    """
    orig_contents = open(rc_file, 'a+').read()
    banner = _("#HG: editing hg config file: ") + rc_file + _("\n\n")
    contents = banner + orig_contents
    new_contents = ui.edit(contents, ui.username())
    new_contents = re.sub(r'^%s' % re.escape(banner), '', new_contents)
    if new_contents != orig_contents:
        open(rc_file, 'w').write(new_contents)


@hgcmd
@deprecated("Use 'editcfg' instead")
@replace_deprecated("edit_config")
def editconfig(*args, **kwargs):
    """ deprecated alias for `editcfg`.
    """
    return listcfgs(*args, **kwargs)

@hgcmd
def editcfg(ui, repo, **opts):
    """edits your local or global hg configuration file

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

    writeable_configs = getwriteableconfigs(ui, repo, scopes)
    if len(writeable_configs) < 1:
        ui.warn(_("no writeable configs to write value to, "
            "try 'hg listconfigs'\n"))
        return False

    if len(writeable_configs) == 1:
        return editconfigfile(ui, writeable_configs[0]['path'])
    else:
        # give them a choice
        choice = getconfigchoice(ui, writeable_configs,
                _("multiple config files to choose from, please select:\n"),
                _("which file do you want to edit"))
        if choice is False:
            ui.warn("invalid choice\n")
            return False
        else:
            ui.status(_("editing config file [%d]\n") % choice)
            return editconfigfile(ui, writeable_configs[int(choice)]['path'])


@hgcmd
@deprecated("Use 'cfg' instead.")
def config(*args, **kwargs):
    """deprecated alias for `cfg`"""
    return cfg(*args, **kwargs)
    
@hgcmd
def cfg(ui, repo, key='', value=None, **opts):
    """view or modify a configuration value

    To view all configuration sections across all files:
        
        hg config

    To view all configuration values in a certain section, across all files:

        hg config SECTION

    To view all configuration values for a particular key, across all files:

        hg config SECTION.KEY

    To set the value for a particular key:

        hg config SECTION.KEY VALUE

    To delete a key:

        hg config --delete SECTION.KEY


    With no arguments, prints out all available sections across all
    known configuration files relevant to the repository. By default,
    the sections are groups by file, and the path and scope is printed
    for each file. With the --quiet option, a unqiue list of all known
    sections is printed, with no information about file or scope.

    With one argument, the argument can be either a section name alone, or a
    section name and key name, joined with a dot.

    With just a section name, prints all configuration keys and values in the
    named section aross all relevant config files. By default, the print out is
    grouped by file, with path and scope information printed for each file. If
    the currently active value for a key is included in the printout, it is
    marked with a '*'. With the --quiet option, only a single section is
    printed, encompassing the lowest (most active) value for each key across all
    relevant config files.

    With a section name and a key name, all known values for the key across all
    relevant config files is printed, with the currently active value marked
    with a '*' (if present). With the --verbose option, the scope and config
    file are printed for each value. With the --quiet option, only the lowest
    (most active) value is printed.

    In all of the above cases, the default is to use all relevant config files.
    This can be refined by specifying the --local, --user, or --global option.
    These options can be combined, but if any are present, then only those
    scopes which are specified will be considered.

    With two arguments, the first should be a section name and key name pair, as
    above, and the second argument should be the value to configure the
    specified key as. By default, the local configuration file will be used. You
    can modify this by using the --local, --user, or --global option. If
    multiple files are found, you will be presented which a choice of which to
    modify. Note that only files which are writeable by you are considered.

    When the --delete option is given, there must be exactly one argument given,
    and it must contain both the section name and the key name. This works
    similarly to editing a key, except that the key is deleted from the config
    file. As with setting a key, the default is to use the local config file,
    but the --local, --user, and --global options can override this behavior. If
    multiple writeable config files are found, you will be presented with a
    choice of which to modify.

    By default, the --delete option does not actually remove anything from the
    config file, it simply comments out all occurrences the of specified key
    in the chosen file. If the "hgcfg.delete_on_replace" configuration value is
    present and True, then all occurrences of the key will actually be deleted
    from the file. You can put this in an active configuration file, or use the
    --config option to specify it for single use in the current command.

    """
    pattern = r"(?:([a-z_][a-z0-9_-]*)(?:\.([a-z_][a-z0-9._-]*))?)?$"
    m = re.match(pattern, key, re.I)
    if not m:
        ui.warn(_("invalid key syntax. try SECTION.KEY\n"))
        return
    section = m.group(1)
    key = m.group(2)

    if opts['delete']:
        if value is not None:
            ui.warn(_('must not specify NEW_VALUE with --delete option'))
            return
        if not section or not key:
            ui.warn(_('must specify SECTION.KEY with --delete option'))
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
        showvalue(ui, repo, section, key, scopes or default_get_scopes)
    # try to set a value
    else:
        # for these values, I think it's best to default to local config
        writevalue(ui, repo, section, key, value, scopes or default_set_scopes)
    #FIXME: --delete is not used.
    return


### Some utility functions for writing to the UI

def uiwritescope(ui, config, func=None):
    if func is None:
        func = ui.write
    func(_('scope=') + ('%s' % config['scope']), label='hgcfg.scope.'
        + config['scope'])
    func(_('\n'))

def uiwritefile(ui, config, func=None):
    if func is None:
        func = ui.write
    func(_('file=') + ('%s' % config['path']), label='hgcfg.file.'
        + config['scope'])
    func(_('\n'))

def uiwritesection(ui, section, config=None, func=None):
    if func is None:
        func = ui.write
    func('[%s]' % section, label='hgcfg.section')
    func(_('\n'))

def uiwriteitem(ui, k, v, config=None, func=None, active=False):
    if func is None:
        func = ui.write
    if active:
        prefix = _('    * ')
        selected = ".selected"
    else:
        prefix = _('      ')
        selected = ""
    func(prefix + k, label="hgcfg.item.key")
    func(_(' = '), label="hgcfg.item.sep")
    func(v, label="hgcfg.item.value" + selected)
    func('\n')
    



### Extensions Stuff

cmdtable = {
        "cfg": (cfg,
            [('d', 'delete', None, 'delete SECTION.KEY'),
             ('l', 'local', None, 'use local config file (default for set)'),
             ('u', 'user', None, 'use per-user config file(s)'),
             ('g', 'global', None, 'use global config file(s)')],
             "[options] [SECTION[.KEY [NEW_VALUE]]]"),
        "editcfg": (editcfg,
            [('l', 'local', None, 'edit local config file (default)'),
             ('u', 'user', None, 'use per-user config file(s)'),
             ('g', 'global', None, 'edit global config file(s)')],
            "[options]"),
        "listcfgs": (listcfgs,
            [],
            ""),
        }

### Add the deprecated command aliases.
for name in ["", "edit", "list"]:
    tail = "cfg"
    otail = "config"
    key = name + tail
    if key not in cmdtable:
        tail += "s"
        otail += "s"
        key = name + tail

    cmddef = list(cmdtable[key])
    cmddef[0] = getattr(sys.modules[__name__], name + otail)
    cmdtable[name + otail] = tuple(cmddef)


commands.optionalrepo += ' ' + ' '.join(cmdtable.keys())

colortable = {
    # A section name, like [paths] or [ui].
    'hgcfg.section':       'cyan',

    ### Paths to config files.

    ## Files with global scope.
    # In `hg config [SECTION[.KEY]]`
    'hgcfg.file.global'            :   'red',
    # In `hg listconfig`
    'hgcfg.file.global.missing'    :   'red ',
    'hgcfg.file.global.writeable'  :   'red bold',
    'hgcfg.file.global.readonly'   :   'red ',

    ## Files with user scope.
    'hgcfg.file.user'            :   'yellow',
    'hgcfg.file.user.missing'    :   'yellow ',
    'hgcfg.file.user.writeable'  :   'yellow bold',
    'hgcfg.file.user.readonly'   :   'yellow ',

    ## Files with local scope.
    'hgcfg.file.local'            :   'green',
    'hgcfg.file.local.missing'    :   'green ',
    'hgcfg.file.local.writeable'  :   'green bold',
    'hgcfg.file.local.readonly'   :   'green ',

    # Scope of a file or value.
    'hgcfg.scope.global':  'red bold',
    'hgcfg.scope.user':    'yellow bold',
    'hgcfg.scope.local':   'green bold',

    ## A key and it's value
    # The name of the key
    'hgcfg.item.key':      'none',
    # Whatever comes between the name and the value (e.g., '=')
    'hgcfg.item.sep':      'none',
    # The value of the key, but not the active value (i.e., it is overriden).
    'hgcfg.item.value':    'none',
    # The active value of the key (i.e, not overriden anywhere).
    'hgcfg.item.value.selected':    'bold',

    # The key name printed with `hg config SECTION.KEY --verbose`.
    'hgcfg.keyname':       'bold',
}

testedwith = '2.7.1'

