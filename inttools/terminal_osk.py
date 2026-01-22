#!/usr/bin/env python3
"""
On-screen terminal UI using urwid.
Shows output on top and a keyboard/input area at the bottom.
"""

import os
import shlex
import subprocess
import sys
from os import get_terminal_size

import urwid
from urwid.widget import Text, Divider
from urwid.container import Columns, Frame, GridFlow, Overlay, Pile
from urwid.decoration import AttrMap, AttrWrap, Filler, Padding
from urwid.graphics import LineBox
from urwid.signals import connect_signal
from urwid.command_map import ACTIVATE
try:
    from urwid.container import WidgetWrap
except Exception:
    from urwid.widget import WidgetWrap, FLOW

ASCII_BLOCK = '█'
SMALL_SCREEN_COLS = 60
SMALL_SCREEN_ROWS = 26
MAX_OUTPUT_LINES = 800

PALETTE = [
    ('input',      'dark gray', 'light gray'),
    ('input text', 'black',     'light gray'),
    ('prompt',     'dark red',  'dark cyan'),
    ('body',       'black',     'light gray'),
    ('bg',         'white',     'dark blue'),
    ('focus key',  'white',     'dark blue'),
    ('header',     'light cyan','dark blue'),
    ('button',     'black',     'light gray'),
    ('selected',   'white',     'dark blue'),
    ('label',      'dark gray', 'light gray'),
    ('label selected', 'yellow', 'dark blue'),
    ('error',      'dark red',  'light gray'),
]


class CenteredButton(WidgetWrap):
    signals = ["click"]

    def selectable(self):
        return True

    def sizing(self):
        return frozenset([FLOW])

    def __init__(self, label, on_press=None, user_data=None, delimiters=True):
        self._label = Text(label, align='center')
        if delimiters:
            cols = Columns(
                [
                    ('fixed', 1, Text("<")),
                    self._label,
                    ('fixed', 1, Text(">"))
                ],
                dividechars=1)
        else:
            cols = self._label
        super().__init__(cols)
        if on_press:
            connect_signal(self, 'click', on_press, user_data)

    def set_label(self, label):
        self._label.set_text(label)

    def get_label(self):
        return self._label.text

    label = property(get_label)

    def keypress(self, size, key):
        if self._command_map[key] != ACTIVATE or key == ' ':
            return key
        self._emit('click')

    def mouse_event(self, size, event, button, x, y, focus):
        return False


class KeyButton(CenteredButton):
    def __init__(self, text, primary=None, secondary=None, on_press=None, user_data=None):
        super().__init__(text, on_press, user_data, delimiters=False)
        if primary is None:
            self.primary_val = text
        else:
            self.primary_val = primary
        if secondary is None and len(text) == 1:
            self.secondary_val = text.upper()
        else:
            self.secondary_val = secondary

    def shift(self, shifted):
        if (shifted
                and self.secondary_val is not None
                and len(self.secondary_val.strip()) > 0):
            self.set_label(self.secondary_val)
        if (not shifted
                and self.primary_val is not None
                and len(self.primary_val.strip()) > 0):
            self.set_label(self.primary_val)

    def get_value(self, shifted):
        if shifted and self.secondary_val:
            return self.secondary_val
        if not shifted and self.primary_val:
            return self.primary_val


class WrappableColumns(Columns):
    def keypress(self, size, key):
        if self.__super.keypress(size, key):
            if key not in ('left', 'right'):
                return key
            if key in ('left'):
                widgets = list(range(len(self.contents) - 1, -1, -1))
            else:
                widgets = list(range(0, len(self.contents)))
            for i in widgets:
                if not self.contents[i][0].selectable():
                    continue
                self.focus_position = i
                break


class ViewExit(Exception):
    pass


