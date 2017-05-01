# tootstream (*experimental*)
A command line interface for interacting with Mastodon instances written in python.

tootstream currently does not support 2FA.

This branch has been heavily modified.  You can find the original at
[magicalraccoon/tootstream](https://github.com/magicalraccoon/tootstream).
Please report problems with this branch here and not on the upstream repo.

## Using tootstream

1. Clone this repo.
2. Initialize a virtual environment.
3. Activate and install dependencies.
4. Run the script.

```
$ git clone --branch experimental --single-branch https://github.com/brrzap/tootstream.git tootstream-experimental
$ cd tootstream-experimental
$ virtualenv -p python3 .
$ source ./bin/activate
$ python3 setup.py install
$ ./tootstream.py
```

##### Close with: `$ deactivate`

----

### experimental features

* popup desktop notifications (`-n`) (**requires external dependencies**)
* multiple accounts via profiles
* follow/block/mute list management commands
* tag/username search commands
* list favourites, user timelines
* thread/history command
* toot/reply with media attachments, spoiler text, visibility settings
* colored prompt
* command aliases
* tab completion for commands
* hashbang, modules
* remove background colors because ugghhh (light fontcolor + light bkgrnd color = unreadable)
* remove localIDs on toots (`https:// + yourinstance + /@username/ + rawID` = actual webpage)

##### Desktop Notifications dependencies:

This feature requires the `notify-send` program.  See
Archwiki's [Desktop notifications](https://wiki.archlinux.org/index.php/Desktop_notifications) page for more details.

* Debian/Ubuntu: install `libnotify-bin`
* Fedora, Arch: install `libnotify`
* Windows: try [notify-send for Windows](http://vaskovsky.net/notify-send/).

There is experimental support for native Python packages instead of `notify-send`:

* GObject-Introspection's Notify:  install via your system package manager (`python-gobject`, probably) and
remove the file `[venvroot]/lib/python3.6/no-global-site-packages.txt` so your virtual environment can find it.
* Notify2: `pip install notify2`.  This depends on `dbus-python` which may need `pip3 install dbus-python` to
install properly.

----

### rationale

The original project's REPL leaves argument processing to individual commands.  This experimental
branch set out to see if the Click library could be put to work for that task.  Working on features 
(subcommands, options) is much more fun than tokenizing a commandline from scratch.

It also serves as a playground for architectural changes (modules etc) that may be of interest
to the project.  (It may only serve as a proof-of-bad-idea, but that can be interesting too.)

----

#### Inspired by Rainbowstream
https://github.com/DTVD/rainbowstream
