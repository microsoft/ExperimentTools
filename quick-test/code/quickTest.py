#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# quickTest.py: runs a set of tests against XT
import os
import sys
import time
import shutil
import logging
import argparse

from xtlib import utils
from xtlib import errors
from xtlib import console
from xtlib import constants
from xtlib import file_utils
from xtlib import process_utils
from xtlib import pc_utils

from xtlib.storage.store import Store
import xtlib.xt_run as xt_run
from xtlib.helpers import xt_config
from xtlib.helpers.dir_change import DirChange

import config_tests
import uploadTests
import dirTests
import downloadTests
import deleteTests
import tagTests
import storageProviderTests
import hpSearchTests
import hp_client_tests
import runTests
import runIndexTests
import showControllerTest
import searchScaleTests

# global
logger = logging.getLogger(__name__)

mydir = os.getcwd()
cmd_count = 0 
test_group = None
cmd_delay = 0

def xt(cmd, capture_output=True):
    print("-------------------------------")
    if test_group:
        print("[{}] ".format(test_group), end="")

    print("xt cmd: " + cmd)
    print("cwd: ", os.getcwd())

    if cmd_delay:
        time.sleep(cmd_delay)

    if capture_output:
        console.set_capture(True)
        xt_run.main(cmd)
        output = console.set_capture(False)
    else:
        xt_run.main(cmd)
        output = None

    global cmd_count
    cmd_count += 1

    return output

def clear_cmd_count():
    global cmd_count
    cmd_count = 0

def set_test_group(group):
    global test_group
    test_group = group

    print("testing group: " + group)

def parse_args(argv=None):
    # Training settings
    parser = argparse.ArgumentParser(description='XT quick-test')

    parser.add_argument('--reset-workspace', default=1, type=int, help='should workspace be deleted and recreated')
    parser.add_argument('--philly', default=0, type=int, help='should Philly tests be run')
    parser.add_argument("tests", nargs="*", help="the tests to be run")

    if not argv:
        argv = sys.argv[1:]

    args = parser.parse_args(argv)
    print("quick-test: args=", args)

    return args

def quick_prep(reset_workspace):

    print("quick_prep")

    # first, ensure docker is working
    exit_code, output = process_utils.sync_run(["docker", "info"])
    if exit_code:
        errors.ConfigError("docker is not running")

    # delete azure errors file from previous run
    file_utils.zap_file("azure_errors.txt")

    config = xt_config.get_merged_config()
    store = Store(config=config)

    # get the quick-test workspace
    ws_name = config.get("general", "workspace")

    if reset_workspace:
        # must delete the xt-demo ws so we can import it
        if store.does_workspace_exist("xt-demo"):
            store.delete_workspace("xt-demo")

        # we require quick-test wd in storage tests
        if not store.does_workspace_exist("quick-test"):
            store.create_workspace("quick-test")

        if store.does_workspace_exist(ws_name):
            # use the quick-test xt_config.yaml file to set the workspace to a unused name
            raise Exception("Error: the quick-test workspace is already in use: {}".format(ws_name))

        # create the quicktest workspace name found in xt config file
        xt('xt create workspace {}'.format(ws_name))

        # import demo data files
        xt("xt import work ../xtlib/demo_files/xt-demo-archive.zip --job-prefix=xtd --overwrite")

    else:
        # for a partial quick-test run, we allow use of existing workspace
        pass

    return store, config

def run_xt_demo(philly=1, basic_mode=None):
    started = time.time()

    with DirChange("../xtlib/demo_files"):

        # launch XT demo
        # to find commands*.py files, we need to add "." to python path
        sys.path.insert(0, ".")
        
        from xtlib.demo_files import xt_demo

        args = "--auto --quick-test --philly={} --basic-mode={}".format(philly, basic_mode)
        arg_parts = args.split(" ")
        count = xt_demo.main(arg_parts)

        elapsed = time.time() - started
        print("\nend of xt_demo, elapsed={:.0f} secs".format(elapsed))    

    return count

def feature_tests():
    set_test_group("Feature tests")
    started = time.time()
    clear_cmd_count()

    # quick local run 
    xt('xt run code/xtTestApp.py --epochs=100')

    # workspaces
    xt('xt list workspaces')
    xt('view workspace')

    # experiments
    xt('xt list experiments')
    xt('view experiment')

    # TODO: uncomment these when VM10 is available
    # utility cmds
    # xt('xt addr vm10')
    # xt('xt ssh vm10 ls -lt')
    # xt('xt scp code/quickTest.py vm10:~/quickTest.py')

    # monitor cmd
    xt('xt monitor $lastrun --escape=10')

    # cancel last job
    xt('xt cancel job $lastjob')

    # turn this off since view status in being transitioned from client to xt_client usage
    # status monitor
    #xt('xt  view status  --escape=10 --active')

    elapsed = time.time() - started
    print("\nend of Feature tests, elapsed={:.0f} secs".format(elapsed))    

    return cmd_count

