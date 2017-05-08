import click
import logging

logger = logging.getLogger('ts.click')


__all__ = [ 'TootStreamCmd', 'TootStreamGroup',
            'CONTEXT_SETTINGS',
            'repl', 'register_repl' ]


CONTEXT_SETTINGS = dict( help_option_names=['-h', '--help'],
                         max_content_width=100 )


class TootStreamCmd(click.Command):
    """Overload click.Command to customize help formatting."""
    hidden = False

    def __init__(self, hidden=False, aliases=None, *args, **kwargs):
        super(TootStreamCmd, self).__init__(*args, **kwargs)
        self.hidden = hidden
        # TODO: do something with aliases

    def format_usage(self, ctx, formatter):
        pieces = list(filter(None, self.collect_usage_pieces(ctx)))
        formatter.write_usage(self.name, ' '.join(pieces))

    def format_help(self, ctx, formatter):
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        # TODO: detect non-help options and print if exist
        # only help options atm, skip
        #self.format_options(ctx, formatter)
        self.format_epilog(ctx, formatter)


class TootStreamGroup(click.Group, TootStreamCmd):
    """Overload click.Group to customize help formatting."""
    def __init__(self, *args, **kwargs):
        super(TootStreamGroup, self).__init__(*args, **kwargs)

    def format_help(self, ctx, formatter):
        self.format_commands(ctx, formatter)
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)

    def format_usage(self, ctx, formatter):
        pieces = list(filter(None, self.collect_usage_pieces(ctx)))
        pieces.append('<args>')
        basename = ""
        if self.name != "tootstream":
            basename = self.name
        formatter.write_usage(basename, ' '.join(pieces))

    def format_options(self, ctx, formatter):
        # TODO: detect non-help options and print if exist
        # Command.format_options(self, ctx, formatter)
        self.format_commands(ctx, formatter)

    def format_commands(self, ctx, formatter):
        # TODO: proper aliases will require changes
        # in click.Group this compiles a list of (cmd, help),
        # but our aliases pull in several duplicates.
        #
        # 1. flip the dict, appending keys of duplicate values in a list.
        flipped = {}
        for c, f in self.commands.items():
            cmd = self.get_command(ctx, c)
            if cmd is None:
                continue
            if cmd.hidden:
                continue
            if f not in flipped: flipped[f] = []
            flipped[f].append(c)

        rows = []
        # 2. sort that list, grab short_help.
        for cmds in flipped.values():
            cmds.sort()
            h = self.commands[cmds[0]].short_help
            args = self.commands[cmds[0]].collect_usage_pieces(ctx)
            rows.append(('|'.join(cmds)+' '+' '.join(args), h))

        # 3. hand off to the formatter as ('cmd1|cmd2 <args>', 'help text')
        if rows:
            with formatter.section('Commands'):
                formatter.write_dl(rows)


class TootStreamCmdCollection(click.CommandCollection):
    """Overload click.CmdCollection to customize help formatting."""
    def __init__(self, *args, **kwargs):
        super(TootStreamCmdCollection, self).__init__(*args, **kwargs)


######################################################
### support utilities for click-repl use
### (mostly python-prompt-toolkit related)

# for prompt styling
from prompt_toolkit import prompt
from prompt_toolkit.styles import style_from_dict
from prompt_toolkit.token import Token
# for fish-shell-esque autosuggest
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
# for readline-style tab completion
from prompt_toolkit.key_binding.bindings.completion import display_completions_like_readline
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.keys import Keys
# for utils
from .toot_utils import get_user, get_config, get_active_profile, get_listeners

# readline-replacement keybinding registry
registry = load_key_bindings( enable_abort_and_exit_bindings=True,   # allow Ctrl-C & Ctrl-D
                              enable_system_bindings=True,           # allow Ctrl-Z, meta-!
                              enable_search=True,                    # allow search bindings
                              enable_auto_suggest_bindings=True )    # fish-style suggestion bindings
registry.add_binding(Keys.ControlI)(display_completions_like_readline)

def get_username():
    return get_user()['acct']

def get_instance():
    p = get_config()[get_active_profile()]
    return p['instance']

def get_prompt_tokens(cli):
    return [
             (Token.Start,    '['   ),
             (Token.Username, '@{}'.format(get_username()) ),
             (Token.Sep,      ' '   ),
             (Token.Profile,  '({})'.format(get_active_profile()) ),
             (Token.End,      ']: ' ) ]

