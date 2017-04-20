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
#from tootstream import TootParser, TootIdDict, TootStreamCmd, TootStreamGroup
from click_shell import make_click_shell
from mastodon import Mastodon
from collections import OrderedDict
from colored import fg, attr, stylize

COLORS = ['red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']
RESERVED = ( "theme", "global" )
KEYCFGFILE = __name__ + 'cfgfile'
KEYPROFILE = __name__ + 'profile'
KEYPROMPT = __name__ + 'prompt'
KEYMASTODON = __name__ + 'mastodon'
KEYSHELL=__name__ + 'shell'
CONTEXT_SETTINGS = dict( help_option_names=['-h', '--help'],
                         max_content_width=100 )


IDS = TootIdDict();
cfg = configparser.ConfigParser()
toot_parser = TootParser(indent='  ')


#####################################
######## UTILITY FUNCTIONS # ########
#####################################
def get_content(toot):
    html = toot['content']
    toot_parser.reset()
    toot_parser.feed(html)
    toot_parser.close()
    return toot_parser.get_text()


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


def get_prompt():
    return click.get_current_context().meta.get(KEYPROMPT)


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
    p = cfg[profile]
    return p['instance'], p['client_id'], p['client_secret'], p['token']


def get_known_profiles():
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
        print("...No configuration found, generating...")
        return

    try:
        cfg.read(filename)
    except configparser.Error:
        cprint("This does not look like a valid configuration:"+filename, fg('red'))
        sys.exit("Goodbye!")


def save_config():
    filename = get_configfile()
    (dirpath, basename) = os.path.split(filename)
    if not (dirpath == "" or os.path.exists(dirpath)):
        os.makedirs(dirpath)

    try:
        with open(filename, 'w') as configfile:
            cfg.write(configfile)
    except os.error:
        cprint("Unable to write configuration to "+filename, fg('red'))


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


#####################################
######## OUTPUT FORMATTING # ########
#####################################
def cprint(text, style, end="\n"):
    print(stylize(text, style), end=end)


def parse_or_input_profile(profile, instance=None, email=None, password=None):
    """
    Validate an existing profile or get user input to generate a new one.
    """
    global cfg
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


def cprint(text, style, end="\n"):
    print(stylize(text, style), end=end)


def print_profiles():
    active = get_active_profile()
    inactiveprofiles = get_known_profiles()
    try:
        inactiveprofiles.remove(active)
    except ValueError:
        # somebody removed the active profile. don't panic.
        pass
    # TODO: wrap based on termwidth
    inactives = ' '.join(inactiveprofiles)
    cprint("  *"+active, fg('red'), end="")
    cprint("  "+inactives, fg('blue'))
    return


def printHistoryToot(toot):
    """Prints toot nicely with hardcoded colors"""
    display_name = "  " + toot['account']['display_name']
    username = " @" + toot['account']['username'] + " "
    reblogs_count = "  ♺:" + str(toot['reblogs_count'])
    favourites_count = " ♥:" + str(toot['favourites_count']) + " "
    toot_id = str(IDS.to_local(toot['id']))

    # Prints individual toot/tooter info
    cprint(display_name, fg('green'), end="",)
    cprint(username + toot['created_at'], fg('yellow'))
    cprint(reblogs_count + favourites_count, fg('cyan'), end="")
    cprint(toot_id, fg('red'))
    content = get_content(toot)
    print(content + "\n")


