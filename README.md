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
* thread/history command
* command aliases
* tab completion for commands
* hashbang, modules
* remove background colors because ugghhh (light fontcolor + light bkgrnd color = unreadable)
* remove localIDs on toots (`https:// + yourinstance + /@username/ + rawID` = actual webpage)

----

#### Inspired by Rainbowstream
https://github.com/DTVD/rainbowstream
