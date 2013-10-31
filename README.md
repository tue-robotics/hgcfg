# hgcfg extension for mercurial

Displays or modifies local, user, and global configuration.

## Contents

* [Overview](#markdown-header-overview)
* [Examples](#markdown-header-examples)
* [Installation](#markdown-header-installation)
* [Screen Shots](#markdown-header-screen-shots)
* [Similar Extensions](#markdown-header-similar-extensions)
* [See Also](#markdown-header-see-also)
* [Recent activity](#repo-activity)

## Overview

This extension provides command-line access to hg configuration values stored
in hgrc files. You can use this extension to view and change configuration
values, show which configuration files are used by hg, and edit any of these
files from the command-line.

Three commands are provided by this extension:

* `hg listcfgs`
* `hg editcfg`
* `hg cfg`

### Features

* Set or query config values in local, user, or global hg config files
* List all items in a given config section
* List all config files for a repository
* Launch `EDITOR` to edit local, user, or global config file
* Delete or comment-out old values when overwriting
* Colorized when `color` extension is enabled
* Backwards compatible with "alu"'s
  [`hgconfig`](https://bitbucket.org/alu/hgconfig) extension (through rev
  [80f98d6](https://bitbucket.org/alu/hgconfig/commits/80f98d6d3386f8c51d7a89a3a53f4ae9fd4db8a8))

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

## Installation

To install this extension, download the files in the [hgext](https://bitbucket.org/bmearns/hgcfg/src/tip/hgext) directory to your system
and edit your hgrc config file to add the `hgcfg.py` file as an extension:

    :::cfg
    [extensions]
    hgcfg = /path/to/hgcfg/hgext/hgcfg.py

You can just as well clone the entire [hgext repository][https://bitbucket.org/bmearns/hgcfg] and use it the same way, just make sure to point
the extension at `hgcfg.py`.

It doesn't matter where you place the files, but a common place to put them is under `~/.hgext` (on Windows, this would be
`%HOMEDRIVE%%HOMEPATH%\.hgext`, typically `C:\Users\USERNAME\.hgext` in Windows 7).


## Screen Shots

The following shows the results of issuing the `hg listcfgs` command in conjunction with the built-in `color` extension.

![hg listcfgs](https://bytebucket.org/bmearns/hgcfg/wiki/res/ss_listcfgs.png "Output of 'hg listcfgs' command")

For more screen shots, see [ScreenShots](https://bitbucket.org/bmearns/hgcfg/wiki/ScreenShots).

For information on customizing the colors used by the extension, see [Config#Colors](https://bitbucket.org/bmearns/hgcfg/wiki/Config#markdown-header-colors).

## Similar Extensions

This extension was originally forked from the [`hgconfig`](http://mercurial.selenic.com/wiki/ConfigExtensionCommandLine)
extension (frequently just called "config") by BitBucket user "[alu](https://bitbucket.org/alu)".
Most of the core functionality comes from that extension, but some additional features have been added.
The `hgcfg` extension retains backwards compatibility with the alu's `hgconfig` extension, so you can
seamlessly replace that extension with this one.

There is also another but developmentally unrelated extension called
[`config`](http://mercurial.selenic.com/wiki/ConfigExtension),
by [Steve Borho](https://bitbucket.org/sborho) which serves many of the same purposes.
However, this extension hasn't been active since 2007 and is marked on its wiki page as "defunct".

## See Also

* [Wiki](https://bitbucket.org/bmearns/hgcfg/wiki/) - Extension's public wiki on BitBucket
* [HG Extension Page](http://mercurial.selenic.com/wiki/HgcfgExtension) - Extensions' page on mercurial wiki
* [Config](https://bitbucket.org/bmearns/hgcfg/wiki/Config) - Configuration keys
* [ScreenShots](https://bitbucket.org/bmearns/hgcfg/wiki/ScreenShots) - More screen shots

