import os.path
import click
import getpass
import sys
import re
import configparser
import random
#Do we still need readline?
#import readline
from toot_parser import TootParser
from mastodon import Mastodon
from collections import OrderedDict
from colored import fg, bg, attr, stylize

#Looks best with black background.
#TODO: Set color list in config file
COLORS = list(range(19,231))
RESERVED = ( "theme" )
KEYCFGFILE = __name__ + 'cfgfile'
KEYPROFILE = __name__ + 'profile'
KEYPROMPT = __name__ + 'prompt'
KEYMASTODON = __name__ + 'mastodon'


class IdDict:
    """Represents a mapping of local (tootstream) ID's to global
    (mastodon) IDs."""
    def __init__(self):
        self._map = []

    def to_local(self, global_id):
        """Returns the local ID for a global ID"""
        global_id = int(global_id) # In case a string gets passed
        try:
            return self._map.index(global_id)
        except ValueError:
            self._map.append(global_id)
            return len(self._map) - 1

    def to_global(self, local_id):
        """Returns the global ID for a local ID, or None if ID is invalid.
        Also prints an error message"""
        local_id = int(local_id)
        try:
            return self._map[local_id]
        except:
            cprint('Invalid ID.', fg('red'))
            return None


IDS = IdDict();
cfg = configparser.ConfigParser()
toot_parser = TootParser(indent='  ')


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
    click.get_current_context().meta[KEYPROMPT] = prompt
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
    # filename = CONF_PATH + instance + CLIENT_FILE
    # if not os.path.exists(CONF_PATH):
        # os.makedirs(CONF_PATH)
    # if os.path.isfile(filename):
        # return

    return Mastodon.create_app(
        'tootstream',
        api_base_url="https://" + instance
    )


def login(instance, email, password):
    """
    Login to a Mastodon instance.
    Return a Mastodon client if login success, otherwise returns None.
    """
    mastodon = get_active_mastodon()
    return mastodon.log_in(email, password)


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


def cprint(text, style, end="\n"):
    print(stylize(text, style), end=end)


#####################################
######## BEGIN COMMAND BLOCK ########
#####################################
commands = OrderedDict()


def command(func):
    commands[func.__name__] = func
    return func


@command
def help(rest):
    """List all commands."""
    print("Commands:")
    for command, cmd_func in commands.items():
        print("\t{}\t{}".format(command, cmd_func.__doc__))


@command
def toot(rest):
    """Publish a toot. ex: 'toot Hello World' will publish 'Hello World'."""
    mastodon = get_active_mastodon()
    mastodon.toot(rest)
    cprint("You tooted: ", fg('magenta') + attr('bold'), end="")
    cprint(rest, fg('magenta') + bg('white') + attr('bold') + attr('underlined'))


@command
def boost(rest):
    """Boosts a toot by ID."""
    mastodon = get_active_mastodon()
    rest = IDS.to_global(rest)
    if rest is None:
        return
    mastodon.status_reblog(rest)
    boosted = mastodon.status(rest)
    msg = "  Boosted: " + get_content(boosted)
    cprint(msg, fg('green') + bg('red'))


@command
def unboost(rest):
    """Removes a boosted tweet by ID."""
    mastodon = get_active_mastodon()
    rest = IDS.to_global(rest)
    if rest is None:
        return
    mastodon.status_unreblog(rest)
    unboosted = mastodon.status(rest)
    msg = "  Removed boost: " + get_content(unboosted)
    cprint(msg, fg('red') + bg('green'))


@command
def fav(rest):
    """Favorites a toot by ID."""
    mastodon = get_active_mastodon()
    rest = IDS.to_global(rest)
    if rest is None:
        return
    mastodon.status_favourite(rest)
    faved = mastodon.status(rest)
    msg = "  Favorited: " + get_content(faved)
    cprint(msg, fg('red') + bg('yellow'))