class TerminalUI:
    def __init__(self, workdir, small_display, cols, rows):
        self.workdir = workdir
        self.home_dir = workdir
        self.small_display = small_display
        self.screen_cols = cols
        self.screen_rows = rows
        self.shifted = False
        self.sudo_pass = ""
        self.pending_cmd = None
        self.mode = "cmd"
        self.input_text = ""

        self.output_walker = urwid.SimpleListWalker([])
        self.output_list = urwid.ListBox(self.output_walker)
        self.output_box = LineBox(self.output_list, title="Output")

        self.input_display = Text([('input text', ''), ('prompt', ASCII_BLOCK)])
        input_box = LineBox(AttrWrap(self.input_display, 'input'), title="Input")

        self.keys = []
        osk = self.build_osk()
        osk = Padding(osk, 'center', ('relative', 100), min_width=10)
        osk_box = Filler(osk, valign='top')
        try:
            _, osk_rows = osk.pack((self.screen_cols,))
        except Exception:
            osk_rows = 12
        max_osk_rows = max(6, self.screen_rows - 10)
        osk_rows = max(6, min(osk_rows, max_osk_rows))
        osk_box = urwid.BoxAdapter(osk_box, osk_rows)

        run_btn = self.setup_button("Run", self.run_button)
        clear_btn = self.setup_button("Clear", self.clear_button)
        exit_btn = self.setup_button("Exit", self.exit_button)
        buttons = GridFlow([run_btn, clear_btn, exit_btn], 10, 2, 0, 'center')

        input_area = Pile([
            ('pack', input_box),
            ('pack', Divider()),
            osk_box,
            ('pack', Divider()),
            ('pack', buttons),
        ])
        input_area = LineBox(input_area, title="Command")
        input_area = AttrWrap(input_area, 'bg')
        input_area = Filler(input_area, valign='top')

        try:
            _, input_rows = input_area.pack((self.screen_cols,))
        except Exception:
            input_rows = osk_rows + 6
        max_input_rows = max(10, self.screen_rows - 3)
        input_rows = max(8, min(input_rows, max_input_rows))
        footer = urwid.BoxAdapter(input_area, input_rows)

        self.header_text = Text(self.header_line(), align='center')
        header = AttrWrap(self.header_text, 'header')
        body = AttrWrap(self.output_box, 'bg')
        self.frame = Frame(body, header=header, footer=footer, focus_part='body')

        self.append_output("HoffmanOS terminal ready.")
        self.append_output("Use the on-screen keyboard and press Run.")
        self.append_output("Type 'exit' to quit.")
        self.render_input()

    def header_line(self):
        suffix = "SUDO" if self.mode == "sudo" else "CMD"
        return f"HoffmanOS Terminal - {self.workdir} [{suffix}]"

    def update_header(self):
        self.header_text.set_text(self.header_line())

    def setup_button(self, label, callback):
        button = CenteredButton(('label', label), callback, delimiters=True)
        return AttrMap(button, {None: 'button'}, {None: 'selected', 'label': 'label selected'})

    def build_osk(self):
        Key = self.add_osk_key
        osk = Pile([
            WrappableColumns([
                (1, Text(" ")),
                (3, Key('`', shifted='~')),
                (3, Key('1', shifted='!')),
                (3, Key('2', shifted='@')),
                (3, Key('3', shifted='#')),
                (3, Key('4', shifted='$')),
                (3, Key('5', shifted='%')),
                (3, Key('6', shifted='^')),
                (3, Key('7', shifted='&')),
                (3, Key('8', shifted='*')),
                (3, Key('9', shifted='(')),
                (3, Key('0', shifted=')')),
                (3, Key('-', shifted='_')),
                (3, Key('=', shifted='+')),
                (1, Text(" ")),
            ], 0),
            Divider(),
            WrappableColumns([
                (3, Key('q')),
                (3, Key('w')),
                (3, Key('e')),
                (3, Key('r')),
                (3, Key('t')),
                (3, Key('y')),
                (3, Key('u')),
                (3, Key('i')),
                (3, Key('o')),
                (3, Key('p')),
                (3, Key('[', shifted='{')),
                (3, Key(']', shifted='}')),
                (3, Key('\\', shifted='|')),
            ], 0),
            Divider(),
            WrappableColumns([
                (3, Text(" ")),
                (3, Key('a')),
                (3, Key('s')),
                (3, Key('d')),
                (3, Key('f')),
                (3, Key('g')),
                (3, Key('h')),
                (3, Key('j')),
                (3, Key('k')),
                (3, Key('l')),
                (3, Key(';', shifted=':')),
                (3, Key('\'', shifted='"')),
            ], 0),
            Divider(),
            WrappableColumns([
                (4, Text(" ")),
                (3, Key('z')),
                (3, Key('x')),
                (3, Key('c')),
                (3, Key('v')),
                (3, Key('b')),
                (3, Key('n')),
                (3, Key('m')),
                (3, Key(',', shifted='<')),
                (3, Key('.', shifted='>')),
                (3, Key('/', shifted='?')),
            ], 0),
            Divider(),
            WrappableColumns([
                (1, Text(" ")),
                (9, Key('↑ Shift', shifted='↑ SHIFT', callback=self.shift_key_press)),
                (2, Text(" ")),
                (15, Key('Space', value=' ', shifted=' ')),
                (2, Text(" ")),
                (10, Key('Delete ←', callback=self.bksp_key_press)),
            ], 0),
            Divider(),
        ])

        if self.small_display and len(osk.contents) > 0:
            osk.contents.pop(len(osk.contents) - 1)

        return osk

    def add_osk_key(self, key, value=None, shifted=None, callback=None):
        if callback is None:
            callback = self.def_key_press
        btn = KeyButton(key, primary=value, secondary=shifted, on_press=callback)
        self.keys.append(btn)
        return AttrWrap(btn, None, 'focus key')

    def shift_key_press(self, key=None):
        self.shifted = not self.shifted
        for b in self.keys:
            b.shift(self.shifted)

    def def_key_press(self, key):
        value = key.get_value(self.shifted)
        if value is None:
            return
        self.input_text += value
        if self.shifted:
            self.shift_key_press()
        self.render_input()

    def bksp_key_press(self, key=None):
        if len(self.input_text) > 0:
            self.input_text = self.input_text[:-1]
            self.render_input()

    def render_input(self):
        if self.mode == "sudo":
            shown = "*" * len(self.input_text)
        else:
            shown = self.input_text
        self.input_display.set_text([('input text', shown), ('prompt', ASCII_BLOCK)])
        self.update_header()

    def append_output(self, text):
        if text is None:
            return
        lines = text.splitlines()
        if not lines:
            lines = [""]
        for line in lines:
            self.output_walker.append(Text(line))
        if len(self.output_walker) > MAX_OUTPUT_LINES:
            del self.output_walker[0:len(self.output_walker) - MAX_OUTPUT_LINES]
        self.output_list.set_focus(len(self.output_walker) - 1)

    def clear_output(self):
        self.output_walker.clear()
        self.append_output("Output cleared.")

    def exit_button(self, btn=None):
        raise urwid.ExitMainLoop()

    def clear_button(self, btn=None):
        self.clear_output()

    def run_button(self, btn=None):
        if self.mode == "sudo":
            if not self.input_text:
                return
            self.sudo_pass = self.input_text
            self.input_text = ""
            self.mode = "cmd"
            self.render_input()
            if self.pending_cmd:
                cmd = self.pending_cmd
                self.pending_cmd = None
                self.run_command(cmd)
            return

        cmd = self.input_text.strip()
        if not cmd:
            return
        self.input_text = ""
        self.render_input()
        self.run_command(cmd)

    def parse_cd(self, cmd):
        try:
            tokens = shlex.split(cmd)
        except ValueError:
            return None
        if not tokens or tokens[0] != "cd":
            return None
        target = self.home_dir if len(tokens) == 1 else tokens[1]
        target = os.path.expanduser(target)
        if not os.path.isabs(target):
            target = os.path.join(self.workdir, target)
        return os.path.abspath(target)

    def parse_sudo(self, cmd):
        try:
            tokens = shlex.split(cmd)
        except ValueError:
            return None
        if not tokens or tokens[0] != "sudo":
            return None
        opts = []
        idx = 1
        end_opts = False
        options_with_arg = {"-u", "-g", "-h", "-p", "-C", "-t", "-a"}
        while idx < len(tokens):
            tok = tokens[idx]
            if end_opts:
                break
            if tok == "--":
                end_opts = True
                idx += 1
                break
            if tok.startswith("-"):
                opts.append(tok)
                idx += 1
                if tok in options_with_arg and idx < len(tokens):
                    opts.append(tokens[idx])
                    idx += 1
                continue
            break
        cmd_tokens = tokens[idx:]
        return opts, cmd_tokens

    def run_command(self, cmd):
        self.append_output(f"$ {cmd}")

        if cmd in ("exit", "quit"):
            raise urwid.ExitMainLoop()

        if cmd == "clear":
            self.clear_output()
            return

        new_dir = self.parse_cd(cmd)
        if new_dir is not None:
            if os.path.isdir(new_dir):
                self.workdir = new_dir
                self.append_output(f"Directory: {self.workdir}")
                self.update_header()
            else:
                self.append_output(f"Directory not found: {new_dir}")
            return

        sudo_info = self.parse_sudo(cmd)
        if sudo_info is not None:
            opts, cmd_tokens = sudo_info
            if "-k" in opts:
                self.sudo_pass = ""
            if not self.sudo_pass and cmd_tokens:
                self.mode = "sudo"
                self.pending_cmd = cmd
                self.input_text = ""
                self.append_output("Enter sudo password and press Run.")
                self.render_input()
                return

            opts_clean = []
            idx = 0
            while idx < len(opts):
                if opts[idx] == "-p" and (idx + 1) < len(opts):
                    idx += 2
                    continue
                opts_clean.append(opts[idx])
                idx += 1

            if "-S" not in opts_clean:
                opts_clean.append("-S")
            opts_clean.extend(["-p", ""])

            sudo_args = ["sudo"] + opts_clean
            if cmd_tokens:
                cmd_str = shlex.join(cmd_tokens)
                sudo_args += ["bash", "--noprofile", "--norc", "-c", cmd_str]

            result = subprocess.run(
                sudo_args,
                input=(self.sudo_pass + "\n") if self.sudo_pass else None,
                text=True,
                capture_output=True,
                cwd=self.workdir
            )
            output = (result.stdout or "") + (result.stderr or "")
            if result.returncode != 0 and "sorry, try again" in output.lower():
                self.sudo_pass = ""
                self.mode = "sudo"
                self.pending_cmd = cmd
                self.append_output(output.rstrip())
                self.append_output("Sudo password incorrect. Enter again.")
                self.render_input()
                return
            self.append_output(output.rstrip() if output.strip() else f"Exit {result.returncode}")
            return

        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-c", cmd],
            capture_output=True,
            text=True,
            cwd=self.workdir
        )
        output = (result.stdout or "") + (result.stderr or "")
        if output.strip():
            self.append_output(output.rstrip())
        else:
            self.append_output(f"Exit {result.returncode}")

    def unhandled_input(self, key):
        if key in ('esc',):
            raise urwid.ExitMainLoop()
        if key == 'enter':
            self.run_button()
            return
        if key == 'backspace':
            self.bksp_key_press()
            return
        if isinstance(key, str) and len(key) == 1 and 32 <= ord(key) <= 126:
            self.input_text += key
            self.render_input()
            return

    def main(self):
        tty_in = open('/dev/tty1', 'r')
        screen = urwid.raw_display.Screen(input=tty_in)
        loop = urwid.MainLoop(self.frame, PALETTE, screen=screen, unhandled_input=self.unhandled_input)
        loop.run()


def main():
    default_dir = "/home/ark"
    if len(sys.argv) > 1 and sys.argv[1].strip():
        default_dir = sys.argv[1].strip()
    try:
        cols, rows = get_terminal_size(1)
    except OSError:
        try:
            cols, rows = get_terminal_size(sys.stdin.fileno())
        except OSError:
            cols, rows = 80, 24
    small = cols < SMALL_SCREEN_COLS or rows < SMALL_SCREEN_ROWS
    ui = TerminalUI(default_dir, small, cols, rows)
    ui.main()


if __name__ == "__main__":
    main()
