import click
import random
import re
import arrow
from mastodon import Mastodon
from colored import fg, attr, stylize
from .toot_parser import TootParser
#from .toot_utils import get_active_profile, get_known_profile, get_active_mastodon

#####################################
######## BEGIN COMMAND BLOCK ########
#####################################
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
               'direct':   GLYPH_DIRECT,
               'unknown':  GLYPH_PINEAPPLE }
_indent = "  "
_continued = "[...]"
toot_parser = TootParser(indent='  ', width=75)
random.seed()


### text wrapping
#def _format_paragraph(text):
#    width = click.get_terminal_size()[0]
#    print("width is "+str(width))
#    return text
#    return click.wrap_text(text, width=width-5, initial_indent=_indent, subsequent_indent=_indent, preserve_paragraphs=True)
#    #return click.wrap_text(text, width=width-5, initial_indent=_indent, subsequent_indent=_indent)


#####################################
######## FORMAT HELPERS      ########
#####################################
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

def _format_counts(toot):
    return _format_boost_count(toot) + " " + _format_faves_count(toot)

def _format_id(tootoruser):
    #toot_id = str(IDS.to_local(toot['id']))
    return "id:" + str(tootoruser['id'])

def _format_time(toot):
    return str(toot['created_at'])

def _format_time_relative(toot):
    return arrow.get(toot['created_at']).humanize()

def _format_spoiler(toot):
    if not toot['spoiler_text']: return ''
    return "[CW: " + toot['spoiler_text'] + "]"

def _format_visibility(toot):
    return "vis:" + VISIBILITY[toot['visibility']]

def _format_nsfw(toot):
    if not toot['sensitive']: return ''
    return "[NSFW]"


### Media dict formatting
def _format_media(toot):
    # TODO: implement
    out = ""
    pass


#####################################
########                     ########
#####################################
def get_content(toot):
    return _format_html(toot['content'])


#####################################
###### STYLE HELPERS           ######
#####################################
def _style_name_line(user, style1=[], style2=None, prefix='', suffix=''):
    # [prefix] 'Display Name' @user@instance [suffix]
    # <========style1         style2================>
    if not style2: style2 = style1
    return ' '.join(( stylize(prefix + _format_display_name(user), style1),
                      stylize(_format_username(user) + suffix, style2) ))


def _style_id_line(toot, style1=[], style2=None, style3=None, style4=None, prefix='', suffix=''):
    # [prefix] vis:X    ♺:0 ♥:0  id:76642  2017-04-21T18:48:34.000Z [suffix]
    #  <=======style1   style2   style3    style4=========================>
    # default all to style1 if not present
    if not style2: style2 = style1
    if not style3: style3 = style1
    if not style4: style4 = style1
    return '  '.join(( stylize(prefix + _format_visibility(toot), style1),
                       stylize(_format_counts(toot), style2),
                       stylize(_format_id(toot), style3),
                       stylize(_format_time(toot) + " (" + _format_time_relative(toot) + ")" + suffix, style4) ))


def _style_tootid_username(toot, style=[], prefix='', suffix=''):
    # [prefix] id:X from @user@instance [suffix]
    # <========style===========================>
    return stylize( prefix + _format_id(toot) + " from "
                    + _format_username(toot['account']) + suffix, style )


_pineapple = '\U0001f34d'  # can never have too many
#####################################
###### PRINTERS (USER-FACING)  ######
#####################################
def cprint(text, style, end="\n"):
    print(stylize(text, style), end=end)


def _print_name_line_solid(user, style=[], end='\n'):
    print( _indent + _style_name_line(user, style), end )
    return


def _print_id_line_solid(toot, style=[], end='\n'):
    print( _indent + _style_id_line(toot, style), end )
    return


def _print_media_list(toot, style=[]):
    # is even there are some?
    if not toot['media_attachments']: return
    out = []
    nsfw = _format_nsfw(toot)
    for thing in toot['media_attachments']:
        # TODO: may actually want thing['remote_url']
        out.append(str(_indent+_indent+nsfw+" "+thing['type']+": "+thing['url']))
    cprint('\n'.join(out), fg('magenta'))


def printProfiles():
    """Prints existing profile names in a sorted list."""
    # TODO: make them nice columns
    from .toot_utils import get_active_profile, get_known_profiles

    active = get_active_profile()
    inactiveprofiles = get_known_profiles()
    inactiveprofiles.sort()
    styledprofs = []
    for prof in inactiveprofiles:
        if prof == active:
            styledprofs.append(stylize("*"+active, fg('red')))
        else:
            styledprofs.append(stylize(prof, fg('blue')))
    print(_indent + ' '.join(styledprofs))
    return


