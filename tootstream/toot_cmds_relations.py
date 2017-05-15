import click
from mastodon import Mastodon
from colored import fg, attr, stylize
from .toot_click import TootArgument, TootStreamCmd, TootStreamGroup, CONTEXT_SETTINGS
from .toot_utils import *
from .toot_print import *
import logging

logger = logging.getLogger('ts.reltns')


#####################################
###### HELPER FUNCTIONS         #####
#####################################
def check_usernames(names):
    """Get userIDs for a list of names. Prints an error message and
    returns [] (empty list) if a 1:1 match is not found."""
    userids = [ get_userid(name) for name in names ]

    # check for problems and error out if found
    for userid, name in zip(userids, names):
        if isinstance(userid, list):
            cprint("  multiple matches found for {}:".format(name), fg('red'))
            printUsersShortShort(userid)
            return []
        elif userid == -1:
            cprint("  user not found: {}".format(name), fg('red'))
            return []

    return userids


#####################################
###### FOLLOWER MANAGEMENT CMDS #####
#####################################
@click.group(     'follow', short_help='follow list|add|remove|following|requests',
                  cls=TootStreamGroup,
                  context_settings=CONTEXT_SETTINGS,
                  invoke_without_command=True,
                  no_args_is_help=True,
                  options_metavar='',
                  subcommand_metavar='<cmd>' )
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
                    show:  display your relations with a user
    """
    # TODO: add `list` subcommand that will display all 3 lists as
    #       well as leaders/groupies/friends designations.
    # TODO: add full relation display mode (`detail` subcommand?)
    pass


@_follow.command( 'help', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='get help for a command' )
@click.argument( 'cmd', metavar='<cmd>', default=None,
                 cls=TootArgument, required=False,
                 help='get help for this command' )
def follow_help(cmd):
    """Get details on how to use a command."""
    ctx = click.get_current_context()
    if not cmd is None:
        c = _follow.get_command(ctx, cmd)
        if not c:
            click.echo('"{}": unknown command'.format(cmd))
        else:
            click.echo(c.get_help(ctx))
        return
    click.echo(_follow.get_help(ctx))


@_follow.command(    'followers', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='list who follows you' )
@click.argument( 'limit', metavar='<limit>', default=None,
                 cls=TootArgument, required=False,
                 type=click.INT, callback=_ts_arg_limitcheck_cb,
                 help='maximum users to show (default: 40, max: 80)' )
def follow_followers(limit):
    """Lists users who follow you."""
    mastodon = get_active_mastodon()
    if limit == 0: return
    user = mastodon.account_verify_credentials()
    users = mastodon.account_followers(user['id'], limit=limit)
    if not users:
        cprint("  You're safe!  There's nobody following you", fg('red'))
    else:
        cprint("  People who follow you (" + str(len(users)) + "):", fg('magenta'))
        printUsersShortShort(users)
_follow.add_command(follow_followers, 'f-ers')


@_follow.command(    'following', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='list who you follow' )
@click.argument( 'limit', metavar='<limit>', default=None,
                 cls=TootArgument, required=False,
                 type=click.INT, callback=_ts_arg_limitcheck_cb,
                 help='maximum users to show (default: 40, max: 80)' )
def follow_following(limit):
    """Lists users you follow."""
    mastodon = get_active_mastodon()
    if limit == 0: return
    user = mastodon.account_verify_credentials()
    users = mastodon.account_following(user['id'], limit=limit)
    if not users:
        cprint("  You aren't following anyone", fg('red'))
    else:
        cprint("  People you follow (" + str(len(users)) + "):", fg('magenta'))
        printUsersShortShort(users)
_follow.add_command(follow_following, 'f-ing')


@_follow.command(    'requests', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='list requests to follow you' )
@click.argument( 'limit', metavar='<limit>', default=None,
                 cls=TootArgument, required=False,
                 type=click.INT, callback=_ts_arg_limitcheck_cb,
                 help='maximum users to show (default: 40, max: 80)' )
def follow_requests(limit):
    """Lists your incoming follow requests."""
    mastodon = get_active_mastodon()
    if limit == 0: return
    users = mastodon.follow_requests(limit=limit)
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
@click.argument( 'usernames', metavar='<users>', nargs=-1,
                 cls=TootArgument, required=True,
                 help='users to follow' )
def follow_follow(usernames):
    """Follows an account by username or id."""
    mastodon = get_active_mastodon()
    userids = check_usernames(usernames)
    for userid in userids:
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
@click.argument( 'usernames', metavar='<users>', nargs=-1,
                 cls=TootArgument, required=True,
                 help='users to unfollow' )
def follow_unfollow(usernames):
    """Unfollows an account by username or id."""
    mastodon = get_active_mastodon()
    userids = check_usernames(usernames)
    for userid in userids:
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
@click.argument( 'usernames', metavar='<users>', nargs=-1,
                 cls=TootArgument, required=True,
                 help='users to accept' )
def follow_accept(usernames):
    """Accepts a user's follow request by username or id."""
    mastodon = get_active_mastodon()
    userids = check_usernames(usernames)
    for userid in userids:
        try:
            mastodon.follow_request_authorize(userid)
        except:
            cprint("  ... well, it *looked* like it was working ...", fg('red'))
            return

        print_ui_msg("  user {}'s request is accepted".format(userid))
    return
