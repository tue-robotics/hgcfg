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
# The version of the extension you're currently viewing is another fork by
# tue-robotics. It continues on the version of Brian Mearns
# <https://bitbucket.org/bmearns/hgcfg>. Which incorporates the changes
# made by Risto Kankkunen up through 2 Dec 2012, revision 6526e84,
# as well as a number of other changes.
#
# This version of the extension is named "hgcfg" and is hosted at
# <https://github.com/tue-robotics/hgcfg>.
#
"""
hgcfg

Displays or modifies local, user, and global configuration.
"""

import re
import os.path
import sys

from mercurial import util, cmdutil
from mercurial.config import config as config_file
from mercurial.i18n import _

sys.path.append(os.path.dirname(__file__))
from deprecate import replace_deprecated, deprecated

if util.version() >= b'4.2':
    from mercurial import rcutil
    rcpath = rcutil.rccomponents
    userrcpath = rcutil.userrcpath
elif util.version() >= b'1.9':
    from mercurial.scmutil import rcpath, userrcpath
else:
    rcpath = util.rcpath
    userrcpath = util.userrcpath

if util.version() >= b'4.7':
    from mercurial.registrar import command
else:
    from mercurial.cmdutil import command


VERSION = [1, 0, 2, 0, b'']


cmdtable = {}
command = command(cmdtable)


def localrc(repo=None):
    """
    Return the filesystem path to the repository's hgrc config file
    as a `str`, or `None` if the given `repo` is None.
    """
    if repo is None:
        return None
    return os.path.join(repo.path, b'hgrc')


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
    # From 4.2 rcpath(rcutil.rccomponents) returns a tuple
    # Not checking here on isinstance, If return type changes, this will probably break instead of silently ignoring
    # this and treating the output as a string like before 4.2.
    if util.version() >= b'4.2':
        allconfigs = [c[1] for c in allconfigs if c[0] == b'path']
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
            scope = b'local'
        elif f in userconfigs:
            scope = b'user'
        else:
            scope = b'global'
        if not os.path.exists(f):
            exists = False
            writeable = False
        else:
            exists = True
            if os.access(f, os.W_OK):
                writeable = True
            else:
                writeable = False
        configs.append({b'scope': scope, b'path': f, b'exists': exists,
                        b'writeable': writeable})

    return configs


@replace_deprecated("listconfigs")  # Don't use bytestring
@command(b"listcfgs",
         [],
         b"",
         optionalrepo=True)
def listcfgs(ui, repo, **opts):
    """list all config files searched for and used by hg

    This command lists all the configuration files searched for by hg in
    order.  Each file name is preceeded by a status indicator: The status
    is '!' if the configuration file is missing. If the file is writable
    by the current user the status is 'rw', otherwise 'ro'.
    """

    configs = getconfigs(ui, repo)

    for c in configs:
        label = b"hgcfg.file." + c[b'scope']

        if not c[b'exists']:
            status_str = b'! '
            label += b".missing"
        elif c[b'writeable']:
            status_str = b'rw'
            label += b".writeable"
        else:
            status_str = b'ro'
            label += b".readonly"

        ui.status(_(b" %s %-6s " % (status_str, c[b'scope'])), label=label)
        ui.write(c[b'path'], label=label)
        ui.write(_(b"\n"))