def printTimelineToot(toot):
    mastodon = get_active_mastodon()
    display_name = "  " + toot['account']['display_name'] + " "
    username = "@" + toot['account']['acct'] + " "
    reblogs_count = "  ♺:" + str(toot['reblogs_count'])
    favourites_count = " ♥:" + str(toot['favourites_count']) + " "
    toot_id = str(IDS.to_local(toot['id']))

    random.seed(display_name)

    # Prints individual toot/tooter info
    random.seed(display_name)
    cprint(display_name, fg(random.choice(COLORS)), end="")
    cprint(username, fg('green'), end="")
    cprint(toot['created_at'], attr('dim'))

    cprint(reblogs_count, fg('cyan'), end="")
    cprint(favourites_count, fg('yellow'), end="")

    cprint("id:" + toot_id, fg('red'))
    content = get_content(toot)

    # Shows boosted toots as well
    if toot['reblog']:
        username = "  Boosted @" + toot['reblog']['account']['acct'] +": "
        cprint(username, fg('blue'), end="")
        content = get_content(toot['reblog'])
        cprint(content + "\n", fg('white'))

    # Show context of toot being replied to
    elif toot['in_reply_to_id']:
        repliedToot = mastodon.status(toot['in_reply_to_id'])
        username = "  Replied @" + repliedToot['account']['acct'] +": "
        cprint(username, fg('blue'), end="")
        repliedTootContent = get_content(repliedToot)
        cprint(repliedTootContent + "\n", fg('blue'))
        cprint(content + "\n", fg('white'))

    else:
        cprint(content + "\n", fg('white'))


def printUser(user):
    """Prints user data nicely with hardcoded colors."""
    print("@" + str(user['username']))
    cprint(user['display_name'], fg('cyan'))
    print(user['url'])
    cprint(re.sub('<[^<]+?>', '', user['note']), fg('red'))


def printUsersShort(users):
    for user in users:
        if not user: continue
        locked = ""
        # lock glyphs: masto web uses FontAwesome's U+F023 (nonstandard)
        # lock emoji: U+1F512
        if user['locked']: locked = " \U0001f512"
        userstr = "@"+str(user['acct'])+locked
        userid = "(id:"+str(user['id'])+")"
        userdisp = "'"+str(user['display_name'])+"'"
        userurl = str(user['url'])
        cprint("  "+userstr, fg('green'), end=" ")
        cprint(" "+userid, fg('red'), end=" ")
        cprint(" "+userdisp, fg('cyan'))
        cprint("      "+userurl, fg('blue'))


def print_error(msg):
    cprint(msg, fg('red')+attr('bold'))


#####################################
######## BEGIN COMMAND BLOCK ########
#####################################

@click.group( 'tootstream', short_help='tootstream commands',
              cls=TootStreamGroup,
              context_settings=CONTEXT_SETTINGS,
              invoke_without_command=True,
              options_metavar='',
              subcommand_metavar='<command>' )
def tootstream():
    """Tootstream commands.

    Commands can be tab-completed. Some readline keybindings are supported.
    Command history is available but not saved between sessions.

    unimplemented: 2FA, CW/NSFW, media attachments, user timelines, favourites list
    """
    pass


@tootstream.command( 'help', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='get help for a command' )
@click.argument('cmd', metavar='<cmd>', required=False, default=None)
def help(cmd):
    """Get details on how to use a command."""
    ctx = click.get_current_context()
    if not cmd is None:
        c = tootstream.get_command(ctx, cmd)
        click.echo(c.get_help(ctx))
        return
    click.echo(tootstream.get_help(ctx))


@tootstream.command( 'toot', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='post a toot' )
@click.argument('text', nargs=-1, metavar='<text>')
def toot(text):
    """Publish a toot. ex: 'toot Hello World' will publish 'Hello World'."""
    mastodon = get_active_mastodon()
    post_text = ' '.join(text)
    mastodon.toot(post_text)
    cprint("You tooted: ", fg('magenta') + attr('bold'), end="")
    cprint(rest, fg('magenta') + attr('bold') + attr('underlined'))
# aliases
tootstream.add_command(toot, 't')


@tootstream.command( 'boost', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='boost a toot' )
@click.argument('tootid', metavar='<id>')
def boost(tootid):
    """Boosts a toot by ID."""
    mastodon = get_active_mastodon()
    tootid = IDS.to_global(tootid)
    if tootid is None:
        return print_error("error: invalid ID.")
    mastodon.status_reblog(tootid)
    boosted = mastodon.status(tootid)
    msg = "  Boosted: " + get_content(boosted)
    cprint(msg, fg('green'))
# aliases
tootstream.add_command(boost, 'rt')
tootstream.add_command(boost, 'retoot')