#aliases
_follow.add_command(follow_accept, 'ok')
_follow.add_command(follow_accept, 'f-yeh')


@_follow.command(    'reject', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='reject a follow request' )
@click.argument( 'usernames', metavar='<users>', nargs=-1,
                 cls=TootArgument, required=True,
                 help='users to reject' )
def follow_reject(usernames):
    """Rejects a user's follow request by username or id."""
    mastodon = get_active_mastodon()
    userids = check_usernames(usernames)
    for userid in userids:
        try:
            mastodon.follow_request_reject(userid)
        except:
            cprint("  ... well, it *looked* like it was working ...", fg('red'))
            return

        print_ui_msg("  user {}'s request is rejected".format(userid))
    return
#aliases
_follow.add_command(follow_reject, 'no')
_follow.add_command(follow_reject, 'f-no')


@_follow.command(    'show', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='show relations with a user' )
@click.argument( 'username', metavar='<user>',
                 cls=TootArgument, required=True,
                 help='user to examine' )
def follow_show(username):
    """Show relations between you and another user."""
    mastodon = get_active_mastodon()
    users = mastodon.account_search(username)
    if not users:
        print_error("  user {} not found".format(username))
        return

    if len(users) > 1:
        cprint("  found {} matches:".format(len(users)), fg('magenta'))

    ids = [ user['id'] for user in users ]
    try:
        relations = mastodon.account_relationships(ids)
    except Exception as e:
        logger.debug("{} when calling Mastodon.account_relationships() with arg(s) {}".format(type(e).__name__, repr(ids)))
        print_error("  ... well, it *looked* like it was working ...")

    if len(relations) != len(users):
        logger.debug("userlist ({}) not same size as relations ({})".format(len(users), len(relations)))

    # users and relations lists not guaranteed to be in the same order
    for rel in relations:
        user = next((user for user in users if user['id'] == rel['id']), None)
        if not user:
            print_error("dbg: no matching user found for id:{}".format(rel['id']))
            continue
        printUserRelations(user, rel)

#aliases


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
@click.argument( 'cmd', metavar='<cmd>', default=None,
                 cls=TootArgument, required=False,
                 help='get help for this command' )
def block_help(cmd):
    """Get details on how to use a command."""
    ctx = click.get_current_context()
    if not cmd is None:
        c = _block.get_command(ctx, cmd)
        if not c:
            click.echo('"{}": unknown command'.format(cmd))
        else:
            click.echo(c.get_help(ctx))
        return
    click.echo(_block.get_help(ctx))


@_block.command(     'list', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='list users you block' )
def block_list():
    """Lists users you have blocked."""
    # TODO: limit, pagination
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
@click.argument( 'usernames', metavar='<users>', nargs=-1,
                 cls=TootArgument, required=True,
                 help='users to block' )
def block_add(usernames):
    """Blocks a user by username or id."""
    mastodon = get_active_mastodon()
    userids = check_usernames(usernames)
    for userid in userids:
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
@click.argument( 'usernames', metavar='<users>', nargs=-1,
                 cls=TootArgument, required=True,
                 help='users to unblock' )
def block_remove(usernames):
    """Unblocks a user by username or id."""
    mastodon = get_active_mastodon()
    userids = check_usernames(usernames)
    for userid in userids:
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
@click.argument( 'cmd', metavar='<cmd>', default=None,
                 cls=TootArgument, required=False,
                 help='get help for this command' )
def mute_help(cmd):
    """Get details on how to use a command."""
    ctx = click.get_current_context()
    if not cmd is None:
        c = _mute.get_command(ctx, cmd)
        if not c:
            click.echo('"{}": unknown command'.format(cmd))
        else:
            click.echo(c.get_help(ctx))
        return
    click.echo(_mute.get_help(ctx))


@_mute.command(      'list', options_metavar='',
                     cls=TootStreamCmd,
                     short_help='list users you mute' )
def mute_list():
    """Lists users you have muted."""
    # TODO: limit, pagination
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
@click.argument( 'usernames', metavar='<users>', nargs=-1,
                 cls=TootArgument, required=True,
                 help='users to mute' )
def mute_add(usernames):
    """Mutes a user by username or id."""
    mastodon = get_active_mastodon()
    userids = check_usernames(usernames)
    for userid in userids:
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
@click.argument( 'usernames', metavar='<users>', nargs=-1,
                 cls=TootArgument, required=True,
                 help='users to unmute' )
def mute_remove(usernames):
    """Unmutes a user by username or id."""
    mastodon = get_active_mastodon()
    userids = check_usernames(usernames)
    for userid in userids:
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


