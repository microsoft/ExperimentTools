# searchScaleTests.py: test out the scalability of our hyperparameter searching
import os
import time
import random
import logging
from threading import Thread

from xtlib import utils
from xtlib.run import Run
from xtlib import cmd_core
from xtlib import constants
from xtlib import file_utils
from xtlib.helpers import xt_config
from xtlib.storage.store import Store
from xtlib.hparams.hparam_search import HParamSearch

class SearchScaleTester():
    def __init__(self, config, store):
        '''
        test the scalability of runs during hyperparameter searching - involves:
            - storage blobs writing
            - MongoDB update of runs/metrics
            - MongoDB smart retrieval of run histories
        '''
        self.config = config
        self.store = store
        self.assert_count = 0

    def _assert(self, value):
        assert value
        self.assert_count  += 1
        self.threads = []

    def test_scale(self, delay, duration, concurrent, child_count, reports, search_type):
        self.threads = []
        started = time.time()

        job_id = self.store.create_job()

        # start threads
        for i in range(concurrent):
            run_worker = Thread(target=self.runner, args=(i, job_id, delay, duration, child_count, reports, search_type))
            run_worker.start()

            self.threads.append(run_worker)

        self.wait_for_all_threads()

        elapsed = time.time() - started
        print("{} runs, {} retryable MONGO errors, (elapsed: {:.2f} mins)".format(concurrent*child_count, self.store.mongo.retry_errors, elapsed/60))

    def wait_for_all_threads(self):
        for thread in self.threads:
            thread.join()

    def runner(self, concurrent_index, job_id, delay, duration, child_count, reports, search_type):
        ws_name = "quick-test"
        exper_name = "qtexper"

        fn = "code/miniSweeps.yaml"
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
            self._assert( "channels1" in hp_set )

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

            #print("  completing: {}".format(run_name))

def main(concurrent=15):
    config = xt_config.get_merged_config()
    store = Store(config=config)
    
    tester = SearchScaleTester(config, store)
    tester.test_scale(delay=10, duration=60, concurrent=concurrent, child_count=6, reports=5,
        search_type="random")

    count = tester.assert_count
    return count

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    utils.init_logging(constants.FN_QUICK_TEST_EVENTS, logger, "XT Quick-Test")
    main(concurrent=30)