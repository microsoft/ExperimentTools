import os
import time
import shutil
import pytest

from xtlib import utils
from xtlib import constants
from xtlib import file_utils
import xtlib.xt_cmds as xt_cmds
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

    def action_target(self, target):
        self.xt('xt run --target={} --data-action=download --model-action=download tests/fixtures/miniMnist.py --auto-download=0  --eval-model=1'.format(target))
        self.xt('xt run --target={} --data-action=mount --model-action=mount tests/fixtures/miniMnist.py --auto-download=0  --eval-model=1'.format(target))
        self.xt('xt run --target={} --data-action=mount --data-writable=1 --model-action=mount --model-writable=1 tests/fixtures/miniMnist.py --auto-download=0  --eval-model=1'.format(target))

    @pytest.mark.skipif(os.environ.get("PHILLY_TESTS", "false").lower() != "true", reason="Skip Philly tests unless explicitly called")
    def test_action_target_philly(self):
        self.action_target("philly")
        self.assert_no_error_runs()

    def test_action_target_batch(self):
        self.action_target("batch")
        self.assert_no_error_runs()

    def test_action_target_aml(self):
        self.action_target("aml")
        self.assert_no_error_runs()
