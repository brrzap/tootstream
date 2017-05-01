from mastodon import StreamListener
from .toot_print import print_error


__all__: [ 'TootDesktopNotifications',
           'kick_new_thread' ]


def kick_new_thread(mastodon, listener):
    from .toot_print import print_error
    from .toot_utils import add_listener, get_listeners
    import threading

    if not mastodon or not listener:
        print_error("Empty object. Unable to comply.")

    ls = get_listeners()
    if ls:
        # Ring of Protection vs Already Listening
        for l in ls:
            if listener == l:
                print_error("Listener already listening. Unable to comply.")
                return
            elif listener._name == l._name and listener._tag == l._tag:
                print_error("Another listener already listening. Unable to comply.")
                return

    try:
        add_listener(listener)
        t = threading.Thread( target=mastodon.user_stream, daemon=True, args=(listener,) )
        if t:
            t.start()
        if listener._tag:
            print_error("Notifications engaged for {} {}".format(listener._tag, listener._name))
        else:
            print_error("Notifications engaged for {}".format(listener._name))
    except Exception as e:
        print_error("{}: error configuring listener: {}".format(type(e).__name__, e))
    return
# end


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

        self._dbgname = ("{} {}".format(self._name, self._tag) if self._tag else self._name)

        # find a notification subsystem to use.
        if self._check_GINotify():
            print_error("listener {} using gi.repository.Notify".format(self._dbgname))
            from gi.repository import Notify
            Notify.init(self._app)
            self._note = Notify.Notification.new('')
            self._note.set_category('im.received')
            self._send = self._via_Notify
        elif self._check_Notify2():
            print_error("listener {} using dbus+notify2".format(self._dbgname))
            import notify2
            notify2.init(self._app)
            self._note = notify2.Notification('')
            self._note.set_category('im.received')
            self._send = self._via_Notify
        elif self._check_notifysend():
            print_error("listener {} using external notify-send".format(self._dbgname))
            self._send = self._via_notifysend
        else:
            print_error("listener {} can't find a backend".format(self._dbgname))
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
        print("Listener {}: summary: {} message: {}".format( self._dbgname, summary, body ))

    def on_update(self, toot):
        # probably don't want notifications on every post
        if self._tag:
            summary = "{}".format(self._tag)
            body = "new from {} (id:{})".format(toot['account']['acct'], str(toot['id']))
            self._send(summary, body)
        else:
            # if self._tag is empty we're on a user stream, ignore
            pass

    def on_delete(self, status):
        # probably don't want notifications on every deletion
        pass

    def on_notification(self, incoming):
        """Our main interest."""
        # deps on Arch: python-gobject, libnotify
        # deps on Debian: python-gobject, libnotify-bin (TODO: verify)
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
            pass

        self._send(summary, body)
        return
    # end
# end