def showvalue(ui, repo, section, key, scopes, **opts):
    """
    Shows values for specified configuration keys, or lists all
    keys and there values in the specified section, or lists all sections
    in the specified scope.
    """

    # Get a list of config files which exist and are in scope.
    configs = [c for c in getconfigs(ui, repo) if c[b'scope'] in scopes and c[b'exists']]

    def confs():
        for c in configs:
            conf = config_file()
            conf.read(c[b'path'])
            yield c, conf

    # If it's quiet, then we aren't indicating which file it came from,
    # so we may as well make it a unique list.
    if ui.quiet and section is None:
        sections = set()
        for c, conf in confs():
            sections.update(conf.sections())
        for s in sorted(sections):
            uiwritesection(ui, s)
        return

    # Similar, but if it's not quiet, then we indicate which file each
    # section comes from, and don't make it unique.
    if section is None:
        for c, conf in confs():
            uiwritescope(ui, c, ui.status)
            uiwritefile(ui, c, ui.status)
            for s in conf.sections():
                uiwritesection(ui, s)
            ui.status(b'\n')
        return

    # List all unique items in the named section
    if ui.quiet and key is None:
        items = dict()
        for c, conf in confs():
            items.update(conf.items(section))
        uiwritesection(ui, section)

        actvals = {}
        for k, v in sorted(items.iteritems()):
            key = b"%s.%s" % (section.replace(b".", b".."),
                              k.replace(b".", b".."))
            if key not in actvals:
                actvals[key] = ui.config(section, k)
            uiwriteitem(ui, k, v, c, active=(v == actvals[key]))
        ui.write(b'\n')
        return

    # Same, but if not quiet, don't make it unique.
    if key is None:
        actvals = {}
        for c, conf in confs():
            if section in conf:
                uiwritescope(ui, c, ui.status)
                uiwritefile(ui, c, ui.status)
                uiwritesection(ui, section, c)
                for k, v in conf.items(section):
                    key = b"%s.%s" % (section.replace(b".", b".."),
                                      k.replace(b".", b".."))
                    if key not in actvals:
                        actvals[key] = ui.config(section, k)
                    uiwriteitem(ui, k, v, c, active=(v == actvals[key]))
                ui.status(b'\n')
        return

    # They specified both a section and a key, so find all values of it.
    output = []
    max_value_len = 0
    for c in configs:
        value = getvalue(ui, section, key, c[b'path'])
        if value is not None:
            output.append({b'p': c[b'path'], b'v': value, b's': c[b'scope']})
            max_value_len = max([max_value_len, len(value)])

    maxscopelen = 0
    i18nscopes = {}
    for scope in scopes:
        s = _(scope)
        i18nscopes[scope] = s
        maxscopelen = max([maxscopelen, len(s)])

    actualval = ui.config(section, key)
    actualfound = False

    scope_str = b" in %s config" % b'/'.join(scopes)
    if len(output) > 0:
        ui.note(_(b'values found for '))
        ui.note(b'%s.%s' % (section, key), label=b'hgcfg.keyname')
        ui.note(_(scope_str + b":\n"))
        for o in output:

            # Fore --quiet, only show the correct value.
            if o[b'v'] == actualval:
                selected = b'.selected'
                write = ui.write
                prefix = b'* '
                actualfound = True
            else:
                selected = b''
                write = ui.status
                prefix = b'  '
            label = b'hgcfg.item.value' + selected
            write(prefix, label=label)
            write(o[b'v'], label=label)

            # Fill space before writing the scope and path.
            ui.note(b'%*s' % (max_value_len - len(o[b'v']) + 2, b''))

            # Write the scope and path
            scope = i18nscopes[o[b's']]
            ui.note(_(b'('))
            ui.note(scope, label=b'hgcfg.scope.' + o[b's'])
            ui.note(_(b')'))
            ui.note(b'%*s' % (maxscopelen - len(scope) + 1, b''))
            ui.note(o[b'p'], label=b'hgcfg.file.' + o[b's'])

            write(b"\n")

        if not actualfound:
            ui.note(_(b"\ncurrent active value not in scope ("))
            ui.note(str(actualval), label=b'hgcfg.item.value.selected')
            ui.note(_(b")\n"))
    else:
        ui.note(_(b'no values found for '))
        ui.note(b'%s.%s' % (section, key), label=b'hgcfg.keyname')
        ui.note(_(scope_str + b":\n"))


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
    with open(rcfile, 'rb') as f:
        for line in f:
            m = re.match(br"^\s*\[(.*)\]", line)
            if m:
                inside_section = section == m.group(1)
            else:
                if inside_section:
                    m = re.match(br"\s*" + re.escape(key) + br"\s*=(.*)", line)
                    if m:
                        values.append(m.group(1).strip())
    return values


def getconfigchoice(ui, configs, start_msg, prompt_msg, default=0):
    """
    Ask the user which of the given configs they want to act on.
    The `configs` parameter should come from `getconfigs` or similar.
    """
    i = 0
    ui.status(start_msg)
    for c in configs:
        ui.status(_(b"[%d] " % i))
        ui.status(c[b'path'], label=b'hgcfg.file.' + c[b'scope'])
        ui.status(_(b"\n"))
        i += 1

    choice = ui.prompt(prompt_msg + _(b": [%s]" % (bytes(default))),
                       default=bytes(default))

    try:
        choice = int(choice)
    except ValueError:
        return False

    if choice < 0 or choice > (len(configs) - 1):
        return False
    else:
        return choice


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
        if c[b'scope'] not in scopes:
            continue
        if not c[b'writeable'] and not c[b'scope'] == b'local':
            continue
        writeable_configs.append(c)
    return writeable_configs


