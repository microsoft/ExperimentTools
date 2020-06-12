import os
import time
import random
import logging
import yaml
import test_base
from threading import Thread

from xtlib import utils
from xtlib.run import Run
from xtlib import cmd_core
from xtlib import constants
from xtlib import file_utils
from xtlib.helpers import xt_config
from xtlib.storage.store import Store
from xtlib.hparams.hparam_search import HParamSearch


class TestSearchScale(test_base.TestBase):

    def setup_class(cls):
        cls.config = xt_config.get_merged_config()
        cls.store = Store(config=cls.config)
        cls.delay = 10
        cls.duration = 60
        cls.concurrent = 15
        cls.child_count = 6
        cls.reports = 5
        cls.search_type = "random"
        print("Setup Class")

    def teardown_class(cls):
        cls.internal_text = None
        print("Teardown class")

    def setup(self):
        print("Setup for test")

    def teardown(self):
        print("Teardown for test")

    def test_scale(self):
        self.threads = []
        started = time.time()

        job_id = self.store.create_job()

        # start threads
        for i in range(self.concurrent):
            run_worker = Thread(target=self.runner, args=(i, job_id, self.delay, self.duration, self.child_count, self.reports, self.search_type))
            run_worker.start()

            self.threads.append(run_worker)

        self.wait_for_all_threads()

        elapsed = time.time() - started
        print("{} runs, {} retryable MONGO errors, (elapsed: {:.2f} mins)".format(self.concurrent*self.child_count, self.store.mongo.retry_errors, elapsed/60))

    def wait_for_all_threads(self):
        for thread in self.threads:
            thread.join()

    def runner(self, concurrent_index, job_id, delay, duration, child_count, reports, search_type):
        ws_name = "quick-test"
        exper_name = "qtexper"

        fn = "xtlib/fixtures/miniSweeps.yaml"
        yd = file_utils.load_yaml(fn)
        hd = yd[constants.HPARAM_DIST]
        
        # simulate a controller for each concurrent runner
        hparam_search = HParamSearch()

        for index in range(child_count):
            # create a new RUN record
            run_name = self.store.start_run(ws_name, exper_name=exper_name, is_parent=False, job_id=job_id, node_index=0,
                search_type=search_type, search_style="dynamic")

            os.environ["XT_RUN_NAME"] = run_name
            os.environ["XT_WORKSPACE_NAME"] = ws_name
            os.environ["XT_EXPERIMENT_NAME"] = exper_name

            fake_context = cmd_core.build_mock_context(self.config, job_id, ws_name, exper_name, run_name)
            metric_name = fake_context.primary_metric

            xt_run = Run(self.config, self.store, supress_normal_output=True)
            xt_run.direct_run = True
            xt_run.context = fake_context

            #print("  starting: concurrent_index={}, child_index={}".format(concurrent_index, index))
            # delay start
            sleep_time = delay * random.random()
            time.sleep(sleep_time)

            hp_set = xt_run.get_next_hp_set_in_search(hd, search_type, hparam_search=hparam_search)
            self.assertKeys(hp_set, ["channels1"])

            # log HPARAMS
            xt_run.log_hparams(hp_set)

            for i in range(reports):
                run_time = (duration/reports) * random.random()
                time.sleep(run_time)

                # log METRICS
                fake_metric = random.random()
                md =  {"epoch": 1+i, "acc": fake_metric}
                xt_run.log_metrics(md, step_name="epoch", stage="test")

            # mark the run as completed
            xt_run.close()
