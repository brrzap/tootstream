import click


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


#from .toot_utils import *
#from .toot_print import *
