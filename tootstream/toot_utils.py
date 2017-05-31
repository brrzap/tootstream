import os
import click
import configparser
import getpass
from mastodon import Mastodon
from colored import fg, attr, stylize
import logging

logger = logging.getLogger('ts.utils')


RESERVED = ( "theme", "global" )
KEYCFGFILE = __name__ + 'cfgfile'
KEYCONFIG = __name__ + 'config'
KEYPROFILE = __name__ + 'profile'
KEYUSER = __name__ + 'user'
KEYMASTODON = __name__ + 'mastodon'
KEYLISTENERS = __name__ + 'listeners'
KEYNOTIFICATIONS = __name__ + 'notifications'

def get_logger(name):
    #import multiprocessing
    #logger = multiprocessing.get_logger().getChild(name)
    parent = click.get_current_context().meta['applogger']
    if parent:
        return parent.getChild(name)
    else:
        import multiprocessing
        return multiprocessing.get_logger().getChild(name)

def set_configfile(filename):
    click.get_current_context().meta[KEYCFGFILE] = filename
    return


def get_configfile():
    return click.get_current_context().meta.get(KEYCFGFILE)


def set_user(user):
    click.get_current_context().meta[KEYUSER] = user
    return


def get_user():
    return click.get_current_context().meta.get(KEYUSER)


def set_config(config):
    click.get_current_context().meta[KEYCONFIG] = config
    return


def get_config():
    return click.get_current_context().meta[KEYCONFIG]


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


def _init_listeners():
    click.get_current_context().meta[KEYLISTENERS] = []
    return


def get_listeners():
    return click.get_current_context().meta.get(KEYLISTENERS)


def add_listener(l):
    if not click.get_current_context().meta.get(KEYLISTENERS):
        _init_listeners()
    click.get_current_context().meta[KEYLISTENERS].append(l)
    return


def get_notifications():
    return click.get_current_context().meta.get(KEYNOTIFICATIONS)


def set_notifications():
    click.get_current_context().meta[KEYNOTIFICATIONS] = True
    return


def get_profile_values(profile):
    # quick return of existing profile, watch out for exceptions
    cfg = get_config()
    p = cfg[profile]
    return p['instance'], p['client_id'], p['client_secret'], p['token']


def get_known_profiles():
    cfg = get_config()
    return list( set(cfg.sections()) - set(RESERVED) )


def get_userid(username):
    # we got some user input.  we need a userid (int).
    # returns userid as int, -1 on error, or list of users if ambiguous.
    if not username:
        return -1

    # maybe it's already an int
    try:
        return int(username)
    except ValueError:
        pass

    # not an int
    mastodon = get_active_mastodon()
    users = mastodon.account_search(username)
    if not users:
        return -1
    elif len(users) > 1:
        # Mastodon's search is fuzzier than we want; check for exact match

        query = (username[1:] if username.startswith('@') else username)
        (quser, _, qinstance) = query.partition('@')
        localinstance, *_ = get_profile_values(get_active_profile())

        # on uptodate servers, exact match should be first in list
        for user in users:
            # match user@remoteinstance, localuser
            if query == user['acct']:
                return user['id']
            # match user@localinstance
            elif quser == user['acct'] and qinstance == localinstance:
                return user['id']

        # no exact match; return list
        return users
    else:
        return users[0]['id']


def parse_config():
    filename = get_configfile()
    (dirpath, basename) = os.path.split(filename)
    if not (dirpath == "" or os.path.exists(dirpath)):
        os.makedirs(dirpath)

    if not os.path.isfile(filename):
        logger.info("No configuration found, generating...")
        cfg = configparser.ConfigParser()
        set_config(cfg)
        return cfg

    cfg = configparser.ConfigParser()
    try:
        cfg.read(filename)
    except configparser.Error:
        logger.critical("This does not look like a valid configuration: {}".format(filename))
        sys.exit("Goodbye!")

    set_config(cfg)
    return cfg
# parse_config


