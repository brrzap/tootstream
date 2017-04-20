#!/usr/bin/env python3

import os.path
import click
import getpass
import sys
import re
import configparser
import random
import readline
from tootstream import *
from tootstream.toot_click import CONTEXT_SETTINGS
from tootstream.toot_utils import *
from tootstream.toot_print import *
#from tootstream.toot_print import cprint, print_profiles
#from tootstream import TootParser, TootIdDict, TootStreamCmd, TootStreamGroup, TootStreamCmdCollection
from click_shell import make_click_shell
from mastodon import Mastodon
from colored import fg, attr, stylize

#COLORS = ['red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']
#IDS = TootIdDict();


#####################################
######## UTILITY FUNCTIONS # ########
#####################################
# see also tootstream.toot_util module

def register_app(instance):
    return Mastodon.create_app( 'tootstream',
                                api_base_url="https://" + instance )


def login(instance, email, password):
    """
    Login to a Mastodon instance.
    Return a Mastodon client if login success, otherwise returns None.
    """
    mastodon = get_active_mastodon()
    return mastodon.log_in(email, password)


def parse_or_input_profile(profile, instance=None, email=None, password=None):
    """
    Validate an existing profile or get user input to generate a new one.
    """
    cfg = get_config()
    # shortcut for preexisting profiles
    if cfg.has_section(profile):
        try:
            return get_profile_values(profile)
        except:
            pass
    else:
        cfg.add_section(profile)

    # no existing profile or it's incomplete
    if (instance != None):
        # Nothing to do, just use value passed on the command line
        pass
    elif "instance" in cfg[profile]:
        instance = cfg[profile]['instance']
    else:
        cprint("  Which instance would you like to connect to? eg: 'mastodon.social'", fg('blue'))
        instance = input("  Instance: ")


    client_id = None
    if "client_id" in cfg[profile]:
        client_id = cfg[profile]['client_id']

    client_secret = None
    if "client_secret" in cfg[profile]:
        client_secret = cfg[profile]['client_secret']

    if (client_id == None or client_secret == None):
        client_id, client_secret = register_app(instance)

    token = None
    if "token" in cfg[profile]:
        token = cfg[profile]['token']

    if (token == None or email != None or password != None):
        if (email == None):
            email = input("  Email used to login: ")
        if (password == None):
            password = getpass.getpass("  Password: ")

        # temporary object to aquire the token
        mastodon = Mastodon(
            client_id=client_id,
            client_secret=client_secret,
            api_base_url="https://" + instance
        )
        token = login(instance, email, password)

    return instance, client_id, client_secret, token


#####################################
######## OUTPUT FORMATTING # ########
#####################################
# see tootstream.toot_print module

#####################################
######## BEGIN COMMAND BLOCK ########
#####################################
#_tootstreamCommands = click.CommandCollection( 'tootstreamCmds', short_help='tootstream commands',
#                                               sources=[],
#                                               context_settings=CONTEXT_SETTINGS,
#                                               invoke_without_command=True,
#                                               options_metavar='',
#                                               subcommand_metavar='<command>' )

@click.group( 'tootstream', short_help='tootstream commands',
              cls=TootStreamGroup,
              context_settings=CONTEXT_SETTINGS,
              invoke_without_command=True,
              options_metavar='',
              subcommand_metavar='<command>' )
def _tootstream():
    """Tootstream commands.

    Commands can be tab-completed. Some readline keybindings are supported.
    Command history is available but not saved between sessions.

    unimplemented: 2FA, CW/NSFW, media attachments, user timelines, favourites list
    """
    pass


@_tootstream.command( 'help', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='get help for a command' )
@click.argument('cmd', metavar='<cmd>', required=False, default=None)
def help(cmd):
    """Get details on how to use a command."""
    ctx = click.get_current_context()
    if not cmd is None:
        c = _tootstream.get_command(ctx, cmd)
        click.echo(c.get_help(ctx))
        return
    click.echo(_tootstream.get_help(ctx))


@_tootstream.command( 'toot', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='post a toot' )
@click.argument('text', nargs=-1, metavar='<text>')
def toot(text):
    """Publish a toot. ex: 'toot Hello World' will publish 'Hello World'."""
    mastodon = get_active_mastodon()
    post_text = ' '.join(text)
    mastodon.toot(post_text)
    cprint("You tooted: ", fg('magenta') + attr('bold'), end="")
    cprint(post_text, fg('magenta') + attr('bold') + attr('underlined'))
