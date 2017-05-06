#!/usr/bin/env python3

import os.path
import click
import sys
from tootstream import *
from tootstream.toot_click import *
from tootstream.toot_utils import *
from tootstream.toot_print import *
from tootstream.toot_listener import *
from mastodon import Mastodon
from colored import fg, attr, stylize
from prompt_toolkit.shortcuts import prompt

#####################################
######## UTILITY FUNCTIONS # ########
#####################################
# see tootstream.toot_util module

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

    unimplemented: 2FA, direct message sending, get/set account options
    """
    pass


@_tootstream.command(cls=TootStreamCmd, hidden=True)
def tsrepl():
    """REPL overloader for click-repl."""

    from tootstream.toot_click import ts_prompt_kwargs
    repl( click.get_current_context(),
          prompt_kwargs=ts_prompt_kwargs,
          allow_secondary_prompt=True )


@_tootstream.command( 'help', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='get help for a command' )
@click.argument('cmd', metavar='<cmd>', required=False, default=None)
def help(cmd):
    """Get details on how to use a command."""
    ctx = click.get_current_context()
    if not cmd is None:
        c = _tootstream.get_command(ctx, cmd)
        if not c:
            click.echo('"{}": unknown command'.format(cmd))
        else:
            click.echo(c.get_help(ctx))
        return
    click.echo(_tootstream.get_help(ctx))


# callback helper
def _ts_filecheck(filename):
    # takes a filename, expands, tests for existence and readability
    # returns expanded path or None
    fnm = os.path.expanduser(filename)
    if os.path.exists(fnm) and os.access(fnm, os.R_OK):
        return fnm
    return None


# callback for media option
def _ts_option_filecheck_list_cb(ctx, param, value):
    # takes a list of filenames from arguments
    # expands paths, tests existence and readability
    # aborts with error if tests fail
    #print("DEBUG: ", str(param), str(param.name), str(value), str(ctx))
    if value is None: return None
    if len(value) > 4:
        print_error("error: only 4 attachments allowed")
        ctx.abort()
    v = []
    error = False
    for val in value:
        f = _ts_filecheck(val)
        if f is None:
            print_error("error: %s not readable" % val)
            ctx.abort()
        v.append(f)
    return v


@_tootstream.command( 'toot', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='post a toot' )
@click.option( '--add-media', '-m', 'media', metavar='<file>',
               required=False, default=None,
               multiple=True,
               callback=_ts_option_filecheck_list_cb,
               type=click.Path(),
               help='attach a file to your post (up to 4)' )
@click.option( '--nsfw', '-n', is_flag=True,
               help='mark attachments NSFW' )
@click.option( '--spoiler', '--cw', '-s', 'spoiler', metavar='<string>',
               required=False, default=None,
               help='a string to be shown before hidden content' )
@click.option( '--vis', '-v', 'vis', metavar='<>',
               # TODO: can we get current account setting from API? make that default
               type=click.Choice(['acct', 'p', 'public', 'u', 'unlisted', 'pr', 'private']),
               default='acct',
               # TODO: direct not supported: https://github.com/halcy/Mastodon.py/issues/41
               #type=click.Choice(['acct', 'p', 'public', 'u', 'unlisted', 'pr', 'private', 'd', 'direct']),
               help='post visibility (public, unlisted, private, direct)' )
@click.option( '--append', '-a', metavar='<file>',
               required=False, default=None,
               multiple=True,
               callback=_ts_option_filecheck_list_cb,
               type=click.Path(),
               help='read post text from a file' )
@click.argument('text', nargs=-1, metavar='<text>')
def toot(text, media, nsfw, spoiler, vis, append):
    """Publish a toot. ex: 'toot Hello World' will publish 'Hello World'.

    \b
      -m, --add-media <file>         attach a media file to the post
                                       (repeat to attach up to 4 files)
      -n, --nsfw                     mark attachments as sensitive
      -v, --vis <p|u|pr>             set post visibility to public/unlisted/private
      -s, --cw, --spoiler <string>   set spoiler text
      -a, --append <file>            read post text from a file (not yet implemented)
    """
    #print("DEBUG: "+' '.join(( "m:"+str(media), "n:"+str(nsfw), "cw:'"+str(spoiler)+"'", "v:"+str(vis), "ap:"+str(append), "t:"+str(text) )))

    if not text and not append:
        print_error("error: cowardly refusing to post an empty post")
        return
    if not text and append:
        print_error("error: posting text from file is currently unimplemented")
        return

    # TODO: verify 'acct' setting is right -- Mastodon.py uses this as account-default setting?
    # convert user-friendly shortcuts
    if vis == 'acct': vis = ''
    elif vis == 'p':  vis = 'public'
    elif vis == 'u':  vis = 'unlisted'
    elif vis == 'pr': vis = 'private'
    #elif vis == 'd':  vis = 'direct'
    post_text = ' '.join(text)
    mpost = []
    mastodon = get_active_mastodon()

    # rule: if no media don't set sensitive.
    if not media:
        nsfw = False
    else:
        for m in media:
            try:
                mpost.append( mastodon.media_post(m) )
            except:
                print_error("error: API error uploading %s" % m)
                return
        assert len(media) == len(mpost)


    resp = mastodon.status_post( post_text, media_ids=mpost, sensitive=nsfw,
                                 visibility=vis, spoiler_text=spoiler )

    printTootSummary(resp)
# aliases
_tootstream.add_command(toot, 't')


@_tootstream.command( 'reply', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='reply to a toot' )
@click.option( '--add-media', '-m', 'media', metavar='<file>',
               required=False, default=None,
               multiple=True,
               callback=_ts_option_filecheck_list_cb,
               type=click.Path(),
               help='attach a file to your post (up to 4)' )
@click.option( '--nsfw', '-n', is_flag=True,
               help='mark attachments NSFW' )
@click.option( '--spoiler', '--cw', '-s', 'spoiler', metavar='<string>',
               required=False, default=None,
               help='a string to be shown before hidden content' )
@click.option( '--nospoiler', '--nocw', 'nospoiler', is_flag=True,
               help='don\'t use original toot\'s spoiler text' )
@click.option( '--vis', '-v', 'vis', metavar='<>',
               # TODO: can we get current account setting from API? make that default
               type=click.Choice(['p', 'public', 'u', 'unlisted', 'pr', 'private', 'orig']),
               default='orig', # follow the parent's setting
               # TODO: direct not supported: https://github.com/halcy/Mastodon.py/issues/41
               #type=click.Choice(['p', 'public', 'u', 'unlisted', 'pr', 'private', 'd', 'direct', 'asorig']),
               help='post visibility (public, unlisted, private, direct)' )
@click.option( '--append', '-a', metavar='<file>',
               required=False, default=None,
               multiple=True,
               callback=_ts_option_filecheck_list_cb,
               type=click.Path(),
               help='read post text from a file' )
@click.argument('tootid', metavar='<id>')
@click.argument('text', nargs=-1, metavar='<text>')
def reply(tootid, text, media, nsfw, spoiler, nospoiler, vis, append):
    """Reply to a toot by ID.  Defaults to the original toot's visibility and spoiler text.

    \b
      -m, --add-media <file>         attach a media file to the post
                                       (repeat to attach up to 4 files)
      -n, --nsfw                     mark attachments as sensitive
      -v, --vis <p|u|pr>             change post visibility to public/unlisted/private
      -s, --cw, --spoiler <string>   change spoiler text
          --nocw, --nospoiler        don't use original toot's spoiler text
      -a, --append <file>            read post text from a file (not yet implemented)
    """
    #print("DEBUG: "+' '.join(( "m:"+str(media), "n:"+str(nsfw), "cw:'"+str(spoiler)+"'", "v:"+str(vis), "ap:"+str(append), "t:"+str(text) )))

    if not text and not append:
        print_error("error: cowardly refusing to post an empty post")
        return
    if not text and append:
        print_error("error: posting text from file is currently unimplemented")
        return
    mastodon = get_active_mastodon()
    parent_toot = mastodon.status(tootid)

    #print("DEBUG: "+' '.join(( "P_vis:"+str(parent_toot['visibility']), "P_cw:'"+str(parent_toot['spoiler_text'])+"'" )))

    # default vis to parent's
    if vis == 'orig': vis = parent_toot['visibility']
    # convert user-friendly shortcuts
    elif vis == 'p':  vis = 'public'
    elif vis == 'u':  vis = 'unlisted'
    elif vis == 'pr': vis = 'private'
    #elif vis == 'd':  vis = 'direct'

    # default spoiler to parent's unless nospoiler is set
    if nospoiler:
        spoiler = ''
    elif not spoiler:
        spoiler = parent_toot['spoiler_text']
    reply_text = ' '.join(text)
    mpost = []

    #print("DEBUG: "+' '.join(( "m:"+str(media), "n:"+str(nsfw), "cw:'"+str(spoiler)+"'", "v:"+str(vis), "ap:"+str(append), "t:"+str(text) )))

    # rule: if no media don't set sensitive.
    if not media:
        nsfw = False
    else:
        for m in media:
            try:
                mpost.append( mastodon.media_post(m) )
            except:
                print_error("error: API error uploading %s" % m)
                return
        assert len(media) == len(mpost)

    mentions = [i['acct'] for i in parent_toot['mentions']]
    mentions.append(parent_toot['account']['acct'])
    mentions = ["@%s" % i for i in list(set(mentions))] # Remove dups
    mentions = ' '.join(mentions)

    post_text = ' '.join(( mentions, reply_text ))

    resp = mastodon.status_post( post_text, media_ids=mpost, sensitive=nsfw,
                                 in_reply_to_id=int(tootid),
                                 visibility=vis, spoiler_text=spoiler )

    printTootSummary(resp)
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


@_tootstream.command( 'faves', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='show your favourites' )
def faves():
    """Displays posts you've favourited."""
    mastodon = get_active_mastodon()
    for toot in reversed(mastodon.favourites()):
        printTimelineToot(toot)