def save_config():
    filename = get_configfile()
    (dirpath, basename) = os.path.split(filename)
    if not (dirpath == "" or os.path.exists(dirpath)):
        os.makedirs(dirpath)

    cfg = get_config()
    try:
        with open(filename, 'w') as configfile:
            cfg.write(configfile)
    except os.error:
        from .toot_print import print_error
        msg = "Unable to write configuration to {}".format(filename)
        logger.error(msg)
        print_error(msg)
# save_config


def register_app(instance):
    return Mastodon.create_app( 'tootstream',
                                api_base_url="https://" + instance )


def login(instance, client_id, client_secret):
    """
    Login to a Mastodon instance.
    Return a valid Mastodon token if login success, likely raises a Mastodon exception otherwise.
    """
    from .toot_print import print_ui_msg
    # temporary object to aquire the token
    mastodon = Mastodon(
        client_id=client_id,
        client_secret=client_secret,
        api_base_url="https://" + instance
    )

    print_ui_msg("  OAuth authorization needed.\nOpen this link in your browser to authorize login:")
    print_ui_msg("  {}".format(mastodon.auth_request_url()))
    print()
    code = input("  Enter authorization code:> ")

    return mastodon.log_in(code=code)


def parse_or_input_profile(profile, instance=None):
    """
    Validate an existing profile or get user input to generate a new one.
    If the user is not logged in, the user will be prompted 3 times
    before giving up.  Returns profile values on success: instance, client_id, client_secret, token
    On failure, returns None, None, None, None.
    """
    from .toot_print import print_ui_msg, print_error
    cfg = get_config()
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
        print_ui_msg("  Which instance would you like to connect to? eg: 'mastodon.social'")
        instance = input("  Instance: ")


    client_id = None
    if "client_id" in cfg[profile]:
        client_id = cfg[profile]['client_id']

    client_secret = None
    if "client_secret" in cfg[profile]:
        client_secret = cfg[profile]['client_secret']

    if (client_id == None or client_secret == None):
        try:
            client_id, client_secret = register_app(instance)
        except Exception as e:
            logger.error("{}: {}".format(type(e).__name__, e))
            print_error("  {}: Please try again later.".format(type(e).__name__))
            return None, None, None, None

    token = None
    if "token" in cfg[profile]:
        token = cfg[profile]['token']

    if (token == None):
        for i in [1, 2, 3]:
            try:
                token = login(instance, client_id, client_secret)
            except Exception as e:
                logger.error("{}: {}".format(type(e).__name__, e))
                print_error("  Error authorizing app. Did you enter the code correctly?")
            if token: break

        if not token:
            logger.error("giving up after 3 failed login attempts")
            print_error("  giving up after 3 failed login attempts")
            return None, None, None, None

    return instance, client_id, client_secret, token


#####################################
######## ARG/OPT CALLBACKS # ########
#####################################
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
        msg = "only 4 attachments allowed"
        print_error(msg)
        logger.error("{} (received: {})".format(msg, len(value)))
        ctx.abort()
    v = []
    error = False
    for val in value:
        f = _ts_filecheck(val)
        if f is None:
            msg = "file {} is not readable".format(val)
            print_error(msg)
            logger.error(msg)
            ctx.abort()
        v.append(f)
    return v


# callback for limit arguments
def _ts_arg_limitcheck_cb(ctx, param, value):
    # aborts with error if negative
    # returns None if None
    if value is None: return None
    elif value < 0:
        msg = "Invalid limit: {}".format(value)
        logger.error(msg)
        ctx.fail(msg)
    return value


__all__ = [ 'set_configfile', 'get_configfile',
            'set_config', 'get_config',
            'set_user', 'get_user',
            'set_active_profile', 'get_active_profile',
            'set_active_mastodon', 'get_active_mastodon',
            'get_profile_values',
            'get_known_profiles',
            'get_userid',
            'add_listener', 'get_listeners',
            'get_notifications', 'set_notifications',
            'parse_or_input_profile',
            'parse_config',
            'save_config',
            'get_logger',
            '_ts_option_filecheck_list_cb',
            '_ts_arg_limitcheck_cb'
            ]