@command
def rep(rest):
    """Reply to a toot by ID."""
    mastodon = get_active_mastodon()
    command = rest.split(' ', 1)
    parent_id = IDS.to_global(command[0])
    if parent_id is None:
        return
    try:
        reply_text = command[1]
    except IndexError:
        reply_text = ''
    parent_toot = mastodon.status(parent_id)
    mentions = [i['acct'] for i in parent_toot['mentions']]
    mentions.append(parent_toot['account']['acct'])
    mentions = ["@%s" % i for i in list(set(mentions))] # Remove dups
    mentions = ' '.join(mentions)
    # TODO: Ensure that content warning visibility carries over to reply
    reply_toot = mastodon.status_post('%s %s' % (mentions, reply_text),
                                      in_reply_to_id=int(parent_id))
    msg = "  Replied with: " + get_content(reply_toot)
    cprint(msg, fg('red') + bg('yellow'))


@command
def unfav(rest):
    """Removes a favorite toot by ID."""
    mastodon = get_active_mastodon()
    rest = IDS.to_global(rest)
    if rest is None:
        return
    mastodon.status_unfavourite(rest)
    unfaved = mastodon.status(rest)
    msg = "  Removed favorite: " + get_content(unfaved)
    cprint(msg, fg('yellow') + bg('red'))


@command
def home(rest):
    """Displays the Home timeline."""
    mastodon = get_active_mastodon()
    for toot in reversed(mastodon.timeline_home()):
        display_name = "  " + toot['account']['display_name'] + " "
        username = "@" + toot['account']['acct'] + " "
        reblogs_count = "  ♺:" + str(toot['reblogs_count'])
        favourites_count = " ♥:" + str(toot['favourites_count']) + " "
        toot_id = str(IDS.to_local(toot['id']))

        # Prints individual toot/tooter info
        random.seed(display_name)
        cprint(display_name, fg(random.choice(COLORS)), end="")
        cprint(username, fg('green'), end="")
        cprint(toot['created_at'], attr('dim'))

        cprint(reblogs_count, fg('cyan'), end="")
        cprint(favourites_count, fg('yellow'), end="")
        cprint("id:" + toot_id, fg('red'))

        # Shows boosted toots as well
        if toot['reblog']:
            username = "  Boosted @" + toot['reblog']['account']['acct'] +": "
            cprint(username, fg('blue'), end="")
            content = get_content(toot['reblog'])
        else:
            content = get_content(toot)

        print(content + "\n")


@command
def fed(rest):
    """Displays the Federated timeline."""
    mastodon = get_active_mastodon()
    for toot in reversed(mastodon.timeline_public()):
        display_name = "  " + toot['account']['display_name']
        username = " @" + toot['account']['username'] + " "
        reblogs_count = "  ♺:" + str(toot['reblogs_count'])
        favourites_count = " ♥:" + str(toot['favourites_count']) + " "
        toot_id = str(IDS.to_local(toot['id']))

        # Prints individual toot/tooter info
        random.seed(display_name)
        cprint(display_name, fg(random.choice(COLORS)), end="")
        cprint(username, fg('green'), end="")
        cprint(toot['created_at'], attr('dim'))

        cprint(reblogs_count, fg('cyan'), end="")
        cprint(favourites_count, fg('yellow'), end="")

        cprint("id:" + toot_id, fg('red'))

        # Shows boosted toots as well
        if toot['reblog']:
            username = "  Boosted @" + toot['reblog']['account']['acct'] +": "
            cprint(username, fg('blue'), end="")
            content = get_content(toot['reblog'])
        else:
            content = get_content(toot)

        print(content + "\n")