def printHistoryToot(toot):
    """Prints toot nicely with hardcoded colors."""
    # Prints individual toot/tooter info
    print( _indent + _style_name_line(toot['account'], fg('green'), fg('yellow')) )
    print( _indent + _style_id_line(toot, fg('blue'), fg('cyan'), fg('red'), attr('dim')) )
    if toot['spoiler_text']:
        cprint(_indent + _format_spoiler(toot), fg('red'))
    content = get_content(toot)
    print(content + "\n")
    _print_media_list(toot)


def printTimelineToot(toot):
    """Prints toot nicely with randomized username coloring."""
    from .toot_utils import get_active_mastodon
    mastodon = get_active_mastodon()
    # Prints individual toot/tooter info
    print( _indent + _style_name_line(toot['account'], fg(random.choice(COLORS))) )
    print( _indent + _style_id_line(toot, fg('blue'), fg('cyan'), fg('red'), attr('dim')) )
    content = get_content(toot)

    # boosted toots
    if toot['reblog']:
        # all the interesting stuff is in here.  media/sensitive/spoiler are not
        # present in the wrapper toot.
        print(_indent + _style_tootid_username(toot['reblog'], fg('cyan'), prefix='Boosted ', suffix=':'))
        if toot['reblog']['spoiler_text']:
            cprint(_indent + _format_spoiler(toot['reblog']), fg('red'), end=":\n")
        content = _indent + get_content(toot['reblog'])
        cprint(content, fg('white'))
        _print_media_list(toot['reblog'])
        print("\n")
        return

    # reply
    elif toot['in_reply_to_id']:
        # get the reply to print context. spoiler text might have changed, etc
        # TODO: cut down to 1 line of context; user can use thread cmd if they need more
        repliedToot = mastodon.status(toot['in_reply_to_id'])
        print(_indent + _style_tootid_username(repliedToot, fg('blue'), prefix='Replied to ', suffix=':'))
        repliedTootContent = get_content(repliedToot)
        if repliedToot['spoiler_text']:
            cprint(_indent + _indent + _format_spoiler(repliedToot), fg('red'), end=": ")
        cprint(repliedTootContent, fg('blue'))
        _print_media_list(repliedToot)
        print("\n")

    # last but not least, spoilertext (CW)
    if toot['spoiler_text']:
        cprint(_indent + _format_spoiler(toot), fg('red'), end=":\n")
    cprint(content, fg('white'))
    _print_media_list(toot)
    print("\n")


def printNotification(note):
    """Prints colorcoded notifications."""
    # Mentions
    if note['type'] == 'mention':
        print(_indent + _style_name_line(note['account'], fg('magenta'), suffix=' mentioned you ======'))
        # TODO: this prints whole toot but we really only need the content
        printTimelineToot(note['status'])

    # Favorites
    elif note['type'] == 'favourite':
        print(_indent + _style_name_line(note['account'], fg('green'), suffix=' favorited your status:'))
        print(_indent + _style_id_line(note['status'], fg('green')))
        if note['status']['spoiler_text']:
            cprint(_indent + _format_spoiler(note['status']), fg('red'))
        cprint(get_content(note['status']), fg('green'))

    # Boosts
    elif note['type'] == 'reblog':
        print(_indent + _style_name_line(note['account'], fg('yellow'), suffix=' boosted your toot:'))
        print(_indent + _style_id_line(note['status'], fg('yellow')))
        if note['status']['spoiler_text']:
            cprint(_indent + _format_spoiler(note['status']), fg('red'))
        cprint(get_content(note['status']), fg('yellow'))

    # Follows
    elif note['type'] == 'follow':
        print(_indent + _style_name_line(note['account'], fg('red'), suffix=' followed you!'))

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
    """Prints a list of users in an abbreviated format."""
    for user in users:
        if not user: continue
        printUserShort(user)


def print_error(msg):
    """Prints an error message in bold red."""
    cprint(msg, fg('red')+attr('bold'))



__all__ = [ 'cprint',
            'get_content',
            'printProfiles',
            'printHistoryToot',
            'printTimelineToot',
            'printNotification',
            'printUser',
            'printUserShort',
            'printUsersShort',
            'print_error' ]

