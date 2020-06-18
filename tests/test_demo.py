import os
import time
import shutil
import pytest

from xtlib import utils
from xtlib import constants
from xtlib import file_utils
import xtlib.xt_cmds as xt_cmds
from xtlib.helpers.dir_change import DirChange
import test_base



class TestUpload(test_base.TestBase):

    def setup_class(cls):
        """
        Setup once for all tests
        """
        pass

    def teardown_class(cls):
        """
        Teardown once after all tests
        """
        pass

    def setup(self):
        """
        Setup per test
        """
        pass

    def teardown(self):
        """
        Teardown per test
        """
        pass

    def run_demo(self, philly, basic_mode):
        started = time.time()

        with DirChange("xtlib/demo_files"):
            import xt_demo
            args = "--auto --quick-test --philly={} --basic-mode={}".format(philly, basic_mode)
            arg_parts = args.split(" ")
            xt_demo.main(arg_parts)
            elapsed = time.time() - started
            print("\nend of xt_demo, elapsed={:.0f} secs".format(elapsed))

    def test_demo_basic_without_philly(self):
        basic_mode = 1
        philly = 0
        self.run_demo(philly, basic_mode)

    @pytest.mark.skip(reason="Skip Philly tests unless explicitly called")
    def test_demo_basic_with_philly(self):
        basic_mode = 1
        philly = 1
        self.run_demo(philly, basic_mode)

    def test_demo_advanced_without_philly(self):
        basic_mode = 0
        philly = 0
        started = time.time()
        self.run_demo(philly, basic_mode)

    @pytest.mark.skip(reason="Skip Philly tests unless explicitly called")
    def test_demo_advanced_with_philly(self):
        basic_mode = 0
        philly = 0
        started = time.time()
        self.run_demo(philly, basic_mode)
