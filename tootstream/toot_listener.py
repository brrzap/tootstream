from mastodon import StreamListener
from .toot_print import print_error, print_ui_msg, printTimelineToot, printNotification
from .toot_utils import add_listener, get_listeners, get_logger
import multiprocessing
import logging

logger = logging.getLogger('ts.listen')


__all__ = [ 'TootDesktopNotifications',
            'TootConsoleListener',
            'seek_and_destroy',
            'seek_and_kick',
            'kick_new_process' ]


def worker_process(q, targetstream, listener, tag=None):
    """Wrapper for Mastodon.py streaming API.  This allows us
    to configure logging properly in the separate process."""
    if not q or not targetstream or not listener: return
    from logging.handlers import QueueHandler
    qh = QueueHandler(q)
    root = multiprocessing.get_logger()
    root.name = 'listenworker'
    name = multiprocessing.current_process().name
    worklogger = root.getChild('{}'.format(name))
    worklogger.setLevel(logging.DEBUG)
    worklogger.addHandler(qh)
    worklogger.debug('initializing worker process for {}'.format(name))

    if not targetstream:
        worklogger.debug('no stream')
        return
    elif not listener:
        worklogger.debug('no listener')
        return

    # ignore Ctrl-C
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    #import os
    #if os.name=='nt':
    #    signal.signal(signal.CTRL_C_EVENT, signal.SIG_IGN)

    lname = listener._dbgname
    # wrap stream call
    try:
        if tag:
            worklogger.debug('starting tag stream {}'.format(lname))
            targetstream(tag, listener)
        else:
            worklogger.debug('starting notification stream {}'.format(lname))
            targetstream(listener)
    except Exception as e:
        worklogger.error('stream exception {} on {}'.format(type(e).__name__, name))
        worklogger.debug('{}: {}'.format(type(e).__name__, e))

    # TODO: if we're dead we should let someone know so they can clean up the listener



def kick_new_process(targetstream, listener, tag=None):
    """Kick off a new child process on the given stream method with a
    given listener object.  Processes are named from the listener's _dbgname
    attribute.  Returns True on success.

    targetstream: can be a Mastodon.user_stream, Mastodon.hashtag_stream, or Mastodon.public_stream
    listener: a TootDesktopNotifications object
    """

    if not targetstream:
        logger.debug("no stream given, aborting")
        return False
    if not listener:
        logger.debug("no listener given, aborting")
        return False

    ls = get_listeners()
    if ls:
        # Ring of Protection vs Already Listening
        for l in ls:
            if listener == l:
                logger.error("Listener already listening. Unable to comply.")
                return False
            elif listener._dbgname == l._dbgname:
                logger.error("Another listener already listening. Unable to comply.")
                return False

    from click import get_current_context
    q = get_current_context().meta.get('Q')
    lname = listener._dbgname
    p = None
    try:
        if tag:
            logger.debug("kicking tag process for {}".format(lname))
            p = multiprocessing.Process( target=worker_process,
                                         daemon=True,
                                         name="L{}".format(lname),
                                         args=(q, targetstream, listener, tag,) )
        else:
            logger.debug("kicking notification process for {}".format(lname))
            p = multiprocessing.Process( target=worker_process,
                                         daemon=True,
                                         name="L{}".format(lname),
                                         args=(q, targetstream, listener,) )
        if p:
            p.start()
            add_listener(listener)


    except Exception as e:
        logger.error("{}: error configuring listener: {}".format(type(e).__name__, e))
        return False

    logger.info("Notifications engaged for {}".format(lname))
    return True
# end


def _split_tag_profile(name):
    # takes #foo@bar and returns (foo, bar)
    # accepts foo@bar, #foo, @bar
    # returns (None, None) if specified profile is invalid
    # if input is "#foo", returns (foo, <activeprofile>)
    # if input is "baz", returns (None, baz) if baz is a valid profile,
    #   or (baz, <activeprofile>) otherwise
    from .toot_utils import get_active_profile, get_known_profiles
    tag = None
    profile = None
    if name.startswith('#'):
        # #name: tag name on current profile
        if '@' in name:
            # #foo@bar: tag foo on profile bar
            (tag, sep, profile) = name[1:].partition('@')
            if profile not in get_known_profiles() and profile != get_active_profile():
                # abort abort abort
                tag = None
                profile = None
        else:
            tag = name[1:]
            profile = get_active_profile()
    elif name.startswith('@'):
        # @name: specified profile
        if name[1:] in get_known_profiles() or name[1:] == get_active_profile():
            profile = name[1:]
    elif '@' in name:
        # foo@bar: tag foo on profile bar
        (tag, sep, profile) = name.partition('@')
        if profile not in get_known_profiles() and profile != get_active_profile():
            # abort abort abort
            tag = None
            profile = None
    else:
        # name: try it as profile and fall back to tag
        if name in get_known_profiles() or name == get_active_profile():
            profile = name
        else:
            tag = name
            profile = get_active_profile()
        pass
    return (tag, profile)