def writevalue(ui, repo, section, key, value, scopes):

    # may have a choice of files to edit from, start from bottom
    writeable_configs = getwriteableconfigs(ui, repo, scopes)
    if len(writeable_configs) < 1:
        ui.warn(_(b"no writeable configs to write value to, "
                  b"try 'hg listconfigs'\n"))
        return False

    if len(writeable_configs) == 1:
        return writevaluetofile(ui, repo, section, key, value,
                                writeable_configs[0][b'path'])
    else:
        # give them a choice
        choice = getconfigchoice(ui, writeable_configs,
                                 _(b"multiple config files to choose from, please select:\n"),
                                 _(b"which file do you want to write to"))
        if choice is False:
            ui.warn(_(b"invalid choice\n"))
            return False
        else:
            ui.status(_(b"writing value to config [%d]\n" % choice))
            return writevaluetofile(ui, repo, section, key, value,
                                    writeable_configs[int(choice)][b'path'])


def writevaluetofile_(ui, repo, section, key, value, rcfile, delete):
    """
    Updates the given config file to assign the specified value to the specified
    key. If the key already exists in the file, then it is either overwritten
    (if `delete` is True), or it is commented out and the new value is written
    before it.
    """

    inside_section = False
    wrote_value = False
    new = b''

    with open(rcfile, 'rb') as f:
        for line in f:
            m = re.match(br"^\s*\[(.*)\]", line)
            if m:
                if section == m.group(1):
                    inside_section = True
                    new += line
                    if not wrote_value and value is not None:
                        new += (b"%s = %s\n" % (key, value))
                        wrote_value = True
                else:
                    inside_section = False
                    new += line
            else:
                if inside_section:
                    m = re.match(br"\s*" + re.escape(key) + br"\s*=(.*)", line)
                    if m:
                        if not delete:
                            new += b';' + line
                    else:
                        new += line
                else:
                    new += line

    # if we haven't written the value yet it's because we never found the
    # right section, so we'll make it now
    if not wrote_value and value is not None:
        new += b"\n[%s]\n%s = %s\n" % (section, key, value)

    # write new file
    with open(rcfile, 'wb') as f:
        f.write(new)
    return True


def writevaluetofile(ui, repo, section, key, value, rcfile):
    """
    Simple delegte to `writevaluetofile_`, but gets the `delete` parameter from
    the `hgcfg.delete_on_replace` configuration value.
    """
    delete = ui.configbool(b"hgcfg", b"delete_on_replace", None)
    if delete is None:
        delete = ui.configbool(b"config", b"delete_on_replace", False)
    return writevaluetofile_(ui, repo, section, key, value, rcfile, delete)


def editconfigfile(ui, rc_file):
    """
    Allows the user to edit the specified config file. This uses the
    `ui.edit` function, similar to the one used for editing commit
    messages.
    """
    with open(rc_file, 'rb') as f:
        orig_contents = f.read()

    banner = _(b"#HG: editing hg config file: ") + rc_file + _(b"\n\n")
    contents = banner + orig_contents
    new_contents = ui.edit(contents, ui.username())
    new_contents = re.sub(br'^%s' % re.escape(banner), b'', new_contents)

    if new_contents != orig_contents:
        with open(rc_file, 'wb') as f:
            f.write(new_contents)


@replace_deprecated("editconfig")  # Don't use bytestring
@command(b"editcfg",
         [(b'l', b'local', None, b'edit local config file (default)'),
          (b'u', b'user', None, b'edit per-user config file(s)'),
          (b'g', b'global', None, b'edit global config file(s)')],
         b"[options]",
         optionalrepo=True)
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
    if opts['local']:  # Don't use bytestring
        scopes.add(b'local')
    if opts['user']:  # Don't use bytestring
        scopes.add(b'user')
    if opts['global']:  # Don't use bytestring
        scopes.add(b'global')
    if not scopes:
        scopes.add(b'local')

    writeable_configs = getwriteableconfigs(ui, repo, scopes)
    if len(writeable_configs) < 1:
        ui.warn(_(b"no writeable configs to write value to, "
                  b"try 'hg listconfigs'\n"))
        return False

    if len(writeable_configs) == 1:
        return editconfigfile(ui, writeable_configs[0][b'path'])
    else:
        # give them a choice
        choice = getconfigchoice(ui, writeable_configs,
            _(b"multiple config files to choose from, please select:\n"),
            _(b"which file do you want to edit"))
        if choice is False:
            ui.warn(b"invalid choice\n")
            return False
        else:
            ui.status(_(b"editing config file [%d]\n") % choice)
            return editconfigfile(ui, writeable_configs[int(choice)][b'path'])


@replace_deprecated('config')  # Don't use bytestring
@command(b"cfg",
         [(b'd', b'delete', None, b'delete SECTION.KEY'),
          (b'l', b'local', None, b'use local config file (default for set)'),
          (b'u', b'user', None, b'use per-user config file(s)'),
          (b'g', b'global', None, b'use global config file(s)')],
         b"[options] [SECTION[.KEY [NEW_VALUE]]]",
         optionalrepo=True)
