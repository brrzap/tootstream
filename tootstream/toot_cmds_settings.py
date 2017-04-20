import click
from mastodon import Mastodon
from colored import fg, attr, stylize
from .toot_click import TootStreamCmd, TootStreamGroup, CONTEXT_SETTINGS
from .toot_utils import *
from .toot_print import *
from .toot_utils import RESERVED
#from .toot_utils import get_known_profiles, get_active_mastodon, get_active_profile, set_active_mastodon, set_active_profile
#from .toot_print import cprint, print_error, print_profiles


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
    print_profiles()
    return
# aliases
_profile.add_command(profile_list, 'ls')


@_profile.command( 'add', options_metavar='',
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
    cfg = get_config()
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
_profile.add_command(profile_load, 'open')