# end


def seek_and_destroy(name):
    if not name:
        return False

    from .toot_utils import get_listeners
    lstnrs = get_listeners()
    children = multiprocessing.active_children()

    if not lstnrs or not children:
        return False

    child = None
    lstn = None
    if (name.startswith('#') and '@' in name) or name.startswith('@'):
        # should find exact match
        pname = "L{}".format(name)
        child = next((x for x in children if x.name == pname), None)
        lstn = next((x for x in lstnrs if x._dbgname == name), None)
        if child and lstn:
            logger.debug("seek_and_destroy: targets found ({}, {})".format(pname, lstn._dbgname))
            child.terminate()
            child.join()
            lstnrs.remove(lstn)
            return True
        elif lstn and not child:
            # found listener but not child process.
            # process died?  remove listener.
            lstnrs.remove(lstn)
            logger.debug("removed listener {} with no matching process.".format(lstn._dbgname))
            return True
    elif '@' in name:
        name = "#{}".format(name)
        # should find exact match
        pname = "L{}".format(name)
        child = next((x for x in children if x.name == pname), None)
        lstn = next((x for x in lstnrs if x._dbgname == name), None)
        if child and lstn:
            logger.debug("seek_and_destroy: targets found ({}, {})".format(pname, lstn._dbgname))
            child.terminate()
            child.join()
            lstnrs.remove(lstn)
            return True
        elif lstn and not child:
            # found listener but not child process.
            # process died?  remove listener.
            lstnrs.remove(lstn)
            logger.debug("removed listener {} with no matching process.".format(lstn._dbgname))
            return True
    elif name.startswith('#'):
        # missing a profilename, so fuzzy match
        child = next((x for x in children if name in x.name), None)
        lstn = next((x for x in lstnrs if name in x._dbgname), None)
        if child and lstn and lstn._dbgname in child.name:
            # names match, ok
            logger.debug("seek_and_destroy: targets found ({}, {})".format(child.name, lstn._dbgname))
            child.terminate()
            child.join()
            lstnrs.remove(lstn)
            return True
        elif child and lstn:
            # we found nonmatching stuff, abort
            logger.debug("found child {} and listener {}, aborting".format(child.name, lstn._dbgname))
            return False
        elif lstn and not child:
            # found listener but not child process.
            # process died?  remove listener.
            lstnrs.remove(lstn)
            logger.debug("removed listener {} with no matching process.".format(lstn._dbgname))
            return True
    else:
        # dunno if this is tag or profile.  maybe it's profile?
        tname = "@{}".format(name)
        logger.debug("ambiguous name {}, trying as profile: {}".format(name, tname))
        child = next((x for x in children if tname in x.name), None)
        lstn = next((x for x in lstnrs if tname in x._dbgname), None)
        if child and lstn and lstn._dbgname in child.name:
            # names match, ok
            logger.debug("seek_and_destroy: targets found ({}, {})".format(child.name, lstn._dbgname))
            child.terminate()
            child.join()
            lstnrs.remove(lstn)
            return True
        elif child and lstn:
            # we found nonmatching stuff, abort
            logger.debug("found child {} and listener {}, aborting".format(child.name, lstn._dbgname))
            return False
        else:
            # try again as a tagname
            tname = "#{}".format(name)
            logger.debug("failed profile search, trying as tag: {}".format(tname))
            child = next((x for x in children if tname in x.name), None)
            lstn = next((x for x in lstnrs if tname in x._dbgname), None)
            if child and lstn and lstn._dbgname in child.name:
                # names match, ok
                logger.debug("seek_and_destroy: targets found ({}, {})".format(child.name, lstn._dbgname))
                child.terminate()
                child.join()
                lstnrs.remove(lstn)
                return True
            # give up
            elif child and lstn:
                logger.debug("found child {} and listener {}, aborting".format(child.name, lstn._dbgname))
            return False

    return False
