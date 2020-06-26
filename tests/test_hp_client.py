import os
import shutil
import test_base
from xtlib import utils
from xtlib import errors
from xtlib import file_utils
from xtlib.hparams.hp_client import HPClient


class HpClientTest(object):

    def __init__(self, test_dir):
        self.test_dir = test_dir

    def _assert(self, value):
        assert value

    def test(self, search_type, static_search, cmd_line, fn_hpsearch, num_runs, max_runs, node_count, option_prefix):

        dd = None
        run_cmds = []

        # build a distribution dict for hyperparameters to be searched
        if search_type != None:
            hp_client = HPClient()
            
            if option_prefix:
                dd, new_cmd_line = hp_client.extract_dd_from_cmdline(cmd_line, option_prefix)
                self._assert(len(list(dd)) > 0)

            if not dd and fn_hpsearch:
                dd = hp_client.yaml_to_dist_dict(fn_hpsearch)
                self._assert(len(list(dd)) > 0)

            if option_prefix:
                cmd_line_base, _ = cmd_line.split("--", 1)
            else:
                cmd_line_base = cmd_line

            # write parameters to YAML file for run record 
            # and use by dynamic search, if needed"
            fn_hpsearch_server = f"{self.test_dir}/hp_search_ex.yaml"
            yaml_data = hp_client.dd_to_yaml(dd)

            file_utils.save_yaml(yaml_data, fn_hpsearch_server)

            self._assert( os.path.exists(fn_hpsearch) )

            # should we preform the search now?
            if dd and static_search and search_type in ["grid", "random"]:

                # generate the static or grid param sets
                hp_sets = hp_client.generate_hp_sets(dd, search_type, num_runs, max_runs, node_count)
                self._assert( len(hp_sets) > 0 )
    
                run_cmds = hp_client.generate_runs(hp_sets, cmd_line_base)

            print("{} commands generated".format(len(run_cmds)))
        return run_cmds


class TestHPClient(test_base.TestBase):

    def setup_class(cls):
        cls.TEST_DIR = "tests/hp_client_tests"
        file_utils.ensure_dir_exists(cls.TEST_DIR)
        cls.cmd_line = "python myApp.py --epochs=30 --lr=[.01, .02, .03] --optimizer=[sgd, adam] --beta=[$linspace(.1, .9, 5)]"
        cls.fn_hpsearch = "tests/fixtures/miniSweeps.yaml"
        cls.hp_test = HpClientTest(cls.TEST_DIR)

    def teardown_class(cls):
        shutil.rmtree(cls.TEST_DIR)

    def setup(self):
        pass

    def teardown(self):
        pass

    def evaluate_search_type(self, search_type):
        run_cmds = self.hp_test.test(search_type=search_type, static_search=True, cmd_line=self.cmd_line, fn_hpsearch=self.fn_hpsearch, 
            num_runs=None, max_runs=None, node_count=1, option_prefix="--")

        if search_type == "grid":
            self.hp_test._assert( len(run_cmds) == 30 )
        else:
            self.hp_test._assert( len(run_cmds) == 1 )

        run_cmds = self.hp_test.test(search_type=search_type, static_search=True, cmd_line=self.cmd_line, fn_hpsearch=self.fn_hpsearch, 
            num_runs=None, max_runs=25, node_count=1, option_prefix="--")
        self.hp_test._assert( len(run_cmds) == 25 )

        run_cmds = self.hp_test.test(search_type=search_type, static_search=True, cmd_line=self.cmd_line, fn_hpsearch=self.fn_hpsearch, 
            num_runs=150, max_runs=200, node_count=1, option_prefix="--")
        self.hp_test._assert( len(run_cmds) == 150 )

    def test_grid_search(self):
        self.evaluate_search_type("grid")

    def test_random_search(self):
        self.evaluate_search_type("random")
