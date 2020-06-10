# test_base.py: a baseclass for quicktest classes
import os
import time

from xtlib import console
import xtlib.xt_run as xt_run

class TestBase():
    def __init__(self, test_name):
        self.test_name = test_name
        self.cmd_count = 0
        self.assert_count = 0

    def test_cmd(self, cmd, capture_output=True):
        print("-----------------------")
        print("{}: testing ({}): {}".format(self.test_name, 1+self.cmd_count, cmd))

        # capture and check results whenever possible
        if capture_output:
            console.set_capture(True)
            xt_run.main(cmd)
            output = console.set_capture(False)
        else:
            xt_run.main(cmd)
            output = None

        self.cmd_count += 1
        return output

    def _assert(self, value):
        assert value
        self.assert_count += 1

    def assert_names(self, output, names, not_names=None):
        output_text = "\n".join(output)

        if isinstance(names, str):
            self._assert(names in output_text)
        else:
            for name in names:
                self._assert(name in output_text)

        if not_names:
            if isinstance(not_names, str):
                self._assert(not(not_names in output_text))
            else:
                for name in not_names:
                    self._assert(not(name in output_text))

    def assert_keys(self, output_dict, keys):
        for key in keys:
            print(key)
            assert(key in output_dict)