# aliases
_tootstream.add_command(toot, 't')


@_tootstream.command( 'reply', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='reply to a toot' )
@click.argument('tootid', metavar='<id>')
@click.argument('text', nargs=-1, metavar='<text>')
def reply(tootid, text):
    """Reply to a toot by ID."""
    mastodon = get_active_mastodon()
    reply_text = ' '.join(text)
    #parent_id = IDS.to_global(tootid)
    parent_id = tootid
    if parent_id is None:
        return print_error("error: invalid ID.")
    parent_toot = mastodon.status(parent_id)
    mentions = [i['acct'] for i in parent_toot['mentions']]
    mentions.append(parent_toot['account']['acct'])
    mentions = ["@%s" % i for i in list(set(mentions))] # Remove dups
    mentions = ' '.join(mentions)
    # TODO: Ensure that content warning visibility carries over to reply
    reply_toot = mastodon.status_post('%s %s' % (mentions, reply_text),
                                      in_reply_to_id=int(parent_id))
    msg = "  Replied with: " + get_content(reply_toot)
    cprint(msg, fg('red'))
# aliases
_tootstream.add_command(reply, 'r')
_tootstream.add_command(reply, 'rep')


@_tootstream.command( 'boost', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='boost a toot' )
@click.argument('tootid', metavar='<id>')
def boost(tootid):
    """Boosts a toot by ID."""
    mastodon = get_active_mastodon()
    #tootid = IDS.to_global(tootid)
    if tootid is None:
        return print_error("error: invalid ID.")
    mastodon.status_reblog(tootid)
    boosted = mastodon.status(tootid)
    msg = "  Boosted: " + get_content(boosted)
    cprint(msg, fg('green'))
# aliases
_tootstream.add_command(boost, 'rt')
_tootstream.add_command(boost, 'retoot')


@_tootstream.command( 'unboost', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='undo a boost' )
@click.argument('tootid', metavar='<id>')
def unboost(tootid):
    """Removes a boosted tweet by ID."""
    mastodon = get_active_mastodon()
    #tootid = IDS.to_global(tootid)
    if tootid is None:
        return print_error("error: invalid ID.")
    mastodon.status_unreblog(tootid)
    unboosted = mastodon.status(tootid)
    msg = "  Removed boost: " + get_content(unboosted)
    cprint(msg, fg('red'))


@_tootstream.command( 'fav', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='favorite a toot' )
@click.argument('tootid', metavar='<id>')
def fav(tootid):
    """Favorites a toot by ID."""
    mastodon = get_active_mastodon()
    #tootid = IDS.to_global(tootid)
    if tootid is None:
        return print_error("error: invalid ID.")
    mastodon.status_favourite(tootid)
    faved = mastodon.status(tootid)
    msg = "  Favorited: " + get_content(faved)
    cprint(msg, fg('red'))
# aliases
_tootstream.add_command(fav, 'star')


@_tootstream.command( 'unfav', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='unfavorite a toot' )
@click.argument('tootid', metavar='<id>')
def unfav(tootid):
    """Removes a favorite toot by ID."""
    mastodon = get_active_mastodon()
    #tootid = IDS.to_global(tootid)
    if tootid is None:
        return print_error("error: invalid ID.")
    mastodon.status_unfavourite(tootid)
    unfaved = mastodon.status(tootid)
    msg = "  Removed favorite: " + get_content(unfaved)
    cprint(msg, fg('yellow'))


@_tootstream.command( 'home', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='show home timeline' )
def home():
    """Displays the Home timeline."""
    mastodon = get_active_mastodon()
    for toot in reversed(mastodon.timeline_home()):
        printTimelineToot(toot)
# aliases
_tootstream.add_command(home, 'h')


@_tootstream.command( 'public', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='show public timeline' )
def public():
    """Displays the Public (federated) timeline."""
    mastodon = get_active_mastodon()
    for toot in reversed(mastodon.timeline_public()):
        printTimelineToot(toot)
# aliases
_tootstream.add_command(public, 'pub')
_tootstream.add_command(public, 'fed')


@_tootstream.command( 'local', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='show local timeline' )
def local():
    """Displays the Local (instance) timeline."""
    mastodon = get_active_mastodon()
    for toot in reversed(mastodon.timeline_local()):
        printTimelineToot(toot)
# aliases
_tootstream.add_command(local, 'l')