@tootstream.command( 'unboost', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='undo a boost' )
@click.argument('tootid', metavar='<id>')
def unboost(tootid):
    """Removes a boosted tweet by ID."""
    mastodon = get_active_mastodon()
    tootid = IDS.to_global(tootid)
    if tootid is None:
        return print_error("error: invalid ID.")
    mastodon.status_unreblog(tootid)
    unboosted = mastodon.status(tootid)
    msg = "  Removed boost: " + get_content(unboosted)
    cprint(msg, fg('red'))


@tootstream.command( 'fav', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='favorite a toot' )
@click.argument('tootid', metavar='<id>')
def fav(tootid):
    """Favorites a toot by ID."""
    mastodon = get_active_mastodon()
    tootid = IDS.to_global(tootid)
    if tootid is None:
        return print_error("error: invalid ID.")
    mastodon.status_favourite(tootid)
    faved = mastodon.status(tootid)
    msg = "  Favorited: " + get_content(faved)
    cprint(msg, fg('red'))
# aliases
tootstream.add_command(fav, 'star')


@tootstream.command( 'reply', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='reply to a toot' )
@click.argument('tootid', metavar='<id>')
@click.argument('text', nargs=-1, metavar='<text>')
def reply(tootid, text):
    """Reply to a toot by ID."""
    mastodon = get_active_mastodon()
    reply_text = ' '.join(text)
    parent_id = IDS.to_global(tootid)
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
tootstream.add_command(reply, 'r')
tootstream.add_command(reply, 'rep')


@tootstream.command( 'unfav', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='unfavorite a toot' )
@click.argument('tootid', metavar='<id>')
def unfav(tootid):
    """Removes a favorite toot by ID."""
    mastodon = get_active_mastodon()
    tootid = IDS.to_global(tootid)
    if tootid is None:
        return print_error("error: invalid ID.")
    mastodon.status_unfavourite(tootid)
    unfaved = mastodon.status(tootid)
    msg = "  Removed favorite: " + get_content(unfaved)
    cprint(msg, fg('yellow'))


@tootstream.command( 'home', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='show home timeline' )
def home():
    """Displays the Home timeline."""
    mastodon = get_active_mastodon()
    for toot in reversed(mastodon.timeline_home()):
        printTimelineToot(toot)
# aliases
tootstream.add_command(home, 'h')


@tootstream.command( 'public', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='show public timeline' )
def public():
    """Displays the Public (federated) timeline."""
    mastodon = get_active_mastodon()
    for toot in reversed(mastodon.timeline_public()):
        printTimelineToot(toot)
# aliases
tootstream.add_command(public, 'public')
tootstream.add_command(public, 'fed')


@tootstream.command( 'local', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='show local timeline' )
def local():
    """Displays the Local (instance) timeline."""
    mastodon = get_active_mastodon()
    for toot in reversed(mastodon.timeline_local()):
        printTimelineToot(toot)
# aliases
tootstream.add_command(local, 'l')


@tootstream.command( 'thread', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='thread history of a toot' )
@click.argument('tootid', metavar='<id>')
def thread(tootid):
    """Displays the thread this toot is part of, ex: 'thread 7'"""
    mastodon = get_active_mastodon()
    tootid = IDS.to_global(tootid)
    if tootid is None:
        return
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
    toot_id = str(IDS.to_local(currentToot['id']))
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
tootstream.add_command(thread, 'history')
tootstream.add_command(thread, 'detail')