# aliases


### TODO: this is mentioned in Mastodon.py but doesn't
### seem to be a real API endpoint.  leaving this here
### for consideration until i can dig into the API docs.
###
#@_tootstream.command( 'mentions', options_metavar='',
#                     cls=TootStreamCmd,
#                     short_help='show your mentions' )
#def mentions():
#    """Displays posts mentioning you."""
#    mastodon = get_active_mastodon()
#    for toot in reversed(mastodon.timeline_mentions()):
#        printTimelineToot(toot)
## aliases


@_tootstream.command( 'timeline', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='show a timeline of toots from a user' )
@click.argument('username', metavar='<user>')
def timeline(username):
    """Displays toots you've tooted."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShort(userid)
    elif userid == -1:
        cprint("  username not found", fg('red'))
    else:
        for toot in reversed(mastodon.account_statuses(userid)):
            printTimelineToot(toot)
# aliases
_tootstream.add_command(timeline, 'tootsfrom')


@_tootstream.command( 'mine', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='show your toots' )
def mine():
    """Displays toots you've tooted."""
    mastodon = get_active_mastodon()
    # TODO: user's creds should really be stored somewhere
    thatsme = mastodon.account_verify_credentials()
    # no specific api for user's own toot timeline
    click.get_current_context().invoke(timeline, username=thatsme['id'])
