import os
import re
import ast
import json
import time
import shutil
import datetime
import numpy as np
import zipfile
import pytest

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


class TestCancel(test_base.TestBase):

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

    def test_cancel_local(self):
        started = time.time()

        # cancel RUN
        self.xt('xt run --target=local tests/fixtures/xtTestApp.py --epochs=100')
        self.xt('xt cancel run $lastrun')

        # cancel JOB
        self.xt('xt run --target=local tests/fixtures/xtTestApp.py --epochs=100')
        self.xt('xt cancel job $lastjob')

        # cancel ALL LOCAL
        self.xt('xt run --target=local tests/fixtures/xtTestApp.py --epochs=100')
        self.xt('xt cancel all local')

        # cancel with NO RUNS
        self.xt('xt cancel run $lastrun')
        self.xt('xt cancel job $lastjob ')
        self.xt('xt cancel all local')

        self.assert_no_error_runs()

        elapsed = time.time() - started
        print("\nend of LOCAL cancel tests, elapsed={:.0f} secs".format(elapsed))

    @pytest.mark.philly_test
    @pytest.mark.skipif(os.environ.get("PHILLY_TESTS", "false").lower() != "true", reason="Skip Philly tests unless explicitly called")
    def test_cancel_philly(self):
        started = time.time()

        philly_delay = 10

        # cancel RUN
        self.xt('xt run --target=philly tests/fixtures/xtTestApp.py --epochs=100')
        time.sleep(philly_delay)
        self.xt('xt cancel run $lastrun')

        # cancel JOB
        self.xt('xt run --target=philly tests/fixtures/xtTestApp.py --epochs=100')
        time.sleep(philly_delay)
        self.xt('xt cancel job $lastjob')

        # cancel ALL PHILLY
        self.xt('xt run --target=philly tests/fixtures/xtTestApp.py --epochs=100')
        time.sleep(philly_delay)
        self.xt('xt cancel all philly')

        # cancel with NO RUNS
        self.xt('xt cancel run $lastrun')
        self.xt('xt cancel job $lastjob ')
        self.xt('xt cancel all philly')

        # view status (all runs cancelled)
        self.xt('xt view status --target=philly')

        self.assert_no_error_runs()

        elapsed = time.time() - started
        print("\nend of PHILLY cancel tests, elapsed={:.0f} secs".format(elapsed))

    def test_cancel_batch(self):
        started = time.time()

        # cancel RUN
        self.xt('xt run --target=batch tests/fixtures/xtTestApp.py --epochs=100')
        self.xt('xt cancel run $lastrun')

        # cancel JOB
        self.xt('xt run --target=batch tests/fixtures/xtTestApp.py --epochs=100')
        self.xt('xt cancel job $lastjob')

        # cancel ALL BATCH
        self.xt('xt run --target=batch tests/fixtures/xtTestApp.py --epochs=100')
        self.xt('xt cancel all batch')

        # cancel with NO RUNS
        self.xt('xt cancel run $lastrun')
        self.xt('xt cancel job $lastjob ')
        self.xt('xt cancel all batch')

        # view status (all runs cancelled)
        self.xt('xt view status --target=batch')

        self.assert_no_error_runs()

        elapsed = time.time() - started
        print("\nend of BATCH cancel tests, elapsed={:.0f} secs".format(elapsed))

    def test_cancel_aml(self):
        started = time.time()

        # cancel RUN
        self.xt('xt run --target=aml tests/fixtures/xtTestApp.py --epochs=100')
        self.xt('xt cancel run $lastrun')

        # cancel JOB
        self.xt('xt run --target=aml tests/fixtures/xtTestApp.py --epochs=100')
        self.xt('xt cancel job $lastjob')

        # cancel ALL AML
        self.xt('xt run --target=aml tests/fixtures/xtTestApp.py --epochs=100')
        self.xt('xt cancel all aml')

        # cancel with NO RUNS
        self.xt('xt cancel run $lastrun')
        self.xt('xt cancel job $lastjob ')
        self.xt('xt cancel all aml')

        # view status (all runs cancelled)
        self.xt('xt view status --target=aml')

        self.assert_no_error_runs()

        elapsed = time.time() - started
        print("\nend of AML cancel tests, elapsed={:.0f} secs".format(elapsed)) 
