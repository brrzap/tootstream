import click
import random
import re
import arrow
from mastodon import Mastodon
from colored import fg, attr, stylize
from textwrap import indent as tw_indent
from wcwidth import wcswidth
from .toot_parser import *
import logging

logger = logging.getLogger('ts.print')
#####################################
######## CONSTANTS           ########
#####################################
COLORS = list(range(19,231))
GLYPHS = {
    'fave':          '♥',
    'boost':         '♺',
    'pineapple':     '\U0001f34d', # pineapple
    'elephant':      '\U0001f418', #
    'toots':         '\U0001f4ea', # mailbox (for toot counts)
    # keys matching possible values for toot['visibility']
    'public':        '\U0001f30e', # globe
    'unlisted':      '\U0001f47b', # ghost '\U0001f47b' ... mute '\U0001f507' ??
    'private':       '\U0001f512', # lock
    'direct':        '\U0001f4e7', # envelopes: '\U0001f4e7' '\U0001f4e9' '\U0001f48c' '\U00002709'
    # keys matching keys in user{}
    'locked':        '\U0001f512', # lock (masto web uses U+F023 from FontAwesome)
    # keys matching keys in toot{}
    'favourited':    '\U00002605', # star '\U0001f31f' '\U00002b50'
    'reblogged':     '\U0001f1e7', # regional-B '\U0001f1e7'? reuse ♺?
    # keys matching keys in relationship{}
    'followed_by':   '\U0001f43e', # pawprints '\U0001f43e'
    'following':     '\U0001f463', # footprints '\U0001f463'
    'blocking':      '\U0000274c', # thumbsdown '\U0001f44e', big X '\U0000274c', stopsign '\U0001f6d1'
    'muting':        '\U0001f6ab', # mute-spkr '\U0001f507', mute-bell '\U0001f515', prohibited '\U0001f6ab'
    'requested':     '\U00002753', # hourglass '\U0000231b', question '\U00002753'
    # catchall
    'unknown':       '\U0001f34d' }

_indent = "  "
_ts_wrapper = TootWrapper( width=75, tabsize=4,
                           initial_indent=_indent, subsequent_indent=_indent,
                           #replace_whitespace=False,
                           drop_whitespace=False,
                           break_long_words=False )
toot_parser = TootParser(indent='  ', width=75)
#_current_width = 0
#_current_height = 0
(_current_width, _current_height) = click.get_terminal_size()
random.seed()


### text wrapping
#def _format_paragraph(text):
#    width = click.get_terminal_size()[0]
#    print("width is "+str(width))
#    return text
#    return click.wrap_text(text, width=width-5, initial_indent=_indent, subsequent_indent=_indent, preserve_paragraphs=True)
#    #return click.wrap_text(text, width=width-5, initial_indent=_indent, subsequent_indent=_indent)

#####################################
######## STRING UTILITIES    ########
#####################################
### handy string collapser
def collapse(text):
    """Return a string with all whitespace sequences replaced by single spaces."""
    #text = re.sub(r'\s+', ' ', text)                # all whitespace
    text = re.sub(r'[ \t\n\r\f\v\xa0]+', ' ', text)     # ascii whitespace + nbsp (preserve unicode)
    return text


