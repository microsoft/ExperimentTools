#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# key_press_checker.py: handles checking for a key being pressed without blocking on Windows and Linux

from xtlib import console
from xtlib import pc_utils

if pc_utils.is_windows():
    import msvcrt
else:
    import sys, select, tty, termios

class KeyPressChecker:
    def __init__(self):
        self.is_windows = pc_utils.is_windows()

    def __enter__(self):
        if not self.is_windows:
            # save off current stdin settings (LINE mode)
            self.old_settings = termios.tcgetattr(sys.stdin)

            # put stdin into CHAR mode
            tty.setcbreak(sys.stdin.fileno())

        return self

    def _get_windows_char(self, encoding):
        bb = msvcrt.getch()

        if bb == '\000' or bb == '\xe0':
            # special function key indicator; next keycode is actual key
            bb = msvcrt.getch()

        try:
            ch = bb.decode(encoding)
        except BaseException as ex:
            #console.print("KeyPressChecker exception decoding bb={}: {}".format(bb, ex))
            ch = ""

        return ch

    def getch_wait(self, encoding='utf-8'):
        '''
        Returns:
            string of single key pressed
        Description:
            wait for single key press and return its identity
        '''
        ch = None
        if self.is_windows:
            import msvcrt
            ch = self._get_windows_char(encoding)
        else:
            # linux
            ch = sys.stdin.read(1)
        return ch

    def getch_nowait(self, encoding='utf-8'):
        '''
        Returns:
            string of single key pressed, if any
        Description:
            check to see if a key has been pressed
        '''
        ch = None
        if self.is_windows:
            import msvcrt
            if msvcrt.kbhit():
                ch = self._get_windows_char(encoding)
        else:
            # linux
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                ch = sys.stdin.read(1)
        return ch

    def __exit__(self, type, value, traceback):
        if not self.is_windows:
            # restore stdin to LINE mode
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

def single_char_input(prompt=None, end="\n"):

    if prompt:
        console.print(prompt, end="", flush=True)

    try:
        with KeyPressChecker() as kpc:
            ch = kpc.getch_wait()
    except KeyboardInterrupt:
        ch = constants.CONTROL_C

    if end:
        console.print(end, end="")

    return ch
