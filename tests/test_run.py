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

SUBMIT_LOGS_DIR = "submitLogs"

if pc_utils.is_windows():
    APPROVED_DIR = "quick-test/approved_{}_windows".format(SUBMIT_LOGS_DIR)
else:
    APPROVED_DIR = "quick-test/approved_{}_linux".format(SUBMIT_LOGS_DIR)

# for debugging
STOP_ON_FIRST_ERROR = True

class RunTests():
    def __init__(self, config, seed, compare, philly=1):
        self.config = config
        self.cmd_count = 0
        self.assert_count = 0
        self.file_count = 0
        self.all_cmds = []
        self.compare = compare
        self.failed_asserts = 0
        self.file_compare_errors = 0
        self.philly = philly

        # regular expressions for value masking
        self.re_run = re.compile(r"run\d+")
        self.re_job = re.compile(r"job\d+")
        self.re_workspace = re.compile(r"quick-test[a-z\-_]*")
        self.re_c_drive = re.compile(r"[cC]:[\\/]")
        self.re_seed = re.compile(r"seed=\d+")
        self.re_xtlib = re.compile(r"xtlib==\d+\.\d+\.\d+")
        self.re_box_secret = re.compile(r"XT_BOX_SECRET=[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}")

        np.random.seed(seed)

    def reset_count(self):
        self.assert_count = 0

    def _assert(self, value):
        if STOP_ON_FIRST_ERROR:
            assert value
        elif not value:
            self.failed_asserts += 1

    def _assert_match(self, name, valuea, valuex):
        prefix = "https://xtsandboxstorage.blob.core.windows.net/xt-store-info/jobs/job999/"

        if isinstance(valuea, str) and valuea.startswith(prefix) and valuex.startswith(prefix):
            # don't compare long random string assigned by AML
            pass
        elif valuea != valuex:
            print("assert_mactch failure:")
            print("  valuea=", valuea)
            print("  valuex=", valuex)
            
            if STOP_ON_FIRST_ERROR:
                assert False and "values don't match for name=" + name
            else:
                self.failed_asserts += 1

    def test_cmd(self, i, cmd, logs_dir, fake):
        self.cmd_count += 1        

        if not fake:
            cmd = cmd.replace("--fake-submit=True", "--fake-submit=False")

        print("-------------------------------------")
        print("runTests: testing (# {}, errors: {}/{}): {}".format(i, self.file_compare_errors, self.file_count, cmd))
        #console.set_level("diagnostics")

        file_utils.ensure_dir_exists(logs_dir)

        xt_cmds.main(cmd)

        if self.compare:
            self.compare_submit_logs(logs_dir)

    def gen_runs(self, target, data, model, mtype, stype, runs, nodes):
        # called 7x3x3x4x5x4 = 5040 times

        args = ""
        mopt = ""
        script = "tests/fixtures/miniMnist.py"

        if mtype == "multi":
            mopt = " --multi"
            script = "tests/fixtures/multi_commands.txt"
        elif mtype == "hp-args":
            args = "--lr=[.01, .03, .05] --optimizer=[sgd, adam] --mlp-units=[64, 100, 128, 256]"
        elif mtype == "hp-file":
            mopt = " --hp-config=tests/fixtures/miniSweeps.yaml"
        elif mtype != "single":
            errors.internal_error("unrecognized mtype={}".format(mtype))

        sopt = " --search-type=" + stype if stype != "none" else ""
        nopt = " --nodes=" + str(nodes) if nodes else ""
        ropt = " --runs=" + str(runs)

        logs_dir = "{}/{}.data_{}.model_{}.{}.{}.{}.{}".format(SUBMIT_LOGS_DIR, target, data, model, mtype, stype, runs, nodes)
        fake_submit = True

        cmd = "xt run --target={}{}{}{}{} --data-action={} --model-action={} --submit-logs={} --fake-submit={} {} {}".format(target, ropt, nopt, mopt, sopt, data, model, logs_dir, fake_submit, script, args)

        self.all_cmds.append( {"cmd": cmd, "logs_dir": logs_dir} )
        # self.test_cmd(cmd)
        # self.compare_submit_logs(logs_dir)

    def compare_submit_logs(self, logs_dir):
        approve_prefix = "approved_"
        prefix_len = len(approve_prefix)
        approved_dir = approve_prefix + logs_dir

        if not os.path.exists(approved_dir):
            errors.general_error("missing approved_dir:", approved_dir)
            return

        paths = [os.path.join(approved_dir, fn) for fn in os.listdir(approved_dir)]
        approved_files = [fn for fn in paths if os.path.isfile(fn)]

        for fn in approved_files:
            if ((not pc_utils.is_windows() and fn.endswith(".bat")) or
                (pc.is_windows() and fn.endswith(".sh"))):
                continue

            self.file_count += 1

            fnx = fn[prefix_len:]
            if not os.path.exists(fnx):
                errors.general_error("missing approved file in submitLogs dir: {}".format(fnx))
            self.compare_log_files(fn, fnx)

    def compare_log_files(self, fn_approved, fnx):
        '''
        we mask and compare at file level.  if errors, we
        drill down to property level for easier debugging.
        only file compare counts should be counted as tests.
        '''
        name = os.path.basename(fn_approved)

        approved_text = file_utils.read_text_file(fn_approved)
        texta = self.mask_out_regular_changes(approved_text)

        tested_text = file_utils.read_text_file(fnx)
        textx = self.mask_out_regular_changes(tested_text)

        match = texta == textx
        if not match:
            # files did not match after masking, but property level matching may work
            self.file_compare_errors += 1
            before_asserts = self.assert_count

            # compare detail; we should see an assert on a smaller property
            file_ext = os.path.splitext(fnx)[1]

            if texta.startswith("{") and file_ext in [".json", ".log"]:
                # debug 
                print("loading JSON: fn_approved={}, fnx={}".format(fn_approved, fnx))
                file_utils.write_text_file("texta.json", texta)
                file_utils.write_text_file("textx.json", textx)

                dda = json.loads(texta)
                ddx = json.loads(textx)
                self.compare_json_values(name, dda, ddx)
            else:
                texta = self.mask_out_regular_changes_from_wrapper(approved_text)
                testx = self.mask_out_regular_changes_from_wrapper(tested_text)
                self.compare_text(name, texta, textx)

            if self.assert_count == before_asserts:
                # no new asserts, so undo our file error count
                # this happens because some failed file compares
                # succeed when compared at property level
                self.file_compare_errors -= 1
            elif STOP_ON_FIRST_ERROR:
                self._assert( False )
    
    def mask_out_regular_changes_from_wrapper(self, texta):
        texta = self.mask_out_regular_changes(texta)

        export_user_re = re.compile(r'export\sUSER\=(.+)\s')
        using_local_path_re = re.compile(r'ENV\[XT\_DATA\_DIR\]\=\s(.+)\s')
        xt_data_dir_re = re.compile(r'XT\_DATA\_DIR\=(.+)\s')
        xt_data_mnt_re = re.compile(r'XT\_DATA\_MNT\=(.+)\s')
        result_export_user = export_user_re.search(texta)
        if result_export_user:
            texta = texta.replace("export USER={}".format(result_export_user.group(1)), "export USER=someuser")

        result_using_local_path = using_local_path_re.search(texta)
        if result_using_local_path:
            texta = texta.replace("ENV[XT_DATA_DIR]= {}".format(result_using_local_path.group(1)), "ENV[XT_DATA_DIR]= somepath")

        result_xt_data_dir = xt_data_dir_re.search(texta)
        if result_xt_data_dir:
            texta = texta.replace("XT_DATA_DIR={}".format(result_xt_data_dir.group(1)), "XT_DATA_DIR=somepath")

        result_xt_data_mnt = xt_data_mnt_re.search(texta)
        if result_xt_data_mnt:
            texta = texta.replace("XT_DATA_MNT={}".format(result_xt_data_mnt.group(1)), "XT_DATA_MNT=somepath")

        return texta

    def mask_out_regular_changes(self, texta):
        # mask out comparisons of specific run names
        if "run" in texta:
            texta = self.re_run.sub("run999", texta)
            
        # mask out comparisons of specific job names
        if "job" in texta:
            texta = self.re_job.sub("job999", texta)

        # mask out comparisons of specific workspaces
        if "quick-test" in texta:
            texta = self.re_workspace.sub("quick-test", texta)

        # mask out comparisons of c:\ vs. C:\
        # replace with forward slash which is safer, in general
        texta = self.re_c_drive.sub(r"c:/", texta)
        texta = texta.replace("c:/\\", "c:/")

        # mask out comparisons of seed values
        if "seed=" in texta:
            texta = self.re_seed.sub("seed=42", texta)

        # mask out comparisons of specific xtlib versions
        if "xtlib==" in texta:
            texta = self.re_xtlib.sub("xtlib==0.0.999", texta)

        # mask out comparisons of specific XT_BOX_SECRET values
        if "XT_BOX_SECRET=" in texta:
            texta = self.re_box_secret.sub("XT_BOX_SECRET=42", texta)

        container_name_re = re.compile(r'containerName\s(.+)\s>>')
        workspace_to_container_re = re.compile(r'\sto\scontainer\s(.+)\s+')
        result_container_name = container_name_re.search(texta)
        if result_container_name:
            texta = texta.replace("containerName {}".format(result_container_name.group(1)), "containerName workspacename")

        result_workspace_to_container = workspace_to_container_re.search(texta)
        if result_workspace_to_container:
            texta = texta.replace(" to container {}".format(result_workspace_to_container.group(1)), " container workspacename")

        return texta

    def compare_text(self, name, texta, textx):
        if texta.startswith("{") and texta.endswith("}"):
            if "'" in texta:
                try:
                    # treat as a PYTHON dict in text form
                    dda = ast.literal_eval(texta)
                    ddx = ast.literal_eval(textx)
                except Exception as ex:
                    print("exception trying to load PYTHON dict: ex=", ex)
                    dda = None
                    ddx = None
            
            if not dda:
                try:
                    # treat as a JSON dict in text form
                    dda = json.loads(texta)
                    ddx = json.loads(textx)
                except Exception as ex:
                    print("exception trying to load PYTHON/JSON dict: ex=", ex)
                    dda = None
                    ddx = None

            if dda:
                # we created 2 dict to compare
                self.compare_dicts(name, dda, ddx)
            else:
                # compare as normal strings
                if texta != textx:
                    # make them easy to compare for xt dev
                    ml_valuea = texta.replace(";", "\n")
                    ml_valuex = textx.replace(";", "\n")

                    file_utils.write_text_file("expected.txt", ml_valuea)
                    file_utils.write_text_file("actual.txt", ml_valuex)

                    self._assert_match(name, ml_valuea, ml_valuex )
        else:
            # compare line by line
            linesa = texta.split("\n")
            linesx = textx.split("\n")

            if len(linesa) ==1 and ";" in texta:
                # try splitting lines on ";" (long philly cmds)
                linesa = texta.split(";")
                linesx = textx.split(";")

            for linea, linex in zip(linesa, linesx):
                self._assert_match(name, linea, linex )

    def compare_json_values(self, name, valuea, valuex):

        if isinstance(valuea, dict):
            self.compare_dicts(name, valuea, valuex)
        elif isinstance(valuea, (list, tuple)):
            self.compare_lists(name, valuea, valuex)
        elif isinstance(valuea, str):
            if name in ["target_file", "cmd_parts", "cmds"]:
                valuea = file_utils.fix_slashes(valuea)
                valuex = file_utils.fix_slashes(valuex)
            self.compare_text(name, valuea, valuex)
        else:
            self._assert_match(name, valuea, valuex)

    def compare_dicts(self, name, dda, ddx):
        
        # does dda match ddx, using list of non_matches?
        non_matches = {"run_name": 1, "job_id": 1, "dest_name": 1, "name": 1, "XT_BOX_SECRET": 1, 
            "dest_url": 1, "from_ip": 1, "from_host": 1, "username": 1, "workspace": 1, "ws": 1,
            "XT_WORKSPACE_NAME": 1, "containerName": 1, "box_name": 1} 

        for name, valuea in dda.items():
            if not name in non_matches:
                self._assert( name in ddx )
                valuex = ddx[name]

                self.compare_json_values(name, valuea, valuex)

    def compare_lists(self, name, valuea, valuex):
        self._assert( isinstance(valuex, (list, tuple)) )
        self._assert( len(valuea) == len(valuex) )

        for itema, itemx in zip(valuea, valuex):
            self.compare_json_values(name, itema, itemx)

    def test_stype(self, target, data, model, mtype, stype):
        # 7x3x3x4x5x4

        self.gen_runs(target, data, model, mtype, stype, 1, 1)
        self.gen_runs(target, data, model, mtype, stype, 2, 1)
        self.gen_runs(target, data, model, mtype, stype, 3, 1)
        self.gen_runs(target, data, model, mtype, stype, 3, 2)

    def test_mtype(self, target, data, model, mtype):
        # 7x3x3x4x5

        self.test_stype(target, data, model, mtype, "random")    # static
        self.test_stype(target, data, model, mtype, "grid")      # static
        self.test_stype(target, data, model, mtype, "dgd")       # dynamic
        self.test_stype(target, data, model, mtype, "bayesian")  # dynamic
        self.test_stype(target, data, model, mtype, "none")

    def test_model(self, target, data, model):
        # 7x3x3x4

        self.test_mtype(target, data, model, "hp-args")
        self.test_mtype(target, data, model, "multi")
        self.test_mtype(target, data, model, "hp-file")
        self.test_mtype(target, data, model, "single")

    def test_data(self, target, data):
        # 7x3x3

        self.test_model(target, data, "none")
        self.test_model(target, data, "download")
        self.test_model(target, data, "mount")

    def test_target(self, target):
        # 7x3

        self.test_data(target, "none")
        self.test_data(target, "download")
        self.test_data(target, "mount")

    def gen_all(self):
        # 7x

        # native targets
        self.test_target("local")

        if self.philly == 1:
            self.test_target("philly")

        self.test_target("batch")
        self.test_target("aml")

        # docker targets
        #self.test_target("local-docker")
        #self.test_target("batch-docker")
        #self.test_target("aml-docker")

    def test_random_subset_cmds(self, fake_count, actual_count):
        all_cmds = self.all_cmds
        cmds = np.random.choice(all_cmds, fake_count + actual_count)

        # for debugging (let's us skip some tests to focus on remaining)
        skip_tests = {}  # {"0": 1, "1": 1}

        for i, cd in enumerate(cmds):
            i_str = str(i)

            if not i_str in skip_tests:
                fake = i < fake_count
                cmd = cd["cmd"]
                logs_dir = cd["logs_dir"]

                self.test_cmd(i, cmd, logs_dir, fake)