def wcs_ljust(text, width, fill=' '):
    """Wide-character-aware left-justify.  Uses wcswidth to guess correct spacing for wide characters.
    Returns text unchanged if larger than the supplied field width.

    width: field width to fill
    fill: string to repeat as filler"""
    if wcswidth(text)>=width: return text
    out = text + fill*((width-wcswidth(text))//wcswidth(fill))
    return out


def wcs_rjust(text, width, fill=' '):
    """Wide-character-aware right-justify.  Uses wcswidth to guess correct spacing for wide characters.
    Returns text unchanged if larger than the supplied field width.

    width: field width to fill
    fill: string to repeat as filler"""
    if wcswidth(text)>=width: return text
    out = fill*((width-wcswidth(text))//wcswidth(fill)) + text
    return out

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
        return "@" + user['acct'] + " " + GLYPHS['locked']
    return "@" + user['acct']

def _format_usercounts(user):
    return ''.join(( GLYPHS['toots'], " :", str(user['statuses_count']), " ",
                     GLYPHS['following'], " :", str(user['following_count']), " ",
                     GLYPHS['followed_by'], " :", str(user['followers_count']) ))


### Toot dict formatting
def _format_boost_count(toot):
    return GLYPHS['boost'] + ":" + str(toot['reblogs_count'])

def _format_faves_count(toot):
    return GLYPHS['fave'] + ":" + str(toot['favourites_count'])

def _format_counts(toot):
    return _format_boost_count(toot) + " " + _format_faves_count(toot)

def _format_id(tootoruser):
    #toot_id = str(IDS.to_local(toot['id']))
    return "id:" + str(tootoruser['id'])

def _format_time(toot):
    return arrow.get(toot['created_at']).strftime('%Y.%m.%d %H:%M %Z')

def _format_time_relative(toot):
    return arrow.get(toot['created_at']).humanize()

def _format_spoiler(toot):
    if not toot['spoiler_text']: return ''
    return "[CW: " + toot['spoiler_text'] + "]"

def _format_spoiler_trimmed(toot):
    (width, _) = click.get_terminal_size()
    trimlen = width*2//7  # very scientific
    return _ts_wrapper.shorten(_format_spoiler(toot), width=trimlen)

def _format_visibility(toot):
    return "vis:" + GLYPHS[toot['visibility']]

def _format_acted(toot):
    # has this user favorited or boosted this toot already?
    # seeing some toot dicts without these keys, so use get()
    out = []
    if toot.get('favourited'): out.append( GLYPHS['favourited'] )
    if toot.get('reblogged'): out.append( GLYPHS['reblogged'] )
    return " "+' '.join(out)

def _format_app(toot):
    if toot.get('application') and toot.get('application').get('name'):
        return "via {} ".format(toot['application']['name'])
    return ''

def _format_nsfw(toot, prefix='[', suffix=']'):
    if not toot['sensitive']: return ''
    return "{}{}{}".format(prefix, "NSFW", suffix)


### Media dict formatting
def _format_media_summary(toot, prefix='[', suffix=']'):
    # [prefix]media:COUNT:NSFW[suffix]
    if not toot['media_attachments']: return None
    return ''.join(( prefix, "media:", str(len(toot['media_attachments'])),
                     _format_nsfw(toot, prefix=':', suffix=''), suffix ))

def _list_media(toot):
    # returns a list instead of a string
    # is even there are some?
    if not toot['media_attachments']: return None
    out = []
    nsfw = (_format_nsfw(toot)+" " if toot['sensitive'] else "")
    count = 1
    for thing in toot['media_attachments']:
        # TODO: may want to cut off any '?xxxxx' after a file extension
        if thing['text_url'] is not None:
            # generally the shortest if it exists
            out.append( ''.join(( nsfw, str(count), ": ", thing['type'], ": (t) ", str(thing['text_url']) )) )
        elif thing['remote_url'] is not None:
            # on originating server
            out.append( ''.join(( nsfw, str(count), ": ", thing['type'], ": (r) ", str(thing['remote_url']) )) )
        else:
            # thing['preview_url'] seems to be the same as this
            # use thing['url'] in case preview is ever a modified version
            out.append( ''.join(( nsfw, str(count), ": ", thing['type'], ": (l) ", str(thing['url']) )) )
        count += 1
    return out


#####################################
########                     ########
#####################################
def get_content(toot):
    return _format_html(toot['content'])

def get_content_trimmed(toot):
    (width, _) = click.get_terminal_size()
    trimlen = width*4//7  # very scientific
    return _ts_wrapper.shorten(collapse(get_content(toot)), trimlen)


#####################################
###### STYLE HELPERS           ######
#####################################
def _style_name_line(user, style1=[], style2=None, prefix='', suffix=''):
    # [prefix] 'Display Name' @user@instance [suffix]
    # <========style1         style2================>
    if not style2: style2 = style1
    return ' '.join(( stylize( prefix + _format_display_name(user), style1 ),
                      stylize( _format_username(user) + suffix, style2 ) ))


def _style_id_line(toot, style1=[], style2=None, style3=None, style4=None, prefix='', suffix=''):
    # [prefix] vis:X    ♺:0 ♥:0  id:76642  2017-04-21T18:48:34.000Z [suffix]
    #  <=======style1   style2   style3    style4=========================>
    # default all to style1 if not present
    if not style2: style2 = style1
    if not style3: style3 = style1
    if not style4: style4 = style1
    return '  '.join(( stylize( prefix + _format_visibility(toot), style1 ),
                       stylize( _format_counts(toot) + _format_acted(toot), style2 ),
                       stylize( _format_id(toot), style3 ),
                       stylize( _format_app(toot) + _format_time(toot) + " (" + _format_time_relative(toot) + ")" + suffix, style4) ))


def _style_tootid_username(toot, style=[], prefix='', suffix=''):
    # [prefix] id:X from @user@instance [suffix]
    # <========style===========================>
    return stylize( prefix + _format_id(toot) + " from "
                    + _format_username(toot['account']) + suffix, style )


def _style_media_summary(toot, style=[], prefix='', suffix=''):
    # [prefix][media:N:NSFW][suffix]
    # <========style===============>
    return stylize(prefix+_format_media_summary(toot)+suffix, style)


def _style_media_list(toot, style=[], prefix='', suffix=''):
    # [prefix] [NSFW] image: http://example.com/foo/bar/baz [suffix]
    # <========style===============================================>
    textin = _list_media(toot)
    out = []
    if not textin: return ''
    for line in textin:
        out.append(str(prefix + line + suffix))
    return stylize('\n'.join(out), style)


def _style_toot_summary_line(toot, style=[], ind=_indent):
    # [CW...]: content summary... [media:N:NSFW]
    content = stylize(get_content_trimmed(toot), style)
    if toot['spoiler_text']:
        content = "{}: {}".format( stylize(_format_spoiler_trimmed(toot), fg('red')), content )
    if toot['media_attachments']:
        content += _style_media_summary(toot, fg('magenta'))
    return content


def _style_toot_historytheme(toot, ind=_indent):
    out = []
    out.append( _style_name_line(toot['account'], fg('green'), fg('yellow')) )
    out.append( _style_id_line(toot, fg('blue'), fg('cyan'), fg('red'), attr('dim')) )
    if toot['spoiler_text']:
        out.append( stylize( '\n'.join(_ts_wrapper.wrap(_format_spoiler(toot))), fg('red')) )
    out.append( get_content(toot) )
    out.append( _style_media_list(toot, fg('magenta'), prefix=ind+ind) )
    for line in out:
        tw_indent(line, ind)
    return '\n'.join(out)


def stylize_rl(text, styles, reset=True):
    """conveniently styles your text as and resets ANSI codes at its end. readline-safe."""
    # problem: stylize doesn't add the escapes we need for readline.
    # see: https://github.com/dslackw/colored/issues/5
    # solution: localized tweak.
    C0_SOH = '\x01'  # nonprinting chars begin
    C0_STX = '\x02'  # nonprinting chars end
    terminator = "{}{}{}".format(C0_SOH, attr("reset"), C0_STX) if reset else ""
    return "{}{}{}{}{}".format(C0_SOH, "".join(styles), C0_STX, text, terminator)


def stylePrompt(username, profile, style1=[], style2=None, prefix='[', suffix=']: '):
    # [prefix]@username (profile)[suffix]
    #         <==style1 style2==>
    if not style2: style2 = style1
    # use stylize_rl() instead of stylize() for prompts. same arguments.
    return ''.join(( prefix, stylize_rl("@"+username, style1), " ",
                     stylize_rl("("+profile+")", style2), suffix ))


_pineapple = '\U0001f34d'  # can never have too many
#####################################
###### PRINTERS (USER-FACING)  ######
#####################################
def cprint(text, style, end="\n"):
    print(stylize(text, style), end=end)


def print_error(msg):
    """Prints an error message in bold red."""
    cprint(msg, fg('red')+attr('bold'))


def print_ui_msg(msg):
    """Prints a UI status message in blue."""
    cprint(msg, fg('blue'))


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
    # _style_toot_historytheme
    print( _indent + _style_name_line(toot['account'], fg('green'), fg('yellow')) )
    print( _indent + _style_id_line(toot, fg('blue'), fg('cyan'), fg('red'), attr('dim')) )
    if toot['spoiler_text']:
        cprint(_indent + _format_spoiler(toot), fg('red'))
    content = get_content(toot)
    print(content)
    if toot['media_attachments']:
        print(_style_media_list(toot, fg('magenta'), prefix=_indent))
    print("")


def printTootSummary(toot):
    """Short 4-line summary: name line, id line, spoiler/content line, media summary."""
    print( _indent + _style_name_line(toot['account'], fg(random.choice(COLORS))) )
    print( _indent + _style_id_line(toot, fg('blue'), fg('cyan'), fg('red'), attr('dim')) )
    print( _indent + _style_toot_summary_line(toot, fg('grey_78')) )
    print("")


def printTimelineToot(toot):
    """Prints toot nicely with randomized username coloring."""
    out = []
    # if it's a boost, only output header line from toot
    # then get other data from toot['reblog']
    if toot['reblog']:
        header = stylize("  Boosted by ", fg('yellow'))
        name = ' '.join(( _style_name_line(toot['account'], fg('blue')),
                          stylize("({}):".format(_format_id(toot)), fg('yellow')) ))
        out.append(header+name)
        toot = toot['reblog']

    # get the first two lines
    out += [ "  "+_style_name_line(toot['account'], fg(random.choice(COLORS))),
             "  "+_style_id_line(toot, fg('blue'), fg('cyan'), fg('red'), attr('dim')) ]

    if toot['in_reply_to_id']:
        out.append( stylize("  Replying to id:{}:".format(toot['in_reply_to_id']), fg('blue')) )

    if toot['spoiler_text'] != '':
        out.append( "  "+stylize(_format_spoiler(toot), fg('red')) )

    out.append( stylize(get_content(toot), fg('white')) )

    if toot['media_attachments']:
        out.append( _style_media_list(toot, fg('magenta'), prefix=_indent) )

    print( '\n'.join(out) )
    print()


def printNotification(note):
    """Prints colorcoded notifications."""
    # Mentions
    if note['type'] == 'mention':
        print(_indent + _style_name_line(note['account'], fg('magenta'), suffix=' mentioned you ======'))
        # TODO: this prints whole toot but we really only need the content
        print(_indent + _style_id_line(note['status'], fg('magenta')))
        print(_indent + _style_toot_summary_line(note['status'], fg('magenta')))

    # Favorites
    elif note['type'] == 'favourite':
        print(_indent + _style_name_line(note['account'], fg('green'), suffix=' favorited your status:'))
        print(_indent + _style_id_line(note['status'], fg('green')))
        print(_indent + _style_toot_summary_line(note['status'], fg('green')) )

    # Boosts
    elif note['type'] == 'reblog':
        print(_indent + _style_name_line(note['account'], fg('yellow'), suffix=' boosted your toot:'))
        print(_indent + _style_id_line(note['status'], fg('yellow')))
        print(_indent + _style_toot_summary_line(note['status'], fg('yellow')) )

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
    # use .get() since some keys may not always be present
    out = [ "",
            "  {} ({}): {}".format( _style_name_line(user, fg(random.choice(COLORS)), fg('spring_green_2b')),
                                    stylize( _format_id(user), fg('orange_red_1')),
                                    stylize( _format_usercounts(user), fg('cornflower_blue')) ),
            "    avatar: {}".format( stylize( (user.get('avatar') if user.get('avatar') else '[none]'), fg('steel_blue_1b')) ),
            "    url:    {}".format( stylize( (user.get('url') if user.get('url') else '[none]'), fg('steel_blue_1b')) ),
            "    joined: {}".format( stylize( ("{} ({})".format(_format_time(user), _format_time_relative(user)) if user.get('created_at') else '[none]'), fg('gold_3b')) ),
            "{}".format( stylize( (_format_html(user.get('note')) if user.get('note') else '[none]'), fg('sky_blue_1')) ),
            "" ]
    print( '\n'.join(out) )


def printUserShort(user):
    """Prints user data in an abbreviated 2-line format."""
    if not user: return
    cprint(_indent + _pineapple + " " + _format_username(user), fg('blue'), end=" ")
    cprint(_format_display_name(user), fg('cyan'))
    cprint(_indent + _indent + _format_id(user), fg('red'), end="  ")
    cprint(_format_usercounts(user), fg('blue'), end="  ")
    cprint(user['url'], fg('green'))


def printUsersShort(users):
    """Prints a list of users in an abbreviated format."""
    for user in users:
        if not user: continue
        printUserShort(user)


def printUsersShortShort(users):
    """Prints a list of users in compact columns."""
    if not users: return

    # TODO: smarter column size determinations
    #(width, _) = click.get_terminal_size()
    out = [ [_format_id(user), _format_username(user)] for user in users ]

    # how many columns? append extra entries to fill
    if len(users) % 2 != 0:
        out.append( [ "", "" ] )

    maxlen_id = max(len(row[0]) for row in out)
    maxlen_u = max(wcswidth(row[1]) for row in out)
    #maxwidth = maxlen_id+2+maxlen_u # 2 for "  " to space the columns

    out_l = out[:len(out)//2]
    out_r = out[len(out)//2:]
    for col_l, col_r in zip(out_l, out_r):
        print( _indent*2 + " ".join((
                    stylize( wcs_rjust(col_l[0], maxlen_id), fg('red') ),
                    stylize( wcs_ljust(col_l[1], maxlen_u), fg(random.choice(COLORS)) ),
                    stylize( wcs_rjust(col_r[0], maxlen_id), fg('red') ),
                    stylize( wcs_ljust(col_r[1], maxlen_u), fg(random.choice(COLORS)) ) )))

    return


def printTootsShortShort(toots):
    """Prints a list of toots in compact columns."""
    if not toots: return

    # TODO: smarter column size determinations
    #(width, _) = click.get_terminal_size()
    out = [ [_format_id(toot), _format_username(toot['account'])] for toot in toots ]

    # how many columns? append extra entries to fill
    if len(users) % 2 != 0:
        out.append( [ "", "" ] )

    maxlen_id = max(len(row[0]) for row in out)
    maxlen_u = max(wcswidth(row[1]) for row in out)
    #maxwidth = maxlen_id+6+maxlen_u # 6 for " from " to space the columns

    out_l = out[:len(out)//2]
    out_r = out[len(out)//2:]
    for col_l, col_r in zip(out_l, out_r):
        print( _indent*2 + " ".join((
                    stylize( wcs_rjust(col_l[0], maxlen_id), fg('red') ),
                    " from ",
                    stylize( wcs_ljust(col_l[1], maxlen_u), fg(random.choice(COLORS)) ),
                    " ",
                    stylize( wcs_rjust(col_r[0], maxlen_id), fg('red') ),
                    " from ",
                    stylize( wcs_ljust(col_r[1], maxlen_u), fg(random.choice(COLORS)) ) )))

    return


def printUserRelations(user, relation):
    # collect phrases for relation keys
    them    = [ ("follows you" if relation['followed_by'] else "doesn't follow you"),
                ("and has requested to follow you" if relation['requested'] else "") ]
    you     = [ ("are following" if relation['following'] else 'are not following'),
                ("are blocking" if relation['blocking'] else ''),
                ("are muting" if relation['muting'] else '') ]
    # sort out the empties and join
    themstr = ' '.join([x for x in them if x != ''])
    youstr  = ', '.join([x for x in you if x != ''])
    # and print
    print("  {} {} {}".format( stylize(_format_id(user), fg('red')),
                               stylize(_format_username(user), fg('blue')),
                               themstr ))
    print("      {} {}".format( stylize("you", fg('cyan')), youstr ))


def printServer(info):
    # atm, interesting keys are 'uri', 'title', 'description', 'email', 'version'
    # use .get() since some keys may not always be present
    out = [ "",
            "  server:  {}".format( stylize(info.get('uri'), fg(random.choice(COLORS))) ),
            "  title:   {}".format( stylize(info.get('title'), fg('orange_red_1')) ),
            "  version: {}".format( stylize(
                                (info.get('version') if info.get('version') else '[none]'), fg('gold_3b')) ),
            "  about:   {}".format( stylize(
                                (_format_html(info.get('description')) if info.get('description') else '[none]'), fg('sky_blue_1') )),
            "" ]
    print( '\n'.join(out) )


__all__ = [ 'cprint',
            'get_content',
            'get_content_trimmed',
            'stylePrompt',
            'printProfiles',
            'printHistoryToot',
            'printTimelineToot',
            'printTootSummary',
            'printNotification',
            'printUser',
            'printUserShort',
            'printUsersShort',
            'printUsersShortShort',
            'printTootsShortShort',
            'printUserRelations',
            'printServer',
            'print_error',
            'print_ui_msg' ]

