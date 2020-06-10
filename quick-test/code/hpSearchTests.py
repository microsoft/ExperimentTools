#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# hpSearchTests.py: test out hyperparmeter processing done by controller on standalone basis
import os
import datetime

from xtlib import utils
from xtlib import errors
from xtlib import file_utils
from xtlib.helpers import xt_config
from xtlib.hparams.hparam_search import HParamSearch
from xtlib.storage.store import Store

class HParamTests():
    def __init__(self, config, philly=1):
        self.config = config
        self.philly = philly
        self.reset_count()

    def reset_count(self):
        self._assert_count = 0

    def _assert(self, value):
        assert value
        self._assert_count  += 1

    def test_from_config(self, fn_config, config_file_text, search_type):
        print("-------------------------------")
        print("testing: {}, is_yaml={}".format(search_type, fn_config.endswith(".yaml")))

        hs = HParamSearch(False)

        cmd_parts = ["miniMnist.py"]
        store = Store(config=self.config)
        providers = self.config.get("providers")

        # If Philly usage disabled then remove from compute providers
        if self.philly == 0:
            del providers['compute']['philly']

        # mock up a context object
        context = utils.dict_to_object({"search_type": search_type, "providers": providers, "ws": "ws1",
            "aggregate_dest": "job", "dest_name": "job2000", "primary_metric": "test-acc", "maximize_metric": True,
            "option_prefix": None})

        # validate result
        arg_dict = hs.generate_hparam_set(fn_config, config_file_text, "run23.2", cmd_parts, store, context)
        self._assert( len(arg_dict) )

    def test_impl(self, search_type):
        # run test on impl
        test_dir = os.path.realpath(os.path.dirname(__file__))

        # using YAML config file #1
        fn_text = os.path.join(test_dir, "miniSweeps.yaml")
        config_text = file_utils.read_text_file(fn_text)
        self.test_from_config(fn_text, config_text, search_type)

        # using YAML config file #2
        fn_yaml = os.path.join(test_dir, "hp_search.yaml")
        yaml_text = file_utils.read_text_file(fn_yaml)
        self.test_from_config(fn_yaml, yaml_text, search_type)

def main(philly=1):
    # init environment
    config = xt_config.get_merged_config()
    tester = HParamTests(config)

    tester.test_impl("dgd")
    tester.test_impl("bayesian")
    tester.test_impl("random")
    
    return tester._assert_count

# MAIN
if __name__ == "__main__":
    main()
