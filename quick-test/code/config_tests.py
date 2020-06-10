#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# config_tests.py: test out tag-related commands

import os
import time

import yaml
from xtlib import constants
from xtlib import file_utils
from test_base import TestBase
from xtlib.helpers import xt_config
from xtlib.impl_utilities import ImplUtilities
from xtlib.impl_shared import ImplShared

class ConfigTests(TestBase):
    def __init__(self):
        return super(ConfigTests, self).__init__("ConfigTests")

    def ensure_file_exists(self, fn):
        self._assert( os.path.exists(fn) )

    def do_merge(self, res_dir):

        internal_text = '''
compute-targets: 
    aml-internal: {service: "aml-temp-ws", compute: "temp-compute", vm-size: "Standard_NC6", nodes: 1, low-pri: false, setup: "aml"} 
'''
        # merge text with default config 
        xt_config.merge_internal_xt_config(internal_text)

        # now test xt after the merge
        output = self.test_cmd("xt list targets")
        self.assert_names(output, ["local", "local-docker", "aml-internal"])

        # check for expected files in resource dir
        fn_default = os.path.join(res_dir, constants.FN_DEFAULT_CONFIG)
        self.ensure_file_exists(fn_default)

        fn_orig_default = os.path.join(res_dir, constants.FN_ORIG_DEFAULT)
        self.ensure_file_exists(fn_orig_default)

        fn_internal_config = os.path.join(res_dir, constants.FN_INTERNAL_CONFIG)
        self.ensure_file_exists(fn_internal_config)

    def merge_tests(self):
        # zap resources dir
        res_dir = xt_config.get_resource_dir()
        file_utils.zap_dir(res_dir)

        # running first cmd here will force xt_default.yaml to be created in res dir
        output = self.test_cmd("xt list targets")

        # check output of list targets (ensure: batch found, philly-from-internal not found)
        self.assert_names(output, ["local", "local-docker"],["batch", "aml-internal"])

        # check for expected files in resource dir
        fn_default = os.path.join(res_dir, constants.FN_DEFAULT_CONFIG)
        self.ensure_file_exists(fn_default)

        # do the merge twice (to check for overwrite of readonly files)
        self.do_merge(res_dir)
        self.do_merge(res_dir)

    def philly_template_tests(self):
        impl_shared = ImplShared()
        impl_utilities = ImplUtilities(xt_config.XTConfig(), impl_shared.store)
        result = yaml.safe_load(impl_utilities.get_config_template("philly"))
        assert(result)
        assert("external-services" in result)
        self.assert_keys(result, ["external-services", "xt-services", "compute-targets", "dockers", "setups"])
        external_services = result["external-services"]
        self.assert_keys(external_services, ["philly", "philly-registry"])
        xt_services = result["xt-services"]
        self.assert_keys(xt_services, ["storage", "mongo", "vault", "target"])


    def run_tests(self):
        # self.merge_tests()
        self.philly_template_tests()

        print("ConfigTests completed: cmds executed={}, asserts tested={}".format(self.cmd_count, self.assert_count))
        return self.cmd_count + self.assert_count

def main():
    ct = ConfigTests()
    count = ct.run_tests()
    return count

if __name__ == "__main__":
    main()
