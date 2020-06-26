import os
import re
import ast
import json
import time
import shutil
import datetime
import numpy as np
import zipfile 

import test_base
from xtlib import pc_utils
from xtlib import utils
from xtlib import errors
from xtlib import console
from xtlib import file_utils
from xtlib.storage.store import Store
import xtlib.xt_cmds as xt_cmds
import xtlib.xt_run as xt_run
from xtlib.helpers import xt_config
from xtlib.helpers import file_helper
from xtlib.hparams.hparam_search import HParamSearch


class TestFeature(test_base.TestBase):

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

    def test_feature(self):
        started = time.time()

        # quick local run 
        self.xt('xt run tests/fixtures/xtTestApp.py --epochs=100')

        # workspaces
        self.xt('xt list workspaces')
        self.xt('view workspace')

        # experiments
        self.xt('xt list experiments')
        self.xt('view experiment')

        # monitor cmd
        self.xt('xt monitor $lastrun --escape=10')

        # cancel last job
        self.xt('xt cancel job $lastjob')

        elapsed = time.time() - started
        print("\nend of Feature tests, elapsed={:.0f} secs".format(elapsed))

        self.assert_no_error_runs()
