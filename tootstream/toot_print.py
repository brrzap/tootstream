import click
import random
import re
from mastodon import Mastodon
from colored import fg, attr, stylize
from .toot_parser import TootParser
#from .toot_utils import get_active_profile, get_known_profile, get_active_mastodon

COLORS = ['red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']
GLYPH_LOCK      = '\U0001f512'  # lock emoji (masto web uses FontAwesome's U+F023 but nonstd)
GLYPH_FAVE      = '♥'
GLYPH_BOOST     = '♺'
GLYPH_PINEAPPLE = '\U0001f34d'  # pineapple
GLYPH_PUBLIC    = '\U0001f30e'  # globe
GLYPH_UNLISTED  = '\U0001f47b'  # ghost '\U0001f47b' ... mute '\U0001f507' ??
GLYPH_PRIVATE   = '\U0001f512'  # lock
GLYPH_DIRECT    = '\U0001f4e7'  # envelopes: '\U0001f4e7' '\U0001f4e9' '\U0001f48c' '\U00002709'
VISIBILITY = { 'public':   GLYPH_PUBLIC,
               'unlisted': GLYPH_UNLISTED,
               'private':  GLYPH_PRIVATE,
               'direct':   GLYPH_DIRECT,       # TODO: verify with api, maybe Mastodon.py lacks support
               'unknown':  GLYPH_PINEAPPLE }
_indent = "  "
toot_parser = TootParser(indent='  ', width=75)


### text wrapping
#def _format_paragraph(text):
#    width = click.get_terminal_size()[0]
#    print("width is "+str(width))
#    return text
#    return click.wrap_text(text, width=width-5, initial_indent=_indent, subsequent_indent=_indent, preserve_paragraphs=True)
#    #return click.wrap_text(text, width=width-5, initial_indent=_indent, subsequent_indent=_indent)


### html formatting
def _format_html(html):
    # update terminal size
    (width, _) = click.get_terminal_size()
    if toot_parser.wrap:
        toot_parser.wrap.width = width*3//4
    toot_parser.reset()
    toot_parser.feed(html)
    toot_parser.close()
    return toot_parser.get_text()


def get_content(toot):
    return _format_html(toot['content'])


### User dict formatting
def _format_display_name(user):
    return "'" + user['display_name'] + "'"

def _format_username(user):
    if user['locked']:
        return "@" + user['acct'] + " " + GLYPH_LOCK
    return "@" + user['acct']


### Toot dict formatting
def _format_boost_count(toot):
    return GLYPH_BOOST + ":" + str(toot['reblogs_count'])

def _format_faves_count(toot):
    return GLYPH_FAVE + ":" + str(toot['favourites_count'])

def _format_id(tootoruser):
    #toot_id = str(IDS.to_local(toot['id']))
    return "id:" + str(tootoruser['id'])

def _format_time(toot):
    return str(toot['created_at'])

def _format_spoiler(toot):
    if not toot['spoiler_text']: return ''
    return "CW: " + toot['spoiler_text']

def _format_visibility(toot):
    return "vis:" + VISIBILITY[toot['visibility']]

def _format_media(toot):
    # TODO: implement
    pass


_pineapple = '\U0001f34d'  # can never have too many
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
    cprint(_indent + "*"+active, fg('red'), end="")
    cprint("  "+inactives, fg('blue'))
    return


def printHistoryToot(toot):
    """Prints toot nicely with hardcoded colors"""
    # Prints individual toot/tooter info
    cprint(_indent + _format_display_name(toot['account']), fg('green'), end=" ")
    cprint(_format_username(toot['account']), fg('yellow'))
    cprint(_indent + _format_visibility(toot), fg('blue'), end=" ")
    cprint(_indent + _format_boost_count(toot) + " " + _format_faves_count(toot), fg('cyan'), end=" ")
    cprint(_format_id(toot), fg('red'), end=" ")
    cprint(_format_time(toot), attr('dim'))
    if toot['spoiler_text']:
        cprint(_indent + _format_spoiler(toot), fg('red'))
    content = get_content(toot)
    print(content + "\n")