@command
def local(rest):
    """Displays the Local (instance) timeline."""
    mastodon = get_active_mastodon()
    for toot in reversed(mastodon.timeline_local()):
        display_name = "  " + toot['account']['display_name']
        username = " @" + toot['account']['username'] + " "
        reblogs_count = "  ♺:" + str(toot['reblogs_count'])
        favourites_count = " ♥:" + str(toot['favourites_count']) + " "
        toot_id = str(IDS.to_local(toot['id']))

        # Prints individual toot/tooter info
        random.seed(display_name)
        cprint(display_name, fg(random.choice(COLORS)), end="")
        cprint(username, fg('green'), end="")
        cprint(toot['created_at'], attr('dim'))

        cprint(reblogs_count, fg('cyan'), end="")
        cprint(favourites_count, fg('yellow'), end="")

        cprint("id:" + toot_id, fg('red'))

        # Shows boosted toots as well
        if toot['reblog']:
            username = "  Boosted @" + toot['reblog']['account']['acct'] +": "
            cprint(username, fg('blue'), end="")
            content = get_content(toot['reblog'])
        else:
            content = get_content(toot)

        print(content + "\n")


@command
def note(rest):
    """Displays the Notifications timeline."""
    mastodon = get_active_mastodon()
    for note in reversed(mastodon.notifications()):
        display_name = "  " + note['account']['display_name']
        username = " @" + note['account']['username']
        random.seed(display_name)

        # Mentions
        if note['type'] == 'mention':
            cprint(display_name + username, (fg(random.choice(COLORS)), attr('bold')), end="")
            cprint(" mentioned you:", attr('bold'))

            cprint(get_content(note['status']), (fg('white'), attr('bold')))

        # Favorites
        elif note['type'] == 'favourite':
            reblogs_count = "  " + "♺:" + str(note['status']['reblogs_count'])
            favourites_count = " ♥:" + str(note['status']['favourites_count'])
            time = " " + note['status']['created_at']
            content = get_content(note['status'])

            cprint(display_name + username, fg(random.choice(COLORS)), end="")
            cprint(" favorited your status:", fg('yellow'))

            cprint(reblogs_count, fg('cyan'), end="")
            cprint(favourites_count, fg('yellow'))

            cprint(content, attr('dim'))

        # Boosts
        elif note['type'] == 'reblog':
            cprint(display_name + username, fg(random.choice(COLORS)), end="")
            cprint(" boosted your status:", fg('blue'))
            cprint(get_content(note['status']), attr('dim'))

        # Follows
        elif note['type'] == 'follow':
            username = re.sub('<[^<]+?>', '', username)
            display_name = note['account']['display_name']
            print("  ", end="")
            cprint(display_name + username + " followed you!", fg('red') + attr('bold'))

        # blank line
        print('')


@command
def exit(rest):
    """Ends the program."""
    sys.exit("Goodbye!")


@command
def info(rest):
    """Prints your user info."""
    mastodon = get_active_mastodon()
    user = mastodon.account_verify_credentials()

    print("@" + str(user['username']))
    cprint(user['display_name'], fg('cyan') + bg('red'))
    print(user['url'])
    cprint(re.sub('<[^<]+?>', '', user['note']), fg('red') + bg('green'))


@command
def delete(rest):
    """Deletes your toot by ID"""
    mastodon = get_active_mastodon()
    rest = IDS.to_global(rest)
    if rest is None:
        return
    mastodon.status_delete(rest)
    print("Poof! It's gone.")


@command
def block(rest):
    """Blocks a user by username."""
    # TODO: Find out how to get global usernames
    mastodon = get_active_mastodon()


@command
def unblock(rest):
    """Unblocks a user by username."""
    # TODO: Find out how to get global usernames
    mastodon = get_active_mastodon()


@command
def follow(rest):
    """Follows an account by username."""
    # TODO: Find out how to get global usernames
    mastodon = get_active_mastodon()


@command
def unfollow(rest):
    """Unfollows an account by username."""
    # TODO: Find out how to get global usernames
    mastodon = get_active_mastodon()


