import click
from mastodon import Mastodon
from colored import fg, attr, stylize
from .toot_click import TootStreamCmd, TootStreamGroup, CONTEXT_SETTINGS
from .toot_utils import *
from .toot_print import *
from .toot_listener import *
from .toot_utils import RESERVED
import logging

logger = logging.getLogger('ts.set')


#####################################
##### LISTENER MANAGEMENT CMDS ######
#####################################
@click.group(      'listen', short_help='listen add|remove|list',
                   cls=TootStreamGroup,
                   context_settings=CONTEXT_SETTINGS,
                   invoke_without_command=True,
                   no_args_is_help=True,
                   options_metavar='',
                   subcommand_metavar='<command>' )
def _listen():
    """Listener management operations: add, remove, list.
    Additions will spawn new desktop notification processes."""
    pass


@_listen.command( 'help', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='get help for a command' )
@click.argument('cmd', metavar='<cmd>', required=False, default=None)
def listen_help(cmd):
    """Get details on how to use a command."""
    ctx = click.get_current_context()
    if not cmd is None:
        c = _listen.get_command(ctx, cmd)
        click.echo(c.get_help(ctx))
        return
    click.echo(_listen.get_help(ctx))


@_listen.command( 'list', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='list known listeners' )
def listen_list():
    """List existing listeners."""
    ls = get_listeners()
    if not ls:
        print_ui_msg("  No listeners found")
        return
    for l in ls:
        print_ui_msg("  listening to {}".format(l._dbgname))
    return
# aliases
_listen.add_command(listen_list, 'ls')


@_listen.command( 'add', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='add a #tag listener' )
@click.argument('names', metavar='<#tag|@profile>', nargs=-1)
def listen_add(names):
    """Add new listeners on specified #hashtags or @profiles.

    Valid arguments: #tagname, @profilename, #tagname@profilename

    \b
       listen add #hashtag     # listens to the current instance's hashtag stream for "hashtag"
       listen add @other       # listens to the user stream at the instance on profile "other"
       listen add #tag@other   # ...stream for "tag" at the instance on profile "other"
       listen add this         # ...first tries as profile, falls back to hashtag
       listen add #this @that #the@other   # starts 3 different listeners
    """
    # ignore global setting here since this is directly user-requested
    if len(names)==0:
        click.get_current_context().invoke(listen_help, cmd='add')
        return

    for name in names:
        if seek_and_kick(name):
            print_ui_msg("  Listener {} is off and running.".format(name))
        else:
            print_error("  Could not locate listener {}.".format(name))

    return
# aliases
_listen.add_command(listen_add, 'create')
_listen.add_command(listen_add, 'new')


@_listen.command( 'stop', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='stop a listener' )
@click.argument('names', metavar='<#tag|@profile>', nargs=-1, required=False)
def listen_stop(names):
    """Stop existing listeners.

    Valid arguments: #tagname, @profilename, #tagname@profilename

    \b
       listen stop #hashtag     # stops a hashtag listener for "hashtag"
       listen stop @other       # stops a user stream listener at the instance on profile "other"
       listen stop #tag@other   # ...stream for "tag" at the instance on profile "other"
       listen stop this         # ...first tries as profile, falls back to hashtag
       listen stop #this @that #the@other   # stops 3 different listeners
    """
    if len(names)==0:
        click.get_current_context().invoke(listen_help, cmd='stop')
        print_ui_msg("\n  Please indicate which listener needs killing:")
        click.get_current_context().invoke(listen_list)
        return

    for name in names:
        if seek_and_destroy(name):
            print_ui_msg("  Listener {} is dead.".format(name))
        else:
            print_error("  Could not locate listener {}.".format(name))

    return
# aliases
_listen.add_command(listen_stop, 'kill')
_listen.add_command(listen_stop, 'rm')


#####################################
###### PROFILE MANAGEMENT CMDS ######
#####################################
@click.group(      'profile', short_help='profile load|create|remove|list',
                   cls=TootStreamGroup,
                   context_settings=CONTEXT_SETTINGS,
                   invoke_without_command=True,
                   no_args_is_help=True,
                   options_metavar='',
                   subcommand_metavar='<command>' )
def _profile():
    """Profile management operations: create, load, remove, list.
    Additions and removals will save the configuration file."""
    pass


@_profile.command( 'help', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='get help for a command' )
@click.argument('cmd', metavar='<cmd>', required=False, default=None)
def profile_help(cmd):
    """Get details on how to use a command."""
    ctx = click.get_current_context()
    if not cmd is None:
        c = _profile.get_command(ctx, cmd)
        click.echo(c.get_help(ctx))
        return
    click.echo(_profile.get_help(ctx))


@_profile.command( 'list', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='list known profiles' )
def profile_list():
    """List known profiles."""
    printProfiles()
    return
# aliases
_profile.add_command(profile_list, 'ls')


@_profile.command( 'add', options_metavar='',
                  cls=TootStreamCmd,
                  short_help='add a profile' )
@click.argument('profile', metavar='[<profile>', required=False, default=None)
@click.argument('instance', metavar='[<hostname>]]', required=False, default=None)
def profile_add(profile, instance):
    """Create a new profile.

    \b
        profile:  name of the profile to add
       hostname:  instance this account is on"""
    if profile is None:
        profile = input("  Profile name: ")

    if profile in RESERVED:
        print_error("Illegal profile name: " + profile)
        return
    elif profile in get_known_profiles():
        print_error("Profile " + profile + " exists")
        return

    instance, client_id, client_secret, token = parse_or_input_profile(profile)
    if not token:
        print_error("Could not log you in. Please try again later.\nThis profile will not be saved.")
        return

    try:
        newmasto = Mastodon(
            client_id=client_id,
            client_secret=client_secret,
            access_token=token,
            api_base_url="https://" + instance)
    except Exception as e:
        msg = "{}: {}".format(type(e).__name__, e)
        logger.error(msg)
        print_error(msg)
        return

    # update stuff
    cfg = get_config()
    cfg[profile] = {
        'instance': instance,
        'client_id': client_id,
        'client_secret': client_secret,
        'token': token
    }
    user = newmasto.account_verify_credentials()
    set_user(user)
    set_active_profile(profile)
    set_active_mastodon(newmasto)
    if get_notifications():
        kick_new_process( newmasto.user_stream, TootDesktopNotifications(profile) )
    cprint("  Profile " + profile + " loaded", fg('green'))
    save_config()
    return
# aliases
_profile.add_command(profile_add, 'new')
_profile.add_command(profile_add, 'create')


@_profile.command( 'del', options_metavar='',
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

    cfg = get_config()
    cfg.remove_section(profile)
    save_config()
    cprint("  Poof! It's gone.", fg('blue'))
    if profile == get_active_profile():
        set_active_profile("")
    return
# aliases
_profile.add_command(profile_del, 'delete')
_profile.add_command(profile_del, 'rm')
_profile.add_command(profile_del, 'remove')


@_profile.command( 'load', options_metavar='',
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
        except Exception as e:
            msg = "{}: {}".format(type(e).__name__, e)
            logger.error(msg)
            print_error(msg)
            return

        # update stuff
        user = newmasto.account_verify_credentials()
        set_user(user)
        set_active_profile(profile)
        set_active_mastodon(newmasto)
        if get_notifications():
            kick_new_process( newmasto.user_stream, TootDesktopNotifications(profile) )
        cprint("  Profile " + profile + " loaded", fg('green'))
        return
    else:
        print_error("Profile " + profile + " doesn't seem to exist")
        printProfiles()

    return
# aliases
_profile.add_command(profile_load, 'open')