def printTimelineToot(toot):
    from .toot_utils import get_active_mastodon
    mastodon = get_active_mastodon()
    random.seed()
    # Prints individual toot/tooter info
    cprint(_indent + _format_display_name(toot['account']), fg(random.choice(COLORS)), end=" ")
    cprint(_format_username(toot['account']), fg('green'))
    cprint(_indent + _format_visibility(toot), fg('blue'), end=" ")
    cprint(_indent + _format_boost_count(toot), fg('cyan'), end=" ")
    cprint(_format_faves_count(toot), fg('yellow'), end=" ")
    cprint(_format_id(toot), fg('red'), end=" ")
    cprint(_format_time(toot), attr('dim'))
    content = get_content(toot)

    # header for boosted toots
    if toot['reblog']:
        cprint(_indent + "Boosted " + _format_id(toot['reblog']) + " from " + _format_username(toot['reblog']['account']), fg('blue'), end=":\n")
        content = _indent + get_content(toot['reblog'])
        # ignore toot['reblog']['spoiler_text'] here,
        # if it's different there's something very wrong

    # header for a reply
    elif toot['in_reply_to_id']:
        repliedToot = mastodon.status(toot['in_reply_to_id'])
        cprint(_indent + "Replied to " + _format_id(repliedToot) + " from " + _format_username(repliedToot['account']), fg('blue'), end=":\n")
        repliedTootContent = get_content(repliedToot)
        if repliedToot['spoiler_text']:
            cprint(_indent + _indent + _format_spoiler(repliedToot), fg('red'), end=": ")
        cprint(repliedTootContent + "\n", fg('blue'))

    # last but not least, spoilertext (CW)
    if toot['spoiler_text']:
        cprint(_indent + _format_spoiler(toot), fg('red'), end=":\n")
    cprint(content + "\n", fg('white'))


def _print_name_line_solid(user, style, end='\n'):
    cprint( _indent + _format_display_name(user)
            + " " + _format_username(user), style, end )
    return


def _print_id_line_solid(toot, style, end='\n'):
    cprint( _indent + _format_visibility(toot)
            + " " + _format_boost_count(toot)
            + " " + _format_faves_count(toot)
            + " " + _format_id(toot)
            + " " + _format_time(toot), style, end )
    return


def printNotification(note):
    """ """
    # Mentions
    if note['type'] == 'mention':
        _print_name_line_solid(note['account'], fg('magenta'), end='')
        cprint(" mentioned you =======", fg('magenta'))
        printTimelineToot(note['status'])

    # Favorites
    elif note['type'] == 'favourite':
        _print_name_line_solid(note['account'], fg('green'), end='')
        cprint(" favorited your status:", fg('green'))
        _print_id_line_solid(note['status'], fg('green'))
        if note['status']['spoiler_text']:
            cprint(_indent + _format_spoiler(note['status']), fg('red'))
        cprint(get_content(note['status']), fg('green'))

    # Boosts
    elif note['type'] == 'reblog':
        _print_name_line_solid(note['account'], fg('yellow'), end='')
        cprint(" boosted your toot:", fg('yellow'))
        _print_id_line_solid(note['status'], fg('yellow'))
        if note['status']['spoiler_text']:
            cprint(_indent + _format_spoiler(note['status']), fg('red'))
        cprint(get_content(note['status']), fg('yellow'))

    # Follows
    elif note['type'] == 'follow':
        _print_name_line_solid(note['account'], fg('red'), end='')
        cprint(" followed you!", fg('red'))

    else:
        print_error("Unknown notification type: "+str(note['type'])+" (id:"+str(note['id'])+")")
    # blank line
    print('')


def printUser(user):
    """Prints user data nicely with hardcoded colors."""
    if not user: return
    cprint(_indent + _pineapple + " " + _format_username(user), fg('cyan'), end="  ")
    cprint(_format_display_name(user), fg('red'))
    cprint(_indent + user['url'], fg('blue'))
    cprint(_format_html(user['note']), fg('green'))


def printUserShort(user):
    """Prints user data in an abbreviated 2-line format."""
    if not user: return
    cprint(_indent + _pineapple + " " + _format_username(user), fg('blue'), end=" ")
    cprint(_format_id(user), fg('red'), end=" ")
    cprint(_format_display_name(user), fg('cyan'))
    cprint(_indent + _indent + user['url'], fg('green'))


def printUsersShort(users):
    for user in users:
        if not user: continue
        printUserShort(user)


def print_error(msg):
    cprint(msg, fg('red')+attr('bold'))



__all__ = [ 'cprint',
            'get_content',
            'print_profiles',
            'printHistoryToot',
            'printTimelineToot',
            'printNotification',
            'printUser',
            'printUserShort',
            'printUsersShort',
            'print_error' ]