@_tootstream.command( 'thread', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='thread history of a toot' )
@click.argument('tootid', metavar='<id>')
def thread(tootid):
    """Displays the thread this toot is part of, ex: 'thread 7'"""
    mastodon = get_active_mastodon()
    #tootid = IDS.to_global(tootid)
    if tootid is None:
        return print_error("error: invalid ID.")
    dicts = mastodon.status_context(tootid)

    # No history
    if ((len(dicts['ancestors']) == 0) and (len(dicts['descendants']) == 0)):
        cprint("  No history to show.", fg('blue'))
        return

    # Print older toots
    if (len(dicts['ancestors']) > 0):
        cprint("  =========   " + "↓↓↓↓↓↓ Older Toots Begin ↓↓↓↓↓↓" + "   ========", fg('red'))
        for oldToot in dicts['ancestors']:
            printHistoryToot(oldToot)
        cprint("  =========   " + "↑↑↑↑↑↑ Older Toots End ↑↑↑↑↑↑" + "   ========", fg('red'))

    # Print current toot
    currentToot = mastodon.status(tootid)
    display_name = "  " + currentToot['account']['display_name']
    username = " @" + currentToot['account']['username'] + " "
    reblogs_count = "  ♺:" + str(currentToot['reblogs_count'])
    favourites_count = " ♥:" + str(currentToot['favourites_count']) + " "
    #toot_id = str(IDS.to_local(currentToot['id']))
    toot_id = str(currentToot['id'])
    cprint(display_name, fg('blue'), end="")
    cprint(username + currentToot['created_at'], fg('blue'))
    cprint(reblogs_count + favourites_count, fg('blue'), end="")
    cprint(toot_id, fg('blue'))
    cprint(get_content(currentToot), fg('blue'), end="\n")

    # Print newer toots
    if (len(dicts['descendants']) > 0):
        cprint("  =========   " + "↓↓↓↓↓↓ Newer Toots Begin ↓↓↓↓↓↓" + "   ========", fg('green'))
        for newToot in dicts['descendants']:
            printHistoryToot(newToot)
        cprint("  =========   " + "↑↑↑↑↑↑ Newer Toots End ↑↑↑↑↑↑" + "   ========", fg('green'))
# aliases
_tootstream.add_command(thread, 'history')
_tootstream.add_command(thread, 'detail')


@_tootstream.command( 'note', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='show notification timeline' )
def note():
    """Displays the Notifications timeline."""
    mastodon = get_active_mastodon()
    for note in reversed(mastodon.notifications()):
        display_name = "  " + note['account']['display_name']
        username = " @" + note['account']['username']

        # Mentions
        if note['type'] == 'mention':
            cprint(display_name + username + " mentioned you =================", fg('magenta'))
            printTimelineToot(note['status'])

        # Favorites
        elif note['type'] == 'favourite':
            reblogs_count = "  " + "♺:" + str(note['status']['reblogs_count'])
            favourites_count = " ♥:" + str(note['status']['favourites_count'])
            time = " " + note['status']['created_at']
            content = get_content(note['status'])
            cprint(display_name + username + " favorited your status:", fg('green'))
            cprint(reblogs_count + favourites_count + time + '\n' + content, fg('green'))

        # Boosts
        elif note['type'] == 'reblog':
            cprint(display_name + username + " boosted your status:", fg('yellow'))
            cprint(get_content(note['status']), fg('yellow'))

        # Follows
        elif note['type'] == 'follow':
            username = re.sub('<[^<]+?>', '', username)
            display_name = note['account']['display_name']
            print("  ", end="")
            cprint(display_name + username + " followed you!", fg('red'))

        # blank line
        print('')
# aliases
_tootstream.add_command(note, 'n')


@_tootstream.command( 'whois', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='search for a user' )
@click.argument('username', metavar='<user>')
def whois(username):
    """Search for a user."""
    mastodon = get_active_mastodon()
    users = mastodon.account_search(username)

    for user in users:
        printUser(user)
# aliases
_tootstream.add_command(whois, 'who')


@_tootstream.command( 'whatis', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='search for a hashtag' )
@click.argument('tag', metavar='<tag>')
def whatis(tag):
    """Search for a hashtag."""
    mastodon = get_active_mastodon()
    for toot in reversed(mastodon.timeline_hashtag(tag)):
        printTimelineToot(toot, mastodon)
# aliases
_tootstream.add_command(whatis, 'what')


