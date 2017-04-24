import os
import click
import configparser
from mastodon import Mastodon
from colored import fg, attr, stylize
from .toot_print import *


RESERVED = ( "theme", "global" )
KEYCFGFILE = __name__ + 'cfgfile'
KEYCONFIG = __name__ + 'config'
KEYPROFILE = __name__ + 'profile'
KEYPROMPT = __name__ + 'prompt'
KEYMASTODON = __name__ + 'mastodon'
KEYSHELL = __name__ + 'shell'


def set_configfile(filename):
    click.get_current_context().meta[KEYCFGFILE] = filename
    return


def get_configfile():
    return click.get_current_context().meta.get(KEYCFGFILE)


def set_prompt(prompt):
    ctx = click.get_current_context()
    ctx.meta[KEYPROMPT] = prompt
    ctx.meta[KEYSHELL].prompt = prompt
    return


def set_shell(shell):
    click.get_current_context().meta[KEYSHELL] = shell
    return


def get_prompt():
    return click.get_current_context().meta.get(KEYPROMPT)


def set_config(config):
    click.get_current_context().meta[KEYCONFIG] = config
    return


def get_config():
    return click.get_current_context().meta[KEYCONFIG]


def set_active_profile(profile):
    click.get_current_context().meta[KEYPROFILE] = profile
    return


def get_active_profile():
    return click.get_current_context().meta.get(KEYPROFILE)


def set_active_mastodon(mastodon):
    click.get_current_context().meta[KEYMASTODON] = mastodon
    return


def get_active_mastodon():
    return click.get_current_context().meta.get(KEYMASTODON)


def get_profile_values(profile):
    # quick return of existing profile, watch out for exceptions
    cfg = get_config()
    p = cfg[profile]
    return p['instance'], p['client_id'], p['client_secret'], p['token']


def get_known_profiles():
    cfg = get_config()
    return list( set(cfg.sections()) - set(RESERVED) )


def get_userid(username):
    # we got some user input.  we need a userid (int).
    # returns userid as int, -1 on error, or list of users if ambiguous.
    if not username:
        return -1

    # maybe it's already an int
    try:
        return int(username)
    except ValueError:
        pass

    # not an int
    mastodon = get_active_mastodon()
    users = mastodon.account_search(username)
    if not users:
        return -1
    elif len(users) > 1:
        return users
    else:
        return users[0]['id']


def parse_config():
    filename = get_configfile()
    (dirpath, basename) = os.path.split(filename)
    if not (dirpath == "" or os.path.exists(dirpath)):
        os.makedirs(dirpath)

    if not os.path.isfile(filename):
        cprint("...No configuration found, generating...", fg('cyan'))
        cfg = configparser.ConfigParser()
        set_config(cfg)
        return cfg

    cfg = configparser.ConfigParser()
    try:
        cfg.read(filename)
    except configparser.Error:
        cprint("This does not look like a valid configuration:"+filename, fg('red'))
        sys.exit("Goodbye!")

    set_config(cfg)
    return cfg
# parse_config


def save_config():
    filename = get_configfile()
    (dirpath, basename) = os.path.split(filename)
    if not (dirpath == "" or os.path.exists(dirpath)):
        os.makedirs(dirpath)

    cfg = get_config()
    try:
        with open(filename, 'w') as configfile:
            cfg.write(configfile)
    except os.error:
        cprint("Unable to write configuration to "+filename, fg('red'))
# save_config


__all__ = [ 'set_configfile', 'get_configfile',
            'set_config', 'get_config',
            'set_prompt', 'get_prompt',
            'set_active_profile', 'get_active_profile',
            'set_active_mastodon', 'get_active_mastodon',
            'set_shell',
            'get_profile_values',
            'get_known_profiles',
            'get_userid',
            'parse_config',
            'save_config' ]

#from .toot_print import *
