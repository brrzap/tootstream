import click
import random
import re
from mastodon import Mastodon
from colored import fg, attr, stylize
#from .toot_utils import get_active_profile, get_known_profile, get_active_mastodon, get_content

COLORS = ['red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']


def cprint(text, style, end="\n"):
    print(stylize(text, style), end=end)


def print_profiles():
    """Prints existing profile names in a horizontal list."""
    # TODO: make them nice columns
    from .toot_utils import get_active_profile, get_known_profiles

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
    from .toot_utils import get_content
    display_name = "  " + toot['account']['display_name']
    username = " @" + toot['account']['username'] + " "
    reblogs_count = "  ♺:" + str(toot['reblogs_count'])
    favourites_count = " ♥:" + str(toot['favourites_count']) + " "
    #toot_id = str(IDS.to_local(toot['id']))
    toot_id = str(toot['id']) # FIXME dropping local-ID concept, cleanup

    # Prints individual toot/tooter info
    cprint(display_name, fg('green'), end="",)
    cprint(username + toot['created_at'], fg('yellow'))
    cprint(reblogs_count + favourites_count, fg('cyan'), end="")
    cprint(toot_id, fg('red'))
    content = get_content(toot)
    print(content + "\n")


def printTimelineToot(toot):
    from .toot_utils import get_content, get_active_mastodon
    mastodon = get_active_mastodon()
    display_name = "  " + toot['account']['display_name'] + " "
    username = "@" + toot['account']['acct'] + " "
    reblogs_count = "  ♺:" + str(toot['reblogs_count'])
    favourites_count = " ♥:" + str(toot['favourites_count']) + " "
    #toot_id = str(IDS.to_local(toot['id']))
    toot_id = str(toot['id']) # FIXME dropping local-ID concept, cleanup

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
    if not user: return
    locked = ""
    # lock glyphs: masto web uses FontAwesome's U+F023 (nonstandard)
    # lock emoji: U+1F512
    if user['locked']: locked = " \U0001f512"
    print("@" + str(user['username']) + locked)
    cprint(user['display_name'], fg('cyan'))
    print(user['url'])
    cprint(re.sub('<[^<]+?>', '', user['note']), fg('red'))


def printUserShort(user):
    """Prints user data in an abbreviated 2-line format."""
    if not user: return
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


def printUsersShort(users):
    for user in users:
        if not user: continue
        printUserShort(user)


def print_error(msg):
    cprint(msg, fg('red')+attr('bold'))



__all__ = [ 'cprint',
            'print_profiles',
            'printHistoryToot',
            'printTimelineToot',
            'printUser',
            'printUserShort',
            'printUsersShort',
            'print_error' ]

#from .toot_utils import *