def local_cancel_tests():
    set_test_group("LOCAL cancel tests")
    started = time.time()
    clear_cmd_count()

    # clean LOCALHOST
    #xt('xt stop controller')

    # cancel RUN
    xt('xt run --target=local code/xtTestApp.py --epochs=100')
    xt('xt cancel run $lastrun')

    # cancel JOB
    xt('xt run --target=local code/xtTestApp.py --epochs=100')
    xt('xt cancel job $lastjob')

    # cancel ALL LOCAL
    xt('xt run --target=local code/xtTestApp.py --epochs=100')
    xt('xt cancel all local')

    # cancel with NO RUNS
    xt('xt cancel run $lastrun')
    xt('xt cancel job $lastjob ')
    xt('xt cancel all local')

    # Disabling test of xt view status for Basic Version
    # view status (all runs cancelled)
    # xt('xt view status --target=local')

    elapsed = time.time() - started
    print("\nend of LOCAL cancel tests, elapsed={:.0f} secs".format(elapsed))   

    return cmd_count 

def philly_cancel_tests():
    set_test_group("PHILLY cancel tests")
    started = time.time()
    clear_cmd_count()

    philly_delay = 10

    # cancel RUN
    xt('xt run --target=philly code/xtTestApp.py --epochs=100')
    time.sleep(philly_delay)
    xt('xt cancel run $lastrun')

    # cancel JOB
    xt('xt run --target=philly code/xtTestApp.py --epochs=100')
    time.sleep(philly_delay)
    xt('xt cancel job $lastjob')

    # cancel ALL PHILLY
    xt('xt run --target=philly code/xtTestApp.py --epochs=100')
    time.sleep(philly_delay)
    xt('xt cancel all philly')

    # cancel with NO RUNS
    xt('xt cancel run $lastrun')
    xt('xt cancel job $lastjob ')
    xt('xt cancel all philly')

    # view status (all runs cancelled)
    xt('xt view status --target=philly')

    elapsed = time.time() - started
    print("\nend of PHILLY cancel tests, elapsed={:.0f} secs".format(elapsed))    
    return cmd_count

def batch_cancel_tests():
    set_test_group("BATCH cancel tests")
    started = time.time()
    clear_cmd_count()

    # cancel RUN
    xt('xt run --target=batch code/xtTestApp.py --epochs=100')
    xt('xt cancel run $lastrun')

    # cancel JOB
    xt('xt run --target=batch code/xtTestApp.py --epochs=100')
    xt('xt cancel job $lastjob')

    # cancel ALL BATCH
    xt('xt run --target=batch code/xtTestApp.py --epochs=100')
    xt('xt cancel all batch')

    # cancel with NO RUNS
    xt('xt cancel run $lastrun')
    xt('xt cancel job $lastjob ')
    xt('xt cancel all batch')

    # view status (all runs cancelled)
    xt('xt view status --target=batch')

    elapsed = time.time() - started
    print("\nend of BATCH cancel tests, elapsed={:.0f} secs".format(elapsed))    
    return cmd_count

def aml_cancel_tests():
    set_test_group("AML cancel tests")
    started = time.time()
    clear_cmd_count()

    # cancel RUN
    xt('xt run --target=aml code/xtTestApp.py --epochs=100')
    xt('xt cancel run $lastrun')

    # cancel JOB
    xt('xt run --target=aml code/xtTestApp.py --epochs=100')
    xt('xt cancel job $lastjob')

    # cancel ALL AML
    xt('xt run --target=aml code/xtTestApp.py --epochs=100')
    xt('xt cancel all aml')

    # cancel with NO RUNS
    xt('xt cancel run $lastrun')
    xt('xt cancel job $lastjob ')
    xt('xt cancel all aml')

    # view status (all runs cancelled)
    xt('xt view status --target=aml')

    elapsed = time.time() - started
    print("\nend of AML cancel tests, elapsed={:.0f} secs".format(elapsed)) 

    return cmd_count   

def cancel_tests(philly=1):
    count = 0

    global cmd_delay
    cmd_delay = 5

    # TURN OFF these tests until cancel
    # command rewrites are complete and
    # we no longer rely on remote-control thru
    # XT Controller
    count += local_cancel_tests()

    if philly == 1:
        count += philly_cancel_tests()
    
    # cancel commands need some work (batch is failing)
    count += batch_cancel_tests()

    # awaiting implementation of AML cancel support...
    count += aml_cancel_tests()

    cmd_delay = 0

    return count

def storage_tests():
    count = 0

    count += uploadTests.main()
    count += dirTests.main()
    count += downloadTests.main()
    count += deleteTests.main()

    return count

def option_tests(config, store):
    '''
    test the ability of XT command line parsing to handle strings and string lists in option values 
    '''
    clear_cmd_count()
    set_test_group("option tests")

    # TODO: why does the first child run of quicktest change from run1.1 to run2.1?
    ws_name = config.get("general", "workspace")
    child_name = "run1"

    # if not store.does_run_exist(ws_name, child_name):
    #     child_name = "run2.1"

    prefix = "xt plot " + child_name

    # options: unquoted tokens
    xt(prefix + " train-acc, test-acc --show-plot=0  --legend-titles=foo, bar ")

    # options: quoted with {}
    xt(prefix + "  train-acc, test-acc --show-plot=0 --legend-titles={foo, bar}, {bar, ski, do} ")

    # options: nested quotes
    xt(prefix + '''  train-acc, test-acc --show-plot=0 --legend-titles="'foo, bar'", "'bar, ski, do'"  ''')

    # arguments: unquoted tokens
    xt(" xt set tags run2 urgent, priority=5, description=awesome ")

    # arguments: quoted with {}
    xt(" xt set tags run2 urgent, priority=5, description={test effect of 8 hidden layers} ")

    # arguments: nested quotes
    xt(''' xt set tags run2 urgent, priority=5, description='"test effect of 8 hidden layers"'  ''')

    return cmd_count