@_tootstream.command( 'search', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='search #tag|@user' )
@click.argument('query', metavar='<query>')
def search(query):
    """Search for a #tag or @user."""
    mastodon = get_active_mastodon()
    usage = str( "  usage: search #tagname\n" +
                 "         search @username" )
    try:
        indicator = query[:1]
        query = query[1:]
    except:
        cprint(usage, fg('red'))
        return

    # @ user search
    if indicator == "@" and not query == "":
        click.get_current_context().invoke(whois, username=query)
    # end @

    # # hashtag search
    elif indicator == "#" and not query == "":
        click.get_current_context().invoke(whatis, tag=query)
    # end #

    else:
        # FIXME: should do mastodon.content_search() here
        cprint("  Invalid format.\n"+usage, fg('red'))

    return
# aliases
_tootstream.add_command(search, 's')


@_tootstream.command( 'info', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='info about your account' )
def info():
    """Prints your user info."""
    mastodon = get_active_mastodon()
    user = mastodon.account_verify_credentials()
    printUser(user)
# aliases
_tootstream.add_command(info, 'me')


@_tootstream.command( 'delete', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='delete a toot' )
@click.argument('tootid', metavar='<id>')
def delete(tootid):
    """Deletes your toot by ID"""
    mastodon = get_active_mastodon()
    #tootid = IDS.to_global(tootid)
    if tootid is None:
        return print_error("error: invalid ID.")
    mastodon.status_delete(tootid)
    print("  Poof! It's gone.")
# aliases
_tootstream.add_command(delete, 'del')
_tootstream.add_command(delete, 'rm')


import tootstream.toot_cmds_settings
import tootstream.toot_cmds_relations
_tootstream.add_command(tootstream.toot_cmds_settings._profile)
_tootstream.add_command(tootstream.toot_cmds_relations._follow)
_tootstream.add_command(tootstream.toot_cmds_relations._block)
_tootstream.add_command(tootstream.toot_cmds_relations._mute)

# if using a CommandCollection ....
#_tootstreamCommands.add_source(_tootstream)
#####################################
######### END COMMAND BLOCK #########
#####################################


#####################################
######## MAIN #######################
#####################################
@click.command(context_settings=CONTEXT_SETTINGS)
@click.option( '--instance', '-i', metavar='<hostname>',
               help='Hostname of the instance to connect' )
@click.option( '--email', '-e', metavar='<email>',
               help='Email to login' )
@click.option( '--password', '-p', metavar='<PASSWD>',
               help='Password to login (UNSAFE)' )
@click.option( '--config', '-c', metavar='<file>',
               type=click.Path(exists=False, readable=True),
               default='~/.config/tootstream/tootstream.conf',
               help='Location of alternate configuration file to load' )
@click.option( '--profile', '-P', metavar='<profile>', default='default',
               help='Name of profile for saved credentials (default)' )
def main(instance, email, password, config, profile):
    configpath = os.path.expanduser(config)
    if os.path.isfile(configpath) and not os.access(configpath, os.W_OK):
        # warn the user before they're asked for input
        cprint("Config file does not appear to be writable: "+configpath, fg('red'))

    set_configfile(configpath)
    cfg = parse_config()
    if not cfg.has_section(profile):
        cfg.add_section(profile)

    instance, client_id, client_secret, token = parse_or_input_profile(profile, instance, email, password)


    mastodon = Mastodon(
        client_id=client_id,
        client_secret=client_secret,
        access_token=token,
        api_base_url="https://" + instance)

    cfg[profile] = {
        'instance': instance,
        'client_id': client_id,
        'client_secret': client_secret,
        'token': token
    }

    set_active_mastodon(mastodon)
    set_active_profile(profile)
    save_config()


    cprint("Welcome to tootstream! Two-Factor-Authentication is currently not supported.", fg('blue'))
    print("You are connected to ", end="")
    cprint(instance, fg('green') + attr('bold'))
    print("Enter a command. Use 'help' for a list of commands.")
    print("\n")

    user = mastodon.account_verify_credentials()
    prompt = "[@" + str(user['username']) + " (" + profile + ")]: "

    # setup shell
    #ctx = _tootstreamCommands.make_context('tootstreamShell', [], parent=click.get_current_context())
    ctx = _tootstream.make_context('tootstreamShell', [], parent=click.get_current_context())
    shell = make_click_shell(ctx, prompt=prompt, intro='', hist_file='/dev/null')
    # push shell object onto the context to enable dynamic prompt
    set_shell(shell)
    set_prompt(prompt)
    # and go
    shell.cmdloop()
    print("Goodbye!")


if __name__ == '__main__':
    main()