# aliases
_tootstream.add_command(mine, 'mytoots')


@_tootstream.command( 'thread', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='thread history of a toot' )
# TODO: option to output to file (`--dump`, `-o`?)
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
        cprint("  No additional history to show.", fg('blue'))
        # fall through and print the current toot anyway

    # Print older toots
    if (len(dicts['ancestors']) > 0):
        cprint("  =========   " + "↓↓↓↓↓↓ Older Toots Begin ↓↓↓↓↓↓" + "   ========", fg('red'))
        for oldToot in dicts['ancestors']:
            printHistoryToot(oldToot)
        cprint("  =========   " + "↑↑↑↑↑↑ Older Toots End ↑↑↑↑↑↑" + "   ========", fg('red'))

    # Print current toot
    currentToot = mastodon.status(tootid)
    printTimelineToot(currentToot)

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
    # TODO: extract follow notifications & print separately?
    #       consolidate so notifs on same toot are all together?
    for note in reversed(mastodon.notifications()):
        printNotification(note)
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
    # if user includes # prefix, remove it
    if tag[0] == "#": tag = tag[1:]
    for toot in reversed(mastodon.timeline_hashtag(tag)):
        printTimelineToot(toot)
# aliases
_tootstream.add_command(whatis, 'what')


@_tootstream.command( 'search', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='search #tag|@user' )
@click.argument('query', metavar='<query>')
def search(query):
    """Search for a #tag or @user.

    \b
       search #tag         # performs a hashtag search for "tag"
       search @user        # performs a user search for "user"
       search thing        # performs a general search; can return users, tags, toots
       search http://other.mastodon.instance/full/url/to/user/or/toot
                           # can get a local id for remote user or toot
    """
    mastodon = get_active_mastodon()
    prefix = query[0]
    # @ user search
    if prefix == "@" and not query[1:] == "":
        click.get_current_context().invoke(whois, username=query)
    # # hashtag search
    elif prefix == "#" and not query[1:] == "":
        click.get_current_context().invoke(whatis, tag=query)
    else:
        stuff = mastodon.search(query)
        users = None
        toots = None
        tags = None
        if stuff:
            users = stuff['accounts']
            toots = stuff['statuses']
            tags = stuff['hashtags']

        summary = ', '.join( ' '.join(( str(len(x[0])), x[1]))             # format as "N label1, ..."
                                for x in zip( [users, toots, tags],        #   for these lists
                                              ["users", "toots", "tags"])  #   with these labels
                                if x[0] and len(x[0])>0 )                  #   skipping empty lists
        print_ui_msg("  Search: {} found {}".format(query, summary))

        # TODO: nice columnized output for large results
        if users and len(users)>0:
            print_ui_msg("\n  User results:")
            if len(users)<=2:
                printUsersShort(users)
            else:
                # the short short version
                printUsersShortShort(users)

        if toots and len(toots)>0:
            print_ui_msg("\n  Toot results:")
            if len(toots)<=2:
                for toot in toots:
                    printTootSummary(toot)
            else:
                # the short short version
                printTootsShortShort(toots)

        if tags and len(tags)>0:
            print_ui_msg("\n  Tag results:\n    {}".format(' '.join(tags)))

        print("")
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
_tootstream.add_command(info, 'whoami')


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


