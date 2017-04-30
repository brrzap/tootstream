from mastodon import StreamListener
from gi.repository import Notify

# initialize modules
Notify.init("tstream")


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
            print_error("Notifications engaged for {} @{}".format(listener._tag, listener._name))
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
    """
    def __init__(self, name, tag=None, *args, **kwargs):
        super(TootDesktopNotifications, self).__init__(*args, **kwargs)
        # store an empty note
        self._note = Notify.Notification.new('')
        self._name = name
        self._tag = tag

        # set identifiers if available
        if name:
            self._note.set_app_name("tstream @{}".format(name))

        if tag and not tag[:1] == '#':
            tag = "#{}".format(tag)
    # end

    def _via_Notify(self, summary, body):
        # helper: the Notify object way
        self._note.update(summary, body)
        self._note.set_timeout(15000) # assuming 15 seconds TODO set default of 5-10s once tested
        self._note.show()

    def _via_notifysend(self, summary, body):
        # helper: kickoff external command
        # sample cmdline: notify-send -u normal -t 5000 -a AppName -i /path/to/file.png "summary" "body"
        # notify-send is available from `libnotify`
        pass

    def on_update(self, toot):
        # probably don't want notifications on every post
        if self._tag:
            summary = "{}".format(self._tag)
            body = "new from {} (id:{})".format(toot['account']['acct'], str(toot['id']))
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
        summary = "{} (id:{})".format(incoming['account']['acct'], str(incoming['account']['id']))
        body = ""

        if incoming['type'] == 'mention':
            body = "mentioned you in id:{}".format(str(incoming['status']['id']))
            pass
        elif incoming['type'] == 'follow':
            body = "followed you"
            pass
        elif incoming['type'] == 'reblog':
            body = "boosted your toot (id:{})".format(str(incoming['status']['id']))
            pass
        elif incoming['type'] == 'favourite':
            body = "fav'd your toot (id:{})".format(str(incoming['status']['id']))
            pass
        else:
            body = "..note id:{} unknown type:{}".format(str(incoming['id']), str(incoming['type']))
            pass

        # send via GI
        self._via_Notify(summary, body)
        return
    # end
# end

