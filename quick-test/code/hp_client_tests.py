#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# hp_client_tests.py: develop and test code to process HP specs and run generation on the XT client
import os

from xtlib import utils
from xtlib import errors
from xtlib import file_utils
from xtlib.hparams.hp_client import HPClient

class HpClientTest():
    def __init__(self):
        self.reset_count()

    def reset_count(self):
        self._assert_count = 0

    def _assert(self, value):
        assert value
        self._assert_count  += 1

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
            fn_hpsearch_server = "hp_search_ex.ymal"
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


def test_search_type(hp_test, cmd_line, fn_hpsearch, search_type):

    run_cmds = hp_test.test(search_type=search_type, static_search=True, cmd_line=cmd_line, fn_hpsearch=fn_hpsearch, 
        num_runs=None, max_runs=None, node_count=1, option_prefix="--")

    if search_type == "grid":
        hp_test._assert( len(run_cmds) == 30 )
    else:
        hp_test._assert( len(run_cmds) == 1 )

    run_cmds = hp_test.test(search_type=search_type, static_search=True, cmd_line=cmd_line, fn_hpsearch=fn_hpsearch, 
        num_runs=None, max_runs=25, node_count=1, option_prefix="--")
    hp_test._assert( len(run_cmds) == 25 )

    run_cmds = hp_test.test(search_type=search_type, static_search=True, cmd_line=cmd_line, fn_hpsearch=fn_hpsearch, 
        num_runs=150, max_runs=200, node_count=1, option_prefix="--")
    hp_test._assert( len(run_cmds) == 150 )

# def test_search_nodes(hp_test, cmd_line, fn_hpsearch, search_type):

#     test_search_type(hp_test, cmd_line, fn_hpsearch, search_type, node_count=1)
#     test_search_type(hp_test, cmd_line, fn_hpsearch, search_type, node_count=2)
#     test_search_type(hp_test, cmd_line, fn_hpsearch, search_type, node_count=3)

def main():
    cmd_line = "python myApp.py --epochs=30 --lr=[.01, .02, .03] --optimizer=[sgd, adam] --beta=[$linspace(.1, .9, 5)]"
    fn_hpsearch = "../cmdlineTest/code/miniSweeps.yaml"

    hp_test = HpClientTest()

    test_search_type(hp_test, cmd_line, fn_hpsearch, "grid")
    test_search_type(hp_test, cmd_line, fn_hpsearch, "random")

    return hp_test._assert_count

if __name__ == "__main__":
    main()