@tootstream.command( 'note', options_metavar='',
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
            cprint(display_name + username + " followed you!", fg('red') + bg('green'))

        # blank line
        print('')
# aliases
tootstream.add_command(note, 'n')


@tootstream.command( 'whois', options_metavar='',
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
tootstream.add_command(whois, 'who')


@tootstream.command( 'whatis', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='search for a hashtag' )
@click.argument('tag', metavar='<tag>')
def whatis(tag):
    """Search for a hashtag."""
    mastodon = get_active_mastodon()
    for toot in reversed(mastodon.timeline_hashtag(tag)):
        printTimelineToot(toot, mastodon)
# aliases
tootstream.add_command(whatis, 'what')


@tootstream.command( 'search', options_metavar='',
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
tootstream.add_command(search, 's')


@tootstream.command( 'info', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='info about your account' )
def info():
    """Prints your user info."""
    mastodon = get_active_mastodon()
    user = mastodon.account_verify_credentials()
    printUser(user)
# aliases
tootstream.add_command(info, 'me')


@tootstream.command( 'delete', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='delete a toot' )
@click.argument('tootid', metavar='<id>')
def delete(tootid):
    """Deletes your toot by ID"""
    mastodon = get_active_mastodon()
    tootid = IDS.to_global(tootid)
    if tootid is None:
        return print_error("error: invalid ID.")
    mastodon.status_delete(tootid)
    print("  Poof! It's gone.")
# aliases
tootstream.add_command(delete, 'del')
tootstream.add_command(delete, 'rm')


@tootstream.command( 'followers', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='list who follows you' )
def followers():
    """Lists users who follow you."""
    mastodon = get_active_mastodon()
    user = mastodon.account_verify_credentials()
    users = mastodon.account_followers(user['id'])
    if not users:
        cprint("  You don't have any followers", fg('red'))
    else:
        cprint("  Your followers:", fg('magenta'))
        printUsersShort(users)


@tootstream.command( 'following', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='list who you follow' )
def following():
    """Lists users you follow."""
    mastodon = get_active_mastodon()
    user = mastodon.account_verify_credentials()
    users = mastodon.account_following(user['id'])
    if not users:
        cprint("  You're safe!  There's nobody following you", fg('red'))
    else:
        cprint("  People following you:", fg('magenta'))
        printUsersShort(users)


@tootstream.command( 'blocks', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='list users you block' )
def blocks():
    """Lists users you have blocked."""
    mastodon = get_active_mastodon()
    users = mastodon.blocks()
    if not users:
        cprint("  You haven't blocked anyone (... yet)", fg('red'))
    else:
        cprint("  You have blocked:", fg('magenta'))
        printUsersShort(users)


@tootstream.command( 'mutes', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='list users you mute' )
def mutes():
    """Lists users you have muted."""
    mastodon = get_active_mastodon()
    users = mastodon.mutes()
    if not users:
        cprint("  You haven't muted anyone (... yet)", fg('red'))
    else:
        cprint("  You have muted:", fg('magenta'))
        printUsersShort(users)


@tootstream.command( 'requests', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='list requests to follow you' )
def requests():
    """Lists your incoming follow requests."""
    mastodon = get_active_mastodon()
    users = mastodon.follow_requests()
    if not users:
        cprint("  You have no incoming requests", fg('red'))
    else:
        cprint("  These users want to follow you:", fg('magenta'))
        printUsersShort(users)
        cprint("  run 'accept <id>' to accept", fg('magenta'))
        cprint("   or 'reject <id>' to reject", fg('magenta'))


@tootstream.command( 'block', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='block a user' )
@click.argument('username', metavar='<user>')
def block(username):
    """Blocks a user by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShort(userid)
    elif userid == -1:
        cprint("  username not found", fg('red'))
    else:
        try:
            relations = mastodon.account_block(userid)
            if relations['blocking']:
                cprint("  user " + str(userid) + " is now blocked", fg('blue'))
        except:
            cprint("  ... well, it *looked* like it was working ...", fg('red'))
# aliases
tootstream.add_command(block, 'bl')


@tootstream.command( 'unblock', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='unblock a user' )
@click.argument('username', metavar='<user>')
def unblock(username):
    """Unblocks a user by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShort(userid)
    elif userid == -1:
        cprint("  username not found", fg('red'))
    else:
        try:
            relations = mastodon.account_unblock(userid)
            if not relations['blocking']:
                cprint("  user " + str(userid) + " is now unblocked", fg('blue'))
        except:
            cprint("  ... well, it *looked* like it was working ...", fg('red'))


@tootstream.command( 'follow', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='follow a user' )
@click.argument('username', metavar='<user>')
def follow(username):
    """Follows an account by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShort(userid)
    elif userid == -1:
        cprint("  username not found", fg('red'))
    else:
        try:
            relations = mastodon.account_follow(userid)
            if relations['following']:
                cprint("  user " + str(userid) + " is now followed", fg('blue'))
        except:
            cprint("  ... well, it *looked* like it was working ...", fg('red'))


@tootstream.command( 'unfollow', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='unfollow a user' )
@click.argument('username', metavar='<user>')
def unfollow(username):
    """Unfollows an account by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShort(userid)
    elif userid == -1:
        cprint("  username not found", fg('red'))
    else:
        try:
            relations = mastodon.account_unfollow(userid)
            if not relations['following']:
                cprint("  user " + str(userid) + " is now unfollowed", fg('blue'))
        except:
            cprint("  ... well, it *looked* like it was working ...", fg('red'))


@tootstream.command( 'mute', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='mute a user' )
@click.argument('username', metavar='<user>')
def mute(username):
    """Mutes a user by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShort(userid)
    elif userid == -1:
        cprint("  username not found", fg('red'))
    else:
        try:
            relations = mastodon.account_mute(userid)
            if relations['muting']:
                cprint("  user " + str(userid) + " is now muted", fg('blue'))
        except:
            cprint("  ... well, it *looked* like it was working ...", fg('red'))


@tootstream.command( 'unmute', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='unmute a user' )
@click.argument('username', metavar='<user>')
def unmute(username):
    """Unmutes a user by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShort(userid)
    elif userid == -1:
        cprint("  username not found", fg('red'))
    else:
        try:
            relations = mastodon.account_unmute(userid)
            if not relations['muting']:
                cprint("  user " + str(userid) + " is now unmuted", fg('blue'))
        except:
            cprint("  ... well, it *looked* like it was working ...", fg('red'))


@tootstream.command( 'accept', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='accept a follow request' )
@click.argument('username', metavar='<user>')
def accept(username):
    """Accepts a user's follow request by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShort(userid)
    elif userid == -1:
        cprint("  username not found", fg('red'))
    else:
        try:
            user = mastodon.follow_request_authorize(userid)
            # a more thorough check would be to call
            # mastodon.account_relationships(user['id'])
            # and check the returned data
            # here we're lazy and assume we're good if the
            # api return matches the request
            if user['id'] == userid:
                cprint("  user " + str(userid) + "'s request is accepted", fg('blue'))
        except:
            cprint("  ... well, it *looked* like it was working ...", fg('red'))


@tootstream.command( 'reject', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='reject a follow request' )
@click.argument('username', metavar='<user>')
def reject(username):
    """Rejects a user's follow request by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShort(userid)
    elif userid == -1:
        cprint("  username not found", fg('red'))
    else:
        try:
            user = mastodon.follow_request_reject(userid)
            # a more thorough check would be to call
            # mastodon.account_relationships(user['id'])
            # and check the returned data
            # here we're lazy and assume we're good if the
            # api return matches the request
            if user['id'] == userid:
                cprint("  user " + str(userid) + "'s request is rejected", fg('blue'))
        except:
            cprint("  ... well, it *looked* like it was working ...", fg('red'))


@tootstream.group( 'profile', short_help='profile load|create|remove|list',
                   cls=TootStreamGroup,
                   context_settings=CONTEXT_SETTINGS,
                   invoke_without_command=True,
                   no_args_is_help=True,
                   options_metavar='',
                   subcommand_metavar='<command>' )
def profile():
    """Profile management operations: create, load, remove, list.
    Additions and removals will save the configuration file."""
    pass


@profile.command( 'help', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='get help for a command' )
@click.argument('cmd', metavar='<cmd>', required=False, default=None)
def profile_help(cmd):
    """Get details on how to use a command."""
    ctx = click.get_current_context()
    if not cmd is None:
        c = profile.get_command(ctx, cmd)
        click.echo(c.get_help(ctx))
        return
    click.echo(profile.get_help(ctx))


@profile.command( 'list', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='list known profiles' )
def profile_list():
    """List known profiles."""
    print_profiles()
    return
# aliases
profile.add_command(profile_list, 'ls')


@profile.command( 'add', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='add a profile' )
@click.argument('profile', metavar='[<profile>', required=False, default=None)
@click.argument('instance', metavar='[<hostname>', required=False, default=None)
@click.argument('email', metavar='[<email>', required=False, default=None)
@click.argument('password', metavar='[<passwd>]]]]', required=False, default=None)
def profile_add(profile, instance, email, password):
    """Create a new profile.

    \b
        profile:  name of the profile to add
       hostname:  instance this account is on
          email:  email to log into the account
         passwd:  password to the account (UNSAFE -- this will be visible)"""
    if profile is None:
        profile = input("  Profile name: ")

    if profile in RESERVED:
        print_error("Illegal profile name: " + profile)
        return
    elif profile in get_known_profiles():
        print_error("Profile " + profile + " exists")
        return

    instance, client_id, client_secret, token = parse_or_input_profile(profile)
    try:
        newmasto = Mastodon(
            client_id=client_id,
            client_secret=client_secret,
            access_token=token,
            api_base_url="https://" + instance)
    except:
        print_error("Mastodon error")
        return

    # update stuff
    cfg[profile] = {
        'instance': instance,
        'client_id': client_id,
        'client_secret': client_secret,
        'token': token
    }
    user = newmasto.account_verify_credentials()
    set_prompt("[@" + str(user['username']) + " (" + profile + ")]: ")
    set_active_profile(profile)
    set_active_mastodon(newmasto)
    cprint("  Profile " + profile + " loaded", fg('green'))
    return
# aliases
profile.add_command(profile_add, 'new')
profile.add_command(profile_add, 'create')


@profile.command( 'del', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='delete a profile' )
@click.argument('profile', metavar='<profile>', required=False, default=None)
def profile_del(profile):
    """Delete a profile."""
    if profile is None:
        profile = input("  Profile name: ")

    if profile in [RESERVED, "default"]:
        print_error("Illegal profile name: " + profile)
        return

    cfg.remove_section(profile)
    save_config()
    cprint("  Poof! It's gone.", fg('blue'))
    if profile == get_active_profile():
        set_active_profile("")
    return
# aliases
profile.add_command(profile_del, 'delete')
profile.add_command(profile_del, 'rm')
profile.add_command(profile_del, 'remove')


@profile.command( 'load', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='load a profile' )
@click.argument('profile', metavar='<profile>', required=False, default=None)
def profile_load(profile):
    """Load a different profile."""
    if profile is None:
        profile = input("  Profile name: ")

    if profile in get_known_profiles():
        # shortcut for preexisting profiles
        try:
            instance, client_id, client_secret, token = get_profile_values(profile)
        except:
            print_error("Invalid or corrupt profile")
            return

        try:
            newmasto = Mastodon(
                client_id=client_id,
                client_secret=client_secret,
                access_token=token,
                api_base_url="https://" + instance)
        except:
            print_error("Mastodon error")
            return

        # update stuff
        user = newmasto.account_verify_credentials()
        set_prompt("[@" + str(user['username']) + " (" + profile + ")]: ")
        set_active_profile(profile)
        set_active_mastodon(newmasto)
        cprint("  Profile " + profile + " loaded", fg('green'))
        return
    else:
        print_error("Profile " + profile + " doesn't seem to exist")
        print_profiles()

    return
# aliases
profile.add_command(profile_load, 'open')


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
    parse_config()
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
    ctx = tootstream.make_context('tootstream', [], parent=click.get_current_context())
    shell = make_click_shell(ctx, prompt=prompt, intro='', hist_file='/dev/null')
    # push shell object onto the context to enable dynamic prompt
    ctx.meta[KEYSHELL] = shell
    set_prompt(prompt)
    # and go
    shell.cmdloop()
    print("Goodbye!")


if __name__ == '__main__':
    main()