def action_test_target(target):
    clear_cmd_count()

    xt('xt run --target={} --data-action=download --model-action=download code/miniMnist.py --auto-download=0  --eval-model=1'.format(target))
    xt('xt run --target={} --data-action=mount --model-action=mount code/miniMnist.py --auto-download=0  --eval-model=1'.format(target))
    xt('xt run --target={} --data-action=mount --data-writable=1 --model-action=mount --model-writable=1 code/miniMnist.py --auto-download=0  --eval-model=1'.format(target))

    return cmd_count

def action_tests(philly=1):
    set_test_group("action_tests starting...")
    count = 0
    # doing this on a user-managed VM still needs some work
    #action_test_target("vm10")

    if philly == 1:
        count += action_test_target("philly")

    count += action_test_target("batch")
    count += action_test_target("aml")

    return count

def show_controller_tests():
    print("Running show controller tests...")
    count = showControllerTest.main()
    print("Finished running show controller tests.")
    return count

def cleanup():
    set_test_group("cleanup...")

    file_utils.ensure_dir_deleted("upload_testing")
    file_utils.ensure_dir_deleted("download_testing")

    # check for errors in runs
    text = xt("xt list runs --status=error", capture_output=True)
    # print("\nruns with errors:")
    # print(text)
    
    if not "no matching runs found" in text[0]:
        errors.internal_error("quick-test: above 'list runs' contains errors")

def main():
    # init stuff
    started = time.time()
    utils.init_logging(constants.FN_QUICK_TEST_EVENTS, logger, "XT Quick-Test")

    print("---- Quick-Test ----")
    
    args = parse_args()

    if args.tests:
        args.reset_workspace = False
    else:
        args.tests = [ "config", "search-scale", "show-controller", "run-index", "storage-provider", "hp-client", "search-provider", "run",
            "feature", "cancel", "storage", "option", "action", "tag", "demo" ]

    print("Tests requested:", args.tests)

    store, config = quick_prep(args.reset_workspace)
    stats = {}

    # if "config" in args.tests:
    #     count = config_tests.main()
    #     stats["config_tests"] = count

    # not yet ready for quick-test (takes 10+ mins by itself)
    # if "search-scale" in args.tests:
    #     # search scaling tests (low level)
    #     count = searchScaleTests.main()
    #     stats["search_scale"] = count

    if "show-controller" in args.tests:
        count = show_controller_tests()
        stats["show_controller_tests"] = count

    if "run-index" in args.tests:
        # run index tests (low level)
        count = runIndexTests.main()
        stats["run_index"] = count

    if "storage-provider" in args.tests:
        # provider tests (low level)
        count = storageProviderTests.main()
        stats["asure_storage_provider"] = count

    if "hp-client" in args.tests:
        # client-side HP processing/search
        count = hp_client_tests.main()
        stats["hp_client"] = count

    if "search-provider" in args.tests:
        # provider tests (low level)
        count = hpSearchTests.main(philly=args.philly)
        stats["hp_search_provider"] = count

    if "plot" in args.tests:
        # plot command testing
        count = plotCommands.main()
        stats["plot"] = count

    if "run" in args.tests:
        # run tests (lots of combinations)
        count = runTests.main(philly=args.philly)
        stats["run"] = count

    if "feature" in args.tests:
        count = feature_tests()
        stats["feature_tests"] = count

    if "cancel" in args.tests:
        count = cancel_tests(philly=args.philly)
        stats["cancel_tests"] = count

    if "storage" in args.tests:
        count = storage_tests()
        stats["storage_tests"] = count

    if "option" in args.tests:
        count = option_tests(config, store)
        stats["option_tests"] = count

    if "action" in args.tests:
        count = action_tests(philly=args.philly)
        stats["action_tests"] = count

    if "tag" in args.tests:
        count = tagTests.main(philly=args.philly)
        stats["tagTests"] = count

    if "demo" in args.tests:
        count = run_xt_demo(philly=args.philly, basic_mode=1)
        count = run_xt_demo(philly=args.philly, basic_mode=0)
        stats["xt_demo"] = count

    # print summary of results
    total_count = 0
    print("\nquick-test summary:")

    for name, count in stats.items():
        print("  {}: {}".format(name, count))
        total_count += count

    print("  total tests: {}".format(total_count))

    cleanup()

    elapsed = time.time() - started
    print("\n*** quick-test PASSED: (test count={}, elapsed: {:.2f} mins) ***".format(total_count, elapsed/60))

if __name__ == "__main__":
    main()