def cfg(ui, repo, key=b'', value=None, **opts):
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
    pattern = br"(?:([a-z_][a-z0-9_-]*)(?:\.([a-z_][a-z0-9._-]*))?)?$"
    m = re.match(pattern, key, re.I)
    if not m:
        ui.warn(_(b"invalid key syntax. try SECTION.KEY\n"))
        return
    section = m.group(1)
    key = m.group(2)

    if opts['delete']:  # Don't use bytestring
        if value is not None:
            ui.warn(_(b'must not specify NEW_VALUE with --delete option'))
            return
        if not section or not key:
            ui.warn(_(b'must specify SECTION.KEY with --delete option'))
            return

    default_get_scopes = {b'local', b'user', b'global'}
    default_set_scopes = {b'local'}
    scopes = set()
    if opts['local']:  # Don't use bytestring
        scopes.add(b'local')
    if opts['user']:  # Don't use bytestring
        scopes.add(b'user')
    if opts['global']:  # Don't use bytestring
        scopes.add(b'global')

    # no value given, we will show them the value
    if value is None and not opts['delete']:  # Don't use bytestring
        showvalue(ui, repo, section, key, scopes or default_get_scopes)
    # try to set a value
    else:
        # for these values, I think it's best to default to local config
        writevalue(ui, repo, section, key, value, scopes or default_set_scopes)
    # FIXME: --delete is not used.
    return


# Some utility functions for writing to the UI

def uiwritescope(ui, config, func=None):
    if func is None:
        func = ui.write
    func(_(b'scope=') + (b'%s' % config[b'scope']), label=b'hgcfg.scope.' + config[b'scope'])
    func(_(b'\n'))


def uiwritefile(ui, config, func=None):
    if func is None:
        func = ui.write
    func(_(b'file=') + (b'%s' % config[b'path']), label=b'hgcfg.file.' + config[b'scope'])
    func(_(b'\n'))


def uiwritesection(ui, section, config=None, func=None):
    if func is None:
        func = ui.write
    func(b'[%s]' % section, label=b'hgcfg.section')
    func(_(b'\n'))


def uiwriteitem(ui, k, v, config=None, func=None, active=False):
    if func is None:
        func = ui.write
    if active:
        prefix = _(b'    * ')
        selected = b".selected"
    else:
        prefix = _(b'      ')
        selected = b""
    func(prefix + k, label=b"hgcfg.item.key")
    func(_(b' = '), label=b"hgcfg.item.sep")
    func(v, label=b"hgcfg.item.value" + selected)
    func(b'\n')


# Extensions Stuff

# Add the deprecated command aliases.
for name in [b"", b"edit", b"list"]:
    tail = b"cfg"
    otail = b"config"
    key = name + tail
    if key not in cmdtable:
        tail += b"s"
        otail += b"s"
        key = name + tail

    cmddef = list(cmdtable[key])
    cmddef[0] = getattr(sys.modules[__name__], (name + otail).decode('ascii'))
    cmdtable[name + otail] = tuple(cmddef)

# colors
colortable = {
    # A section name, like [paths] or [ui].
    b'hgcfg.section': b'cyan',

    # Paths to config files.

    # Files with global scope.
    # In `hg config [SECTION[.KEY]]`
    b'hgcfg.file.global': b'red',
    # In `hg listconfig`
    b'hgcfg.file.global.missing': b'red ',
    b'hgcfg.file.global.writeable': b'red bold',
    b'hgcfg.file.global.readonly': b'red ',

    # Files with user scope.
    b'hgcfg.file.user': b'yellow',
    b'hgcfg.file.user.missing': b'yellow ',
    b'hgcfg.file.user.writeable': b'yellow bold',
    b'hgcfg.file.user.readonly': b'yellow ',

    # Files with local scope.
    b'hgcfg.file.local': b'green',
    b'hgcfg.file.local.missing': b'green ',
    b'hgcfg.file.local.writeable': b'green bold',
    b'hgcfg.file.local.readonly': b'green ',

    # Scope of a file or value.
    b'hgcfg.scope.global': b'red bold',
    b'hgcfg.scope.user': b'yellow bold',
    b'hgcfg.scope.local': b'green bold',

    # A key and it's value
    # The name of the key
    b'hgcfg.item.key': b'none',
    # Whatever comes between the name and the value (e.g., '=')
    b'hgcfg.item.sep': b'none',
    # The value of the key, but not the active value (i.e., it is overridden).
    b'hgcfg.item.value': b'none',
    # The active value of the key (i.e, not overridden anywhere).
    b'hgcfg.item.value.selected': b'bold',

    # The key name printed with `hg config SECTION.KEY --verbose`.
    b'hgcfg.keyname': b'bold'
}

testedwith = b'5.3.2'
