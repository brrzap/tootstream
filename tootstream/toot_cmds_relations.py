import click
from mastodon import Mastodon
from colored import fg, attr, stylize
from .toot_click import TootStreamCmd, TootStreamGroup, CONTEXT_SETTINGS
from .toot_utils import *
from .toot_print import *


#####################################
###### FOLLOWER MANAGEMENT CMDS #####
#####################################
@click.group(     'follow', short_help='follow list|add|remove|following|requests',
                  cls=TootStreamGroup,
                  context_settings=CONTEXT_SETTINGS,
                  invoke_without_command=True,
                  no_args_is_help=True,
                  options_metavar='',
                  subcommand_metavar='<command>' )
def _follow():
    """Follower management operations: list, add, remove, following,
    requests, accept, reject.

    \b
             add, remove:  displays or changes who you follow
               followers:  displays who follows you
               following:  displays who follows you
                requests:  displays who wants to follow you
                  accept:  accepts a follow request
                  reject:  rejects a follow request
    """
    # TODO: add `list` subcommand that will display all 3 lists as
    #       well as leaders/groupies/friends designations.
    # TODO: add full relation display mode (`detail` subcommand?)
    pass


@_follow.command( 'help', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='get help for a command' )
@click.argument('cmd', metavar='<cmd>', required=False, default=None)
def follow_help(cmd):
    """Get details on how to use a command."""
    ctx = click.get_current_context()
    if not cmd is None:
        c = _follow.get_command(ctx, cmd)
        click.echo(c.get_help(ctx))
        return
    click.echo(_follow.get_help(ctx))


@_follow.command(    'followers', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='list who follows you' )
def follow_followers():
    """Lists users who follow you."""
    mastodon = get_active_mastodon()
    user = mastodon.account_verify_credentials()
    users = mastodon.account_followers(user['id'])
    if not users:
        cprint("  You're safe!  There's nobody following you", fg('red'))
    else:
        cprint("  People who follow you (" + str(len(users)) + "):", fg('magenta'))
        printUsersShortShort(users)
_follow.add_command(follow_followers, 'f-ers')


@_follow.command(    'following', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='list who you follow' )
def follow_following():
    """Lists users you follow."""
    mastodon = get_active_mastodon()
    user = mastodon.account_verify_credentials()
    users = mastodon.account_following(user['id'])
    if not users:
        cprint("  You aren't following anyone", fg('red'))
    else:
        cprint("  People you follow (" + str(len(users)) + "):", fg('magenta'))
        printUsersShortShort(users)
_follow.add_command(follow_following, 'f-ing')


@_follow.command(    'requests', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='list requests to follow you' )
def follow_requests():
    """Lists your incoming follow requests."""
    mastodon = get_active_mastodon()
    users = mastodon.follow_requests()
    if not users:
        cprint("  You have no incoming requests", fg('red'))
    else:
        cprint("  These users want to follow you:", fg('magenta'))
        printUsersShortShort(users)
        cprint("  run 'accept <id>' to accept", fg('magenta'))
        cprint("   or 'reject <id>' to reject", fg('magenta'))
_follow.add_command(follow_requests, 'req')


@_follow.command(    'follow', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='follow a user' )
@click.argument('username', metavar='<user>')
def follow_follow(username):
    """Follows an account by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShortShort(userid)
    elif userid == -1:
        cprint("  username not found", fg('red'))
    else:
        try:
            relations = mastodon.account_follow(userid)
            if relations['following']:
                cprint("  user " + str(userid) + " is now followed", fg('blue'))
        except:
            cprint("  ... well, it *looked* like it was working ...", fg('red'))
#aliases
_follow.add_command(follow_follow, 'add')
_follow.add_command(follow_follow, 'f')


@_follow.command(    'unfollow', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='unfollow a user' )
@click.argument('username', metavar='<user>')
def follow_unfollow(username):
    """Unfollows an account by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShortShort(userid)
    elif userid == -1:
        cprint("  username not found", fg('red'))
    else:
        try:
            relations = mastodon.account_unfollow(userid)
            if not relations['following']:
                cprint("  user " + str(userid) + " is now unfollowed", fg('blue'))
        except:
            cprint("  ... well, it *looked* like it was working ...", fg('red'))
#aliases
_follow.add_command(follow_unfollow, 'rm')
_follow.add_command(follow_unfollow, 'remove')
_follow.add_command(follow_unfollow, 'unf')


@_follow.command(    'accept', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='accept a follow request' )
@click.argument('username', metavar='<user>')
def follow_accept(username):
    """Accepts a user's follow request by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShortShort(userid)
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
#aliases
_follow.add_command(follow_accept, 'ok')
_follow.add_command(follow_accept, 'f-yeh')


@_follow.command(    'reject', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='reject a follow request' )
@click.argument('username', metavar='<user>')
def follow_reject(username):
    """Rejects a user's follow request by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShortShort(userid)
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
#aliases
_follow.add_command(follow_reject, 'no')
_follow.add_command(follow_reject, 'f-no')