def get_bottom_toolbar_tokens(cli):
    """Define a nifty bottom-aligned statusbar."""
    from .toot_print import _format_usercounts
    from wcwidth import wcswidth

    # leftside: instance
    instance = get_instance()
    usercounts = _format_usercounts(get_user())
    out = [ (Token.TbHeader, '   '),
            (Token.Instance, instance),
            (Token.TbSep, ' '),
            (Token.UserCounts, usercounts) ]

    # rightside: active listeners
    lsnrs = get_listeners()
    if lsnrs and len(lsnrs)>0:
        (width, _) = click.get_terminal_size()
        lstnheader = 'listeners: ['
        lsnrstring = "{}".format(' '.join( (l._dbgname for l in lsnrs) ))
        lsnrslen = wcswidth(lsnrstring)       # min length of full lsnr list
        if lsnrslen > (width//2):
            # lsnr list is too long, summarize
            lsnrstring = "{} listeners".format(str(len(lsnrs)))

        spacerlen = int( width
                        - (5 + wcswidth(instance) + wcswidth(usercounts))  # leftside length
                        - (5 + wcswidth(lstnheader))           # rightside header+footer
                        - (1 + wcswidth(lsnrstring)) )         # rightside content

        out += [ ( Token.TbSep,       ' '*spacerlen ),
                 ( Token.LstnHeader,  lstnheader    ),
                 ( Token.Listener,    lsnrstring    ),
                 ( Token.LstnFooter,  ']'           ) ]

    return out


ts_prompt_toolbar_style = style_from_dict({
    # user input
    Token: '#d0d0d0',

    # prompt
    Token.Start:      '#d0d0d0',
    Token.Username:   '#5f87ff',
    Token.Sep:        '#000000',
    Token.Profile:    '#00ff5f',
    Token.End:        '#d0d0d0',

    # toolbar
    Token.Toolbar:    '#ffff00 bg:#303030',
    Token.TbHeader:   '#ffff00 bg:#303030',
    Token.TbSep:      '#ffff00 bg:#303030',
    Token.Instance:   '#af0000 bg:#303030',
    Token.UserCounts: '#5f87ff bg:#303030',
    Token.LstnHeader: '#af875f bg:#303030',
    Token.Listener:   '#5f5fff bg:#303030',
    Token.LstnFooter: '#af875f bg:#303030'
}) # end style

ts_prompt_kwargs = { # prompt-toolkit options
    #
    #'history':  InMemoryHistory()  # click-repl default but we might want to tweak
    #'completer':  ClickCompleter(_tootstream) #click-repl default
    #'message':  # use get_prompt_tokens instead
    #'mouse_support': True    # clever but kills buffer scrollback
    'patch_stdout': True,                      # don't scroll the prompt?
    'auto_suggest': AutoSuggestFromHistory(),  # fish-shell autosuggestions
    'key_bindings_registry': registry,         # readline-style tab completion
    'complete_while_typing': False,            # ? docs say necessary
    'get_prompt_tokens': get_prompt_tokens,
    'get_bottom_toolbar_tokens': get_bottom_toolbar_tokens,
    'style': ts_prompt_toolbar_style
} # end kwargs


######################################################
### click-repl
### https://github.com/click-contrib/click-repl
### included in entirety here for ease of modification
### will attempt to ensure any useful modifications are
### donated back to the official project
"""
Copyright (c) 2014-2015 Markus Unterwaditzer & contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from collections import defaultdict
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.shortcuts import prompt
import click
import click._bashcomplete
import click.parser
import os
import shlex
import sys
import six


#__version__ = '0.1.1'  # click-repl version when forked

_internal_commands = dict()


class InternalCommandException(Exception):
    pass


class ExitReplException(InternalCommandException):
    pass



def _register_internal_command(names, target, description=None):
    if not hasattr(target, '__call__'):
        raise ValueError('Internal command must be a callable')

    if isinstance(names, six.string_types):
        names = [names]
    elif not isinstance(names, (list, tuple)):
        raise ValueError('"names" must be a string or a list / tuple')

    for name in names:
        _internal_commands[name] = (target, description)


def _get_registered_target(name, default=None):
    target_info = _internal_commands.get(name)
    if target_info:
        return target_info[0]
    return default


def _exit_internal():
    raise ExitReplException()


def _help_internal():
    formatter = click.HelpFormatter()
    formatter.write_heading('REPL help')
    formatter.indent()
    with formatter.section('External Commands'):
        formatter.write_text('prefix external commands with "!"')
    with formatter.section('Internal Commands'):
        formatter.write_text('prefix internal commands with ":"')
        info_table = defaultdict(list)
        for mnemonic, target_info in six.iteritems(_internal_commands):
            info_table[target_info[1]].append(mnemonic)
        formatter.write_dl(
            (', '.join((':{0}'.format(mnemonic)
                        for mnemonic in sorted(mnemonics))), description)
            for description, mnemonics in six.iteritems(info_table)
        )
    return formatter.getvalue()


_register_internal_command(['q', 'quit', 'exit'], _exit_internal,
                           'exits the repl')
_register_internal_command(['?', 'h', 'help'], _help_internal,
                           'displays general help information')


class ClickCompleter(Completer):
    def __init__(self, cli):
        self.cli = cli

    def get_completions(self, document, complete_event=None):
        # Code analogous to click._bashcomplete.do_complete

        try:
            args = shlex.split(document.text_before_cursor)
        except ValueError:
            # Invalid command, perhaps caused by missing closing quotation.
            return

        cursor_within_command = \
            document.text_before_cursor.rstrip() == document.text_before_cursor

        if args and cursor_within_command:
            # We've entered some text and no space, give completions for the
            # current word.
            incomplete = args.pop()
        else:
            # We've not entered anything, either at all or for the current
            # command, so give all relevant completions for this context.
            incomplete = ''

        ctx = click._bashcomplete.resolve_ctx(self.cli, '', args)
        if ctx is None:
            return

        choices = []
        for param in ctx.command.params:
            if not isinstance(param, click.Option):
                continue
            for options in (param.opts, param.secondary_opts):
                for o in options:
                    choices.append(Completion(o, -len(incomplete),
                                              display_meta=param.help))

        if isinstance(ctx.command, click.MultiCommand):
            for name in ctx.command.list_commands(ctx):
                command = ctx.command.get_command(ctx, name)
                choices.append(Completion(
                    name,
                    -len(incomplete),
                    display_meta=getattr(command, 'short_help')
                ))

        for item in choices:
            if item.text.startswith(incomplete):
                yield item


def repl(
        old_ctx,
        prompt_kwargs=None,
        allow_system_commands=True,
        allow_internal_commands=True,
        allow_secondary_prompt=False,
        secondary_prompt='>> '
):
    """
    Start an interactive shell. All subcommands are available in it.

    :param old_ctx: The current Click context.
    :param prompt_kwargs: Parameters passed to
        :py:func:`prompt_toolkit.shortcuts.prompt`.
    :param allow_secondary_prompt: Provides multiline
        input in the case of unmatched quotes.
    :param secondary_prompt: The prompt to display
        to the user during multiline input.

    If stdin is not a TTY, no prompt will be printed, but only commands read
    from stdin.

    """
    # parent should be available, but we're not going to bother if not
    group_ctx = old_ctx.parent or old_ctx
    group = group_ctx.command
    isatty = sys.stdin.isatty()

    # Delete the REPL command from those available, as we don't want to allow
    # nesting REPLs (note: pass `None` to `pop` as we don't want to error if
    # REPL command already not present for some reason).
    repl_command_name = old_ctx.command.name
    available_commands = group_ctx.command.commands
    available_commands.pop(repl_command_name, None)

    if isatty:
        prompt_kwargs = prompt_kwargs or {}
        # don't set 'message' if 'get_prompt_tokens' is set
        if not prompt_kwargs.get('get_prompt_tokens', None):
            prompt_kwargs.setdefault('message', u'> ')
        history = prompt_kwargs.pop('history', None) \
            or InMemoryHistory()
        completer = prompt_kwargs.pop('completer', None) \
            or ClickCompleter(group)

        def get_command():
            return prompt(completer=completer, history=history,
                          **prompt_kwargs)
    else:
        get_command = sys.stdin.readline

    while True:
        try:
            command = get_command()
        except KeyboardInterrupt:
            continue
        except EOFError:
            break

        if not command:
            if isatty:
                continue
            else:
                break

        if allow_system_commands and dispatch_repl_commands(command):
            continue

        if allow_internal_commands:
            try:
                result = handle_internal_commands(command)
                if isinstance(result, six.string_types):
                    click.echo(result)
                    continue
            except ExitReplException:
                break

        try:
            args = shlex.split(command)
        except ValueError as e:
            if not allow_secondary_prompt:
                click.echo("{}: {}".format(type(e).__name__, e))
                continue
            else:
                try:
                    args = _secondary_prompt_helper(command, secondary_prompt)
                except KeyboardInterrupt:
                    continue

        logger.debug("command: {}".format(repr(args)))
        try:
            with group.make_context(None, args, parent=group_ctx) as ctx:
                group.invoke(ctx)
                ctx.exit()
        except click.ClickException as e:
            e.show()
        except SystemExit:
            pass
        except KeyboardInterrupt:
            continue
        except ExitReplException:
            break
        except Exception as e:
            click.echo("{}: {}".format(type(e).__name__, e))


def register_repl(group, name='repl'):
    """Register :func:`repl()` as sub-command *name* of *group*."""
    group.command(name=name)(click.pass_context(repl))


def dispatch_repl_commands(command):
    """Execute system commands entered in the repl.

    System commands are all commands starting with "!".

    """
    if command.startswith('!'):
        os.system(command[1:])
        return True

    return False


def handle_internal_commands(command):
    """Run repl-internal commands.

    Repl-internal commands are all commands starting with ":".

    """
    if command.startswith(':'):
        target = _get_registered_target(command[1:], default=None)
        if target:
            return target()


def _secondary_prompt_helper(command, ps2='>> '):
    """Collect additional lines."""
    args = None
    while True:
        addcommand = prompt(ps2)
        # assuming we're here because intentionally unmatched quotes,
        # the user probably wants their newlines. add back.
        command = '\n'.join(( command, addcommand ))
        try:
            args = shlex.split(command)
            break
        except ValueError:
            continue
    return args


