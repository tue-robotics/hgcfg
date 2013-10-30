# hgcfg extension for mercurial

## Overview

This extension provides command-line access to hg configuration values stored
in hgrc files. You can use this extension to view and change configuration
values, show which configuration files are used by hg, and edit any of these
files from the command-line.

Three commands are provided by this extension:

* `hg listcfgs`
* `hg editcfg`
* `hg cfg`

## Examples

### Check how a configuration key is being set

    :::console
    $ hg cfg ui.username --verbose

Results:

    :::console
    values found for ui.username in global/local/user config:
      bmearns   (user)   C:\Users\bmearns\mercurial.ini
    * metalark  (local)  C:\Users\bmearns\.hgext\hgconfig\.hg\hgrc

### Change a configuration key in the local (repo) config file

    :::console
    $ hg cfg ui.username "kingcobra"

Results:

    :::console
    $ hg cfg ui.username --verbose
    values found for ui.username in global/local/user config:
      bmearns    (user)   C:\Users\bmearns\mercurial.ini
    * kingcobra  (local)  C:\Users\bmearns\.hgext\hgconfig\.hg\hgrc

### Edit user config file

    :::console
    $h g editcfg --user
    multiple config files to choose from, please select:
    [0] C:\Users\bmearns\.hgrc
    [1] C:\Users\bmearns\mercurial.ini
    which file do you want to edit: [0] 1
    editing config file [1]

Uses configured editor to edit the specified file, by way of a temp file, like commit messages.

### List available config files

    :::console
    $ hg listcfgs
     ro globalC:\Program Files\TortoiseHg\hgrc.d\EditorTools.rc
     ro globalC:\Program Files\TortoiseHg\hgrc.d\Mercurial.rc
     ro globalC:\Program Files\TortoiseHg\hgrc.d\MergePatterns.rc
     ro globalC:\Program Files\TortoiseHg\hgrc.d\MergeTools.rc
     rw globalC:\Program Files\TortoiseHg\hgrc.d\Paths.rc
     ro globalC:\Program Files\TortoiseHg\hgrc.d\TerminalTools.rc
     rw user  C:\Users\bmearns\mercurial.ini
     !  user  C:\Users\bmearns\.hgrc
     rw local C:\Users\bmearns\.hgext\hgconfig\.hg\hgrc

A `!` indicates the file is not present, `ro` indicates the file is not writeable by the current user, `rw` indicates that it is writeable.


