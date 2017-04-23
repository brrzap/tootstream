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

#### experimental features

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

#### rationale

The original project's REPL leaves argument processing to individual commands.  This experimental
branch set out to see if the Click library could be put to work for that task.  Working on features 
(subcommands, options) is much more fun than tokenizing a commandline from scratch.

It also serves as a playground for architectural changes (modules etc) that may be of interest
to the project.  (It may only serve as a proof-of-bad-idea, but that can be interesting too.)

----

#### Inspired by Rainbowstream
https://github.com/DTVD/rainbowstream