# end


def seek_and_kick(name, console=False):
    from .toot_utils import get_active_profile
    if not name:
        return False

    (tag, profile) = _split_tag_profile(name)
    logger.debug('seek_and_kick trying name:{} tag:{} profile:{}'.format(name, tag, profile))

    targetstream = None
    listener = None

    # validate and find targetstream
    if not tag and not profile:
        return False
    elif profile == get_active_profile():
        from .toot_utils import get_active_mastodon
        if tag is None:
            targetstream = get_active_mastodon().user_stream
            #listener = TootDesktopNotifications(profile)
        else:
            targetstream = get_active_mastodon().hashtag_stream
            #listener = TootDesktopNotifications(profile, tag)
    else:
        from mastodon import Mastodon
        from .toot_utils import get_profile_values
        try:
            pinstance, pclientid, pclientsec, ptoken = get_profile_values(profile)
            newmasto = Mastodon( client_id=pclientid, client_secret=pclientsec,
                                 access_token=ptoken, api_base_url="https://{}".format(pinstance) )
        except:
            return False

        if tag is None:
            targetstream = newmasto.user_stream
            #listener = TootDesktopNotifications(profile)
        else:
            targetstream = newmasto.hashtag_stream
            #listener = TootDesktopNotifications(profile, tag)

    # get listener
    if console:
        listener = TootConsoleNotifications(profile, tag)
    else:
        listener = TootDesktopNotifications(profile, tag)

    return kick_new_process( targetstream, listener, tag=tag )
# end


class TootConsoleListener(StreamListener):
    """Simple subclass of the mastodon.StreamListener class to print toots
    on the console as they come in."""
    def __init__(self, *args, **kwargs):
        super(TootConsoleListener, self).__init__(*args, **kwargs)
        self.logger = get_logger("consoleListener")

    def on_update(self, toot):
        self.logger.debug("on_update: toot id:{} from acct:{}".format(toot['id'], toot['account']['acct']))
        printTimelineToot(toot)
        return

    def on_delete(self, statusid):
        self.logger.debug("on_delete: toot id:{} deleted".format(statusid))
        return

    def on_notification(self, incoming):
        self.logger.debug("on_notification: note id:{} type:{} from acct:{}".format(incoming['id'], incoming['type'], incoming['account']['acct']))
        return


class TootConsoleNotifications(StreamListener):
    """Simple subclass of mastodon.StreamListener to print notifications
    on the console as they come in."""
    def __init__(self, name, tag=None, *args, **kwargs):
        super(TootConsoleNotifications, self).__init__(*args, **kwargs)
        self._name = name
        self._tag = tag
        # set identifiers if available
        if name and not name[:1] == '@':
            self._name = "@{}".format(name)

        if tag and not tag[:1] == '#':
            self._tag = "#{}".format(tag)

        self._dbgname = ("{}{}".format(self._tag, self._name) if self._tag else self._name)
        self.logger = get_logger("consoleNotify{}".format(self._dbgname))
        self.logger.debug("initializing logger")

    def on_update(self, toot):
        # probably don't want notifications on every post
        self.logger.debug("on_update: toot id:{} from acct:{}".format(toot['id'], toot['account']['acct']))
        if self._tag:
            print()
            printTimelineToot(toot)
        else:
            # if self._tag is empty we're on a user stream, ignore
            pass

    def on_notification(self, incoming):
        self.logger.debug("on_notification: note id:{} type:{} from acct:{}".format(incoming['id'], incoming['type'], incoming['account']['acct']))
        # TODO: this should really go into a queue of some sort
        print()  # extra newline first to clear the prompt, if applicable
        printNotification(incoming)
        return