def init_approved_dir():
    compare = False

    if os.path.exists(APPROVED_DIR):
        compare = True
    else:
        # unzip file to directory
        fn_zip = APPROVED_DIR + ".zip"
        if os.path.exists(fn_zip):
            with zipfile.ZipFile(fn_zip, 'r') as zip:
                zip.extractall(".")
            compare = True
            print("created APPROVED logs from .zip")
        elif os.path.exists(SUBMIT_LOGS_DIR):
            # create a new approved dir from the completed test logs 
            shutil.copytree(SUBMIT_LOGS_DIR, APPROVED_DIR)

            # create a .zip file (to check in approved logs)
            filenames = file_helper.get_filenames_from_include_lists([ APPROVED_DIR ], recursive=True)

            with zipfile.ZipFile(fn_zip, 'w') as zip:
                for fn in filenames:
                    zip.write(fn)
            compare = True
            print("created APPROVED logs from existings submitJob results")

    if not compare:
        print("----> WARNING: running WITHOUT approved (no compares will be done) ----")

    return compare


class TestRun(test_base.TestBase):

    def setup_class(cls):
        """
        Setup once for all tests
        """

        # until we improve the comparision system to avoid "all or nothing" acceptance
        # of changes, we are disabling log file checking here
        # compare = init_approved_dir()
        compare = False

        config = xt_config.get_merged_config()
        seed = 42

        # Disable compare for now
        # tester = RunTests(config, seed, compare)
        cls.tester = RunTests(config, seed, False, philly=0)

        cls.started = time.time()

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

    def options(self):
        '''
        test the ability of XT command line parsing to handle strings and string lists in option values 
        '''
        child_name = "run1"

        # if not store.does_run_exist(ws_name, child_name):
        #     child_name = "run2.1"

        prefix = "xt plot " + child_name

        # options: unquoted tokens
        self.xt(prefix + " train-acc, test-acc --show-plot=0  --legend-titles=foo, bar ")

        # options: quoted with {}
        self.xt(prefix + "  train-acc, test-acc --show-plot=0 --legend-titles={foo, bar}, {bar, ski, do} ")

        # options: nested quotes
        self.xt(prefix + '''  train-acc, test-acc --show-plot=0 --legend-titles="'foo, bar'", "'bar, ski, do'"  ''')

        # arguments: unquoted tokens
        self.xt(" xt set tags run2 urgent, priority=5, description=awesome ")

        # arguments: quoted with {}
        self.xt(" xt set tags run2 urgent, priority=5, description={test effect of 8 hidden layers} ")

        # arguments: nested quotes
        self.xt(''' xt set tags run2 urgent, priority=5, description='"test effect of 8 hidden layers"'  ''')

    def set_tags(self, names):
        for name in names:
            self.xt('''xt set tags {} urgent, priority=5, description="'test effect of 8 hidden layers'" '''.format(name))
            self.xt('xt set tags {} funny, sad'.format(name))

    def clear_tags(self, names):
        for name in names:
            self.xt('xt clear tags {} funny'.format(name))
            #self.xt('xt clear tags run1428-run1429 sad')

    def list_tags(self, names):
        for name in names:
            #self.xt('xt list tags job2740')

            output = self.xt('xt list tags {}'.format(name))
            self.assert_names(output, ["description", "priority", "sad", "urgent"], "happy")

    def filter_tags(self):
        # NOTE: in these tests, job2748 is not defined and will be missing for
        # all list jobs commands

        # test basic PROPERTY FILTERS

        output = self.xt('xt list jobs job2741-job2751 --filter={nodes==5}')
        # expected: job2742
        self.assert_names(output, "job2742", "job2471")

        output = self.xt('xt list jobs job2741-job2751 --filter={nodes > 5}')
        # expected: job2741, job2743
        self.assert_names(output, ["job2741", "job2743"], "job2742")

        output = self.xt('xt list jobs job2741-job2751 --filter={nodes != 5}')
        # expected: job2741-job2751 EXCEPT for job2742
        self.assert_names(output, ["job2741", "job2751"], "job2742")

        # test TAG FILTERS

        output = self.xt('xt list jobs job2741-job2751 --filter={tags.urgent=$exists}')
        # expected: job2747
        self.assert_names(output, "job2747", "job2471")

        output = self.xt('xt list jobs job2741-job2751 --filter={tags.urgent!=$exists}')
        # expected: job2741-job2751 EXCEPT for job2747
        # BUG: the above command mistakenly returns ALL 11 jobs (MongoDB or XT?)
        #self.assert_names(output, ["job2741", "job2751"], "job2747")

        # :regex: (regular expressions)
        output = self.xt('xt list jobs job2741-job2751 --filter={tags.description:regex:.*hidden.*}')
        # expected: job2747
        self.assert_names(output, "job2747", "job2471")

        output = self.xt('xt list jobs job2741-job2751 --filter={tags.description:regex:.*hiDxDen.*}')
        # expected: <no matching jobs>
        self.assert_names(output, "no matching jobs")

        output = self.xt('xt list jobs job2741-job2751 --filter={tags.description:regex:^(.*hidden.*}')
        # expected: <no matching jobs>
        self.assert_names(output, "no matching jobs")

        # this is busted on Azure Mongodb
        output = self.xt('xt list jobs job2741-job2751 --filter={tags.description:regex:/.*hiDDen.*/i}')
        # expected: job2747
        # BUG: the above command mistakenly returns ALL 11 jobs (MongoDB or XT?)
        #self.assert_names(output, "job2747", "job2471")

        # :exists: (test for property existence)
        output = self.xt('xt list jobs job2741-job2751 --filter={tags.urgent:exists:true}')
        # expected: job2747
        self.assert_names(output, "job2747", "job2471")

        output = self.xt('xt list jobs job2741-job2751 --filter={tags.urgent:exists:false}')
        # expected: job2741-job2751 EXCEPT for job2747
        self.assert_names(output, ["job2741", "job2751"], "job2747")

        output = self.xt('xt list jobs job2741-job2751 --tags-all={urgent, nodes}')
        # expected: <no matching jobs>
        self.assert_names(output, "no matching jobs")

        output = self.xt('xt list jobs job2741-job2751 --tags-any={urgent, nodes}')

    def test_tag(self):
        result_runs = self.xt("xt list runs --status=completed")
        self.assertTrue(len(result_runs) > 3)
        first_result = result_runs[3]
        result_fields = list(filter(lambda f: len(f.strip()) > 0, first_result.split(" ")))
        run_id = result_fields[0].strip()
        job_id = result_fields[1].strip()

        self.set_tags([job_id, run_id])
        self.clear_tags([job_id, run_id])
        self.list_tags([job_id, run_id])

        self.filter_tags()


    def test_random(self):
        # scale this up to 100, 5
        fake_runs = 100
        actual_runs = 5

        self.tester.gen_all()
        elapsed = time.time() - self.started
        print("generated of {} tests took: {:.2f} secs".format(len(self.tester.all_cmds), elapsed))

        self.tester.test_random_subset_cmds(fake_runs, actual_runs)

        self.assert_no_error_runs()

        self.options()