@_tootstream.command( 'raw', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='raw data about a user or toot' )
@click.option( '--user', '-u', flag_value='user',
               help='argument is a userid' )
#@click.option( '--get', '-g', flag_value='get',
#               help='argument is an API enpoint' )
@click.argument('thisid', metavar='<id>')
def raw(thisid, user):
    """Displays the API's view of a toot or user.  Assumes
    the argument is a tootID unless it begins with @ or /.

    \b
       -u, --user    force treat argument as a user

    \b
    Ex:   raw 100                   # gets toot with ID 100
          raw @foo                  # gets user foo
          raw -u 100                # gets user with ID 100
          raw /api/v1/accounts/100  # gets user with ID 100
    """
    #  -g, --get    argument is an API endpoint (ie /api/v1/foo)
    mastodon = get_active_mastodon()

    response = None
    if user or thisid[:1] == "@":
        userid = get_userid(thisid)
        response = mastodon.account(userid)
    elif thisid[:1] == "/":
        # undocumented easter egg. have fun.
        try:
            response = mastodon._Mastodon__api_request('GET', thisid)
        except:
            pass
    else:
        try:
            #tootid = IDS.to_global(tootid)
            thisid = int(thisid)
        except:
            return print_error("are you sure '" + str(thisid) + "' is a real tootID?")
        response = mastodon.status(thisid)

    if response:
        # TODO: add --summarize and/or --prettify flags
        #       to do something other than barf python dicts
        print(str(response))
#aliases


import tootstream.toot_cmds_settings
import tootstream.toot_cmds_relations
_tootstream.add_command(tootstream.toot_cmds_settings._profile)
_tootstream.add_command(tootstream.toot_cmds_settings._listen)
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
@click.option( '--notifications', '-n', metavar='', default=False, is_flag=True,
               help='Enable desktop notifications (experimental)' )
def main(instance, email, password, config, profile, notifications):
    configpath = os.path.expanduser(config)
    if os.path.isfile(configpath) and not os.access(configpath, os.W_OK):
        # warn the user before they're asked for input
        cprint("Config file does not appear to be writable: "+configpath, fg('red'))

    set_configfile(configpath)
    cfg = parse_config()
    if not cfg.has_section(profile):
        cfg.add_section(profile)

    instance, client_id, client_secret, token = parse_or_input_profile(profile, instance, email, password)
    if not token:
        print_error("Could not log you in.  Please try again later.")
        sys.exit(1)


    mastodon = Mastodon(
        client_id=client_id,
        client_secret=client_secret,
        access_token=token,
        api_base_url="https://" + instance)

    if notifications:
        set_notifications()
        kick_new_process( mastodon.user_stream, TootDesktopNotifications(profile) )

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
    set_user(user)

    # setup repr
    ctx = _tootstream.make_context('tootstreamShell', [], parent=click.get_current_context())
    ctx.invoke(tsrepl)

    print("Goodbye!")


if __name__ == '__main__':
    main()