@command
def profile(rest):
#def profile(mastodon, rest):
    """Profile operations: create, load, remove, list."""
    global cfg
    command = rest.split(' ')
    usage = str("  usage: profile load [profilename]\n" +
                "         profile new [profilename [email [password]]]\n" +
                "         profile del [profilename]\n" +
                "         profile list")

    def profile_error(error):
        cprint("  "+error, fg('red'))
        return

    try:
        profile = command[1]
    except IndexError:
        profile = ""

    # load subcommand
    if command[0] in ["load"]:
        if profile == "":
            profile = input("  Profile name: ")

        if profile in get_known_profiles():
            # shortcut for preexisting profiles
            try:
                instance, client_id, client_secret, token = get_profile_values(profile)
            except:
                return profile_error("Invalid or corrupt profile")

            try:
                newmasto = Mastodon(
                    client_id=client_id,
                    client_secret=client_secret,
                    access_token=token,
                    api_base_url="https://" + instance)
            except:
                return profile_error("Mastodon error")

            # update stuff
            user = newmasto.account_verify_credentials()
            set_prompt("[@" + str(user['username']) + " (" + profile + ")]: ")
            set_active_profile(profile)
            set_active_mastodon(newmasto)
            cprint("  Profile " + profile + " loaded", fg('green'))
            return
        else:
            profile_error("Profile " + profile + " doesn't seem to exist")
            print_profiles()
            return
    # end load

    # new/create subcommand
    elif command[0] in ["new", "add", "create"]:
        if profile == "":
            profile = input("  Profile name: ")

        if profile in RESERVED:
            return profile_error("Illegal profile name: " + profile)
        elif profile in get_known_profiles():
            return profile_error("Profile " + profile + " exists")

        instance, client_id, client_secret, token = parse_or_input_profile(profile)
        try:
            newmasto = Mastodon(
                client_id=client_id,
                client_secret=client_secret,
                access_token=token,
                api_base_url="https://" + instance)
        except:
            return profile_error("Mastodon error")

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
    # end new/create

    # delete subcommand
    elif command[0] in ["delete", "del", "rm", "remove"]:
        if profile in [RESERVED, "default"]:
            return profile_error("Illegal profile name: " + profile)
        elif profile == "":
            profile = input("  Profile name: ")

        cfg.remove_section(profile)
        save_config()
        cprint("  Poof! It's gone.", fg('blue'))
        if profile == get_active_profile():
            set_active_profile("")
        return
    # end delete

    # list subcommand
    elif command[0] in ["ls", "list"]:
        print_profiles()
        return
    # end list

    # no subcommand; print usage
    cprint(usage, fg('red'))
    return


#####################################
######### END COMMAND BLOCK #########
#####################################


def authenticated(mastodon):
    if not os.path.isfile(APP_CRED):
        return False
    if mastodon.account_verify_credentials().get('error'):
        return False
    return True


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.option( '--instance', '-i', metavar='<string>',
               help='Hostname of the instance to connect' )
@click.option( '--email', '-e', metavar='<string>',
               help='Email to login' )
@click.option( '--password', '-p', metavar='<PASSWD>',
               help='Password to login (UNSAFE)' )
@click.option( '--config', '-c', metavar='<file>',
               type=click.Path(exists=False, readable=True),
               default='~/.config/tootstream/tootstream.conf',
               help='Location of alternate configuration file to load' )
@click.option( '--profile', '-P', metavar='<string>', default='default',
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


    say_error = lambda a, b: cprint("Invalid command. Use 'help' for a list of commands.",
            fg('white') + bg('red'))

    cprint("Welcome to tootstream! Two-Factor-Authentication is currently not supported.", fg('blue'))
    print("You are connected to ", end="")
    cprint(instance, fg('green') + attr('bold'))
    print("Enter a command. Use 'help' for a list of commands.")
    print("\n")

    user = mastodon.account_verify_credentials()
    set_prompt("[@" + str(user['username']) + " (" + profile + ")]: ")

    while True:
        command = input(get_prompt()).split(' ', 1)
        rest = ""
        try:
            rest = command[1]
        except IndexError:
            pass
        command = command[0]
        cmd_func = commands.get(command, say_error)
        cmd_func(rest)


if __name__ == '__main__':
    main()
