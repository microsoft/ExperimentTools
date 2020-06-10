#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# validate.py: validates XT CONFIG yaml files

import os
import time

from xtlib import file_utils
from xtlib import errors
from xtlib.helpers.validator import Validator
from xtlib.helpers.xt_config import get_default_config_path

def test():
    fn_schema = os.path.join(file_utils.get_xtlib_dir(), "helpers", "xt_config_schema.yaml")
    schema = file_utils.load_yaml(fn_schema)

    # a good first test: the default config file!
    fn_to_validate = get_default_config_path()

    default_config = file_utils.load_yaml(fn_to_validate)

    local_config = file_utils.load_yaml("xt_config.yaml")
    qt_config = file_utils.load_yaml("../quick-test/xt_config.yaml")

    validator = Validator()
    started = time.time()

    validator.validate(schema, default_config, True, "default config")
    validator.validate(schema, local_config, False, "local_config")
    validator.validate(schema, qt_config, False, "qt_config")

    elapsed = time.time() - started
    print("elapsed time: {:.4f} secs".format(elapsed))

if __name__ == "__main__":
    test()