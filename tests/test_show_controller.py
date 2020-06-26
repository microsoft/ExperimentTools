import os
import pytest
import subprocess
import time
from xtlib import pc_utils
import xtlib.xt_cmds as xt_cmds
import test_base


class TestShowController(test_base.TestBase):

    def setup_class(cls):
        internal_text_file = open("tests/fixtures/internal.yaml", "r")
        cls.internal_text = internal_text_file.read()
        internal_text_file.close()
        print("Setup Class")

    def teardown_class(cls):
        cls.internal_text = None
        print("Teardown class")

    def setup(self):
        print("Setup for test")

    def teardown(self):
        print("Teardown for test")

    def show_controller_linux(self):
        """
        This tests that setting show-controller to true will spawn a new Gnome
        terminal at location ~/.xt/cwd
        """

        p = subprocess.Popen(
            ("bash -c 'if xset q &> /dev/null; then "
             "xdotool search --onlyvisible -class gnome-terminal getwindowname %@ | "
             "wc -l; else echo 0; fi'"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        gnome_terminal_before_count = int(p.stdout.read().decode())

        cmd = "xt run --monitor=new --target=local tests/fixtures/miniMnist.py"
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

    def show_controller_windows(self):
        pass

    @pytest.mark.skip(reason="Skip as it involves GUI")
    def test_show_controller(self):
        if pc_utils.has_gui():
            if not pc_utils.is_windows():
                self.show_controller_linux()
            else:
                self.show_controller_windows()