#####################################
####### BLOCK MANAGEMENT CMDS #######
#####################################
@click.group(     'block', short_help='block list|add|remove',
                  cls=TootStreamGroup,
                  context_settings=CONTEXT_SETTINGS,
                  invoke_without_command=True,
                  no_args_is_help=True,
                  options_metavar='',
                  subcommand_metavar='<command>' )
def _block():
    """Block list management: list, add, remove."""
    pass


@_block.command(  'help', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='get help for a command' )
@click.argument('cmd', metavar='<cmd>', required=False, default=None)
def block_help(cmd):
    """Get details on how to use a command."""
    ctx = click.get_current_context()
    if not cmd is None:
        c = _block.get_command(ctx, cmd)
        click.echo(c.get_help(ctx))
        return
    click.echo(_block.get_help(ctx))


@_block.command(     'list', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='list users you block' )
def block_list():
    """Lists users you have blocked."""
    mastodon = get_active_mastodon()
    users = mastodon.blocks()
    if not users:
        cprint("  You haven't blocked anyone (... yet)", fg('red'))
    else:
        cprint("  You have blocked:", fg('magenta'))
        printUsersShortShort(users)
#aliases
_block.add_command(block_list, 'l')
_block.add_command(block_list, 'show')


@_block.command(     'block', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='block a user' )
@click.argument('username', metavar='<user>')
def block_add(username):
    """Blocks a user by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShortShort(userid)
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
_block.add_command(block_add, 'bl')
_block.add_command(block_add, 'add')


@_block.command(     'unblock', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='unblock a user' )
@click.argument('username', metavar='<user>')
def block_remove(username):
    """Unblocks a user by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShortShort(userid)
    elif userid == -1:
        cprint("  username not found", fg('red'))
    else:
        try:
            relations = mastodon.account_unblock(userid)
            if not relations['blocking']:
                cprint("  user " + str(userid) + " is now unblocked", fg('blue'))
        except:
            cprint("  ... well, it *looked* like it was working ...", fg('red'))
#aliases
_block.add_command(block_remove, 'rm')
_block.add_command(block_remove, 'remove')
_block.add_command(block_remove, 'unbl')


#####################################
######## MUTE MANAGEMENT CMDS #######
#####################################
@click.group(     'mute', short_help='mute list|add|remove',
                  cls=TootStreamGroup,
                  context_settings=CONTEXT_SETTINGS,
                  invoke_without_command=True,
                  no_args_is_help=True,
                  options_metavar='',
                  subcommand_metavar='<command>' )
def _mute():
    """Mute list management: list, add, remove."""
    pass


@_mute.command(   'help', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='get help for a command' )
@click.argument('cmd', metavar='<cmd>', required=False, default=None)
def mute_help(cmd):
    """Get details on how to use a command."""
    ctx = click.get_current_context()
    if not cmd is None:
        c = _mute.get_command(ctx, cmd)
        click.echo(c.get_help(ctx))
        return
    click.echo(_mute.get_help(ctx))


@_mute.command(      'list', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='list users you mute' )
def mute_list():
    """Lists users you have muted."""
    mastodon = get_active_mastodon()
    users = mastodon.mutes()
    if not users:
        cprint("  You haven't muted anyone (... yet)", fg('red'))
    else:
        cprint("  You have muted:", fg('magenta'))
        printUsersShortShort(users)
#aliases
_mute.add_command(mute_list, 'l')
_mute.add_command(mute_list, 'show')


@_mute.command(      'mute', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='mute a user' )
@click.argument('username', metavar='<user>')
def mute_add(username):
    """Mutes a user by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShortShort(userid)
    elif userid == -1:
        cprint("  username not found", fg('red'))
    else:
        try:
            relations = mastodon.account_mute(userid)
            if relations['muting']:
                cprint("  user " + str(userid) + " is now muted", fg('blue'))
        except:
            cprint("  ... well, it *looked* like it was working ...", fg('red'))
#aliases
_mute.add_command(mute_add, 'm')
_mute.add_command(mute_add, 'add')


@_mute.command(      'unmute', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='unmute a user' )
@click.argument('username', metavar='<user>')
def mute_remove(username):
    """Unmutes a user by username or id."""
    mastodon = get_active_mastodon()
    userid = get_userid(username)
    if isinstance(userid, list):
        cprint("  multiple matches found:", fg('red'))
        printUsersShortShort(userid)
    elif userid == -1:
        cprint("  username not found", fg('red'))
    else:
        try:
            relations = mastodon.account_unmute(userid)
            if not relations['muting']:
                cprint("  user " + str(userid) + " is now unmuted", fg('blue'))
        except:
            cprint("  ... well, it *looked* like it was working ...", fg('red'))
#aliases
_mute.add_command(mute_remove, 'rm')
_mute.add_command(mute_remove, 'remove')
_mute.add_command(mute_remove, 'unm')


