#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# showControllerTest.py: test out the ability to spawn a gnome terminal
#                        with controller output there.
import os
import subprocess
import time
from xtlib import pc_utils
import xtlib.xt_cmds as xt_cmds


cmd_count = 0

def test_show_controller_linux():
    """
    This tests that setting show-controller to true will spawn a new Gnome
    terminal at location ~/.xt/cwd
    """
    global cmd_count

    p = subprocess.Popen(
        ("bash -c 'if xset q &> /dev/null; then "
         "xdotool search --onlyvisible -class gnome-terminal getwindowname %@ | "
         "wc -l; else echo 0; fi'"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    gnome_terminal_before_count = int(p.stdout.read().decode())

    cmd = "xt run --monitor=new code/miniMnist.py"
    xt_cmds.main(cmd)

    # We need to wait long enough for the gnome terminal to show up in the
    # list of open windows.
    time.sleep(5)
    p = subprocess.Popen(
        ("bash -c 'if xset q &> /dev/null; then "
         "xdotool search --onlyvisible -class gnome-terminal getwindowname %@ | "
         "wc -l; else echo 0; fi'"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    gnome_terminal_after_count = int(p.stdout.read().decode())

    # We should have one additional gnome terminal open with location ~/.xt/cwd
    print("Spawned {} additional gnome-terminals.".format(
        (gnome_terminal_after_count - gnome_terminal_before_count)))
    assert((gnome_terminal_after_count - gnome_terminal_before_count) == 1)
    cmd_count = cmd_count + 1


def test_show_controller_windows():
    pass


def main():
    if not pc_utils.is_windows():
        test_show_controller_linux()
    else:
        test_show_controller_windows()

    return cmd_count

    
if __name__ == "__main__":
    main()