class TootDesktopNotifications(StreamListener):
    """Subclass of mastodon.StreamListener to interface with a Desktop Environment's
    notifications display.  The user will need a notification server (likely builtin
    if you're using GNOME, KDE, Unity, or another major DE).

    1st experiment: using gi.repository.Notify

    2nd experiment: launch `notify-send`

    name: instance name or profile nickname to display
    tag: hashtag stream we'll be following
    timeout: default timeout for notification popups
    """
    def __init__(self, name, tag=None, timeout=15000, *args, **kwargs):
        super(TootDesktopNotifications, self).__init__(*args, **kwargs)
        # store an empty note
        self._name = name
        self._tag = tag
        self._timeout = timeout
        self._app = 'tootstream'

        # set identifiers if available
        if name and not name[:1] == '@':
            self._name = "@{}".format(name)

        if tag and not tag[:1] == '#':
            self._tag = "#{}".format(tag)

        self._dbgname = ("{}{}".format(self._tag, self._name) if self._tag else self._name)
        self.logger = get_logger("listener{}".format(self._dbgname))
        self.logger.debug("initializing logger")

        # find a notification subsystem to use.
        if self._check_GINotify():
            self.logger.debug("using gi.repository.Notify")
            from gi.repository import Notify
            Notify.init(self._app)
            self._note = Notify.Notification.new('')
            self._note.set_category('im.received')
            self._send = self._via_Notify
        elif self._check_Notify2():
            self.logger.debug("using dbus+notify2")
            import notify2
            notify2.init(self._app)
            self._note = notify2.Notification('')
            self._note.set_category('im.received')
            self._send = self._via_Notify
        elif self._check_notifysend():
            self.logger.debug("using external notify-send")
            self._send = self._via_notifysend
        else:
            self.logger.error("can't find a backend")
            self._send = self._via_stdout
    # end

    def _check_GINotify(self):
        try:
            from gi.repository import Notify
        except:
            return False
        return True

    def _check_Notify2(self):
        try:
            import notify2
        except:
            return False
        return True

    def _check_notifysend(self):
        try:
            from subprocess import call, getstatusoutput
            (err, out) = getstatusoutput('which notify-send')
            if err:
                # msg user to install relevant package? or fix paths?
                return False
        except:
            return False
        return True

    def _via_Notify(self, summary, body):
        # helper: the Notify object way
        if self._check_GINotify():
            from gi.repository import Notify
        elif self._check_Notify2():
            import notify2
        else:
            return

        self._note.update(summary, body)
        self._note.set_timeout(self._timeout) # assuming 15 seconds TODO set default of 5-10s once tested
        self._note.show()

    def _via_notifysend(self, summary, body):
        # helper: kickoff external command
        # notify-send is available from `libnotify`
        from subprocess import call

        # notify-send arguments
        thisnote = [ 'notify-send',
                     '-t', str(self._timeout),   # expiration 15s, TODO make configurable
                     '--category=im.received',   # generic
                     '--app-name', self._app,    # TODO make configurable
                     #'-i', self._icon            # specify an icon? might be too much unless we provide one
                     summary,
                     body ]
        call(thisnote)

    def _via_stdout(self, summary, body):
        # helper: dump to stdout
        msg = "Listener {}: summary: {} message: {}".format( self._dbgname, summary, body )
        self.logger.info(msg)
        print(msg)

    def on_update(self, toot):
        # probably don't want notifications on every post
        if not toot: return
        self.logger.debug("on_update: toot id:{} from acct:{}".format(toot['id'], toot['account']['acct']))
        if self._tag:
            summary = "{}".format(self._tag)
            body = "new from {} (id:{})".format(toot['account']['acct'], str(toot['id']))
            self._send(summary, body)
        else:
            # if self._tag is empty we're on a user stream, ignore
            pass

    def on_delete(self, tootid):
        # probably don't want notifications on every deletion
        pass

    def on_notification(self, incoming):
        """Our main interest."""
        # deps on Arch: python-gobject, libnotify
        # deps on Debian: python-gobject, libnotify-bin (TODO: verify)
        self.logger.debug("on_notification: note id:{} type:{} from acct:{}".format(incoming['id'], incoming['type'], incoming['account']['acct']))
        summary = "{}".format(self._name)
        body = "{} (id:{})".format(incoming['account']['acct'], str(incoming['account']['id']))

        if incoming['type'] == 'mention':
            body += " mentioned you in id:{}".format(str(incoming['status']['id']))
            pass
        elif incoming['type'] == 'follow':
            body += " followed you"
            pass
        elif incoming['type'] == 'reblog':
            body += " boosted your toot (id:{})".format(str(incoming['status']['id']))
            pass
        elif incoming['type'] == 'favourite':
            body += " fav'd your toot (id:{})".format(str(incoming['status']['id']))
            pass
        else:
            body += " ..note id:{} unknown type:{}".format(str(incoming['id']), str(incoming['type']))
            self.logger.debug("unknown notification type:{} {}".format(incoming['type'], repr(incoming)))
            pass

        self._send(summary, body)
        return
    # end
# end

