#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# runner.py: code to prepare to build a run submission (shared code for all backends)
import os
import sys
import json
import math
import time
import yaml
import uuid
import shutil

from xtlib.client import Client
from xtlib.console import console
from xtlib.cmd_core import CmdCore
from xtlib.helpers import file_helper
from xtlib.helpers.scanner import Scanner
from xtlib.storage import mongo_run_index
from xtlib.hparams.hp_client import HPClient
from xtlib.helpers.feedbackParts import feedback as fb
from xtlib.helpers.xt_config import get_installed_package_version

from xtlib import utils
from xtlib import errors
from xtlib import capture
from xtlib import xt_dict
from xtlib import pc_utils
from xtlib import scriptor
from xtlib import constants
from xtlib import file_utils
from xtlib import process_utils
from xtlib import box_information

class Runner():
    ''' class to consolidate all shared code for run submission '''
    def __init__(self, config, core, temp_dir):
        self.config = config
        self.core = core
        self.store = core.store
        self.backend = None
        self.is_docker = None
        self.target_dir = None
        self.temp_dir = temp_dir

    def process_args(self, args):

        run_script = None
        parent_script = None
        run_cmd_from_script = None
        target_file = args["script"]
        target_args = args["script_args"]
        code_upload = args["code_upload"]

        # user may have wrong slashes for this OS
        target_file = file_utils.fix_slashes(target_file)

        if os.path.isabs(target_file):
            errors.syntax_error("path to app file must be specified with a relative path: {}".format(target_file))

        is_rerun = "is_rerun" in args
        if is_rerun:
            # will be running from script dir, so remove any path to script file
            self.script_dir = os.path.dirname(target_file)
            target_file = os.path.basename(target_file)

        if target_file.endswith(".py"):
            # PYTHON target
            cmd_parts = ["python"]
            cmd_parts.append("-u")
            cmd_parts.append(target_file)
        else:
            cmd_parts = [target_file] 

        if target_args:
            # split on unquoted spaces
            arg_parts = utils.cmd_split(target_args)
            cmd_parts += arg_parts

        if target_file == "docker":
            self.is_docker = True
            
        if not self.is_docker and code_upload and not os.path.exists(target_file):
            errors.env_error("script file not found: {}".format(target_file))

        ps_path = args["parent_script"]
        if ps_path:
            parent_script = file_utils.read_text_file(ps_path, as_lines=True)

        if target_file.endswith(".bat") or target_file.endswith(".sh"):
            # a RUN SCRIPT was specified as the target
            run_script = file_utils.read_text_file(target_file, as_lines=True)
            run_cmd_from_script = scriptor.get_run_cmd_from_script(run_script)

        compute = args["target"]
        box_def = self.config.get("boxes", compute, suppress_warning=True)
        setup = utils.safe_value(box_def, "setup")

        compute_def = self.config.get_compute_def(compute)        
        if compute_def:
            # must be defined in [compute-targets]
            compute_def = self.config.get_compute_def(compute)

            if not "service" in compute_def:
                errors.config_error("compute target '{}' must define a 'service' property".format(compute))

            service = compute_def["service"]
            if service in ["local", "pool"]:
                # its a list of box names
                boxes = compute_def["boxes"]
                if len(boxes)==1 and boxes[0] == "localhost":
                    pool = None
                    box = "local"
                    service_type = "pool"
                else:
                    pool = compute
                    box = None
                    service_type = "pool"
            else:
                # it a set of compute service properties
                pool = compute
                box = None
                service_name = compute_def["service"]
                service_type = self.config.get_service_type(service_name)
        elif box_def:
            # translate single box name to a compute_def
            box = compute
            pool = None
            service_type = "pool"
            compute_def = {"service": service_type, "boxes": [box], setup: setup}
        else:
            errors.config_error("unknown target or box: {}".format(compute))

        args["target"] = compute
        args["compute_def"] = compute_def
        args["service_type"] = service_type

        # for legacy code
        args["box"] = box
        args["pool"] = pool

        return service_type, cmd_parts, ps_path, parent_script, target_file, run_script, run_cmd_from_script, \
            compute, compute_def

    def make_local_snapshot(self, snapshot_dir, code_dir, dest_name, omit_list):
        '''
        keep code simple (and BEFORE upload fast):
            - always copy code dir to temp dir
            - if needed, copy xtlib subdir
            - later: if needed, add 2 extra controller files
            - later: zip the whole thing at once & upload 
        '''
        if dest_name and dest_name != ".":
            snapshot_dir += "/" + dest_name

        console.diag("before create local snapshot")

        # fixup slashes for good comparison
        snapshot_dir = os.path.realpath(snapshot_dir)

        # fully qualify path to code_dir for simpler code & more informative logging
        code_dir = os.path.realpath(code_dir)

        recursive = True

        if code_dir.endswith("**"):
            code_dir = code_dir[:-2]   # drop the **
        elif code_dir.endswith("*"):
            recursive = False

        # copy user's source dir (as per config file options)
        if True:    
            omit_list = utils.parse_list_option_value(omit_list)

            # build list of files matching both criteria
            filenames = file_helper.get_filenames_from_include_lists(None, omit_list, recursive=recursive, from_dir=code_dir)

            file_utils.ensure_dir_exists(snapshot_dir)
            prefix_len = 2 if code_dir == "." else len(code_dir)
            copy_count = 0

            # copy files recursively, preserving subdir names
            for fn in filenames:
                fn = os.path.realpath(fn)           # fix slashes

                if fn.startswith(code_dir) and fn != code_dir:
                    fn_dest = snapshot_dir + "/" + fn[prefix_len:]
                    file_utils.ensure_dir_exists(file=fn_dest)
                    shutil.copyfile(fn, fn_dest)
                else:
                    shutil.copy(fn, snapshot_dir)
                copy_count += 1

            #console.diag("after snapshot copy of {} files".format(copy_count))
        else:
            shutil.copytree(code_dir, snapshot_dir)  
            
        return snapshot_dir


    def ensure_script_ext_matches_box(self, script_name, fn_script, box_info):
        _, file_ext = os.path.splitext(fn_script)
        if file_ext in [".bat", ".sh"]:
            expected_ext = ".bat" if box_info.box_os == "windows" else ".sh"

            if file_ext != expected_ext:
                errors.combo_error("{} file ext='{}' doesn't match box.os='{}'".format(script_name, file_ext, box_info.box_os))

    def build_first_run_for_node(self, node_index, box_name, run_script_path, parent_script_path, using_hp, use_aml_hparam, run_specs, 
            job_id, parent_name, cmds, pool_info, repeat_count, fake_submit, search_style, box_secret, args):
        exper_name = args['experiment']

        box_info = box_information.BoxInfo(self.config, box_name, self.store, args=args)

        if node_index == 0:
            # check that script file extensions match OS of first box
            if run_script_path:
                self.ensure_script_ext_matches_box("run script", run_script_path, box_info)

            if parent_script_path:
                self.ensure_script_ext_matches_box("parent script", parent_script_path, box_info)

        node_id = "node" + str(node_index)
        # if using_hp:
        #     if not node_id in cmds_by_node:
        #         errors.combo_error("you specified more nodes/boxes than hyperparameter search runs")

        cmd_parts = run_specs["cmd_parts"]
        actual_parts = None

        if cmd_parts:
            actual_parts = list(cmd_parts)
            if box_info.box_os == "linux" and actual_parts[0] == "docker":
                # give our user permission to run DOCKER on linux
                actual_parts.insert(0, "sudo")
                # run nvidia-docker to gain access to machines GPUs
                actual_parts[1] = "nvidia-docker"
            #console.print("actual_parts=", actual_parts)

        # CREATE RUN 
        path = os.path.realpath(args["script"])

        run_name, full_run_name, box_name, pool = \
            self.create_run(job_id, actual_parts, box_name=box_name, parent_name=parent_name, node_index=node_index, using_hp=using_hp, 
                repeat=repeat_count, app_info=None, path=path, exper_name=exper_name, pool_info=pool_info, fake_submit=fake_submit, 
                search_style=search_style, args=args)

        run_data = {"run_name": run_name, "run_specs": run_specs, "box_name": box_name, "box_index": node_index, 
            "box_info": box_info, "repeat": repeat_count, "box_secret": box_secret}

        return run_data
       
    def write_hparams_to_files(self, job_id, cmds, fake_submit, using_hp, args):
        # write to job-level sweeps-list file
        #console.print("cmds=", cmds)   
        cmds_text = json.dumps(cmds)

        if not fake_submit:
            self.store.create_job_file(job_id, constants.HP_SWEEP_LIST_FN, cmds_text)

        boxes, pool_info, service_type = box_information.get_box_list(self, job_id=job_id, args=args)
        num_boxes = len(boxes)

        is_distributed = args["distributed"]
        if is_distributed:
            # check for conflicts
            if using_hp:
                errors.combo_error("Cannot do hyperparamer search on a distributed-training job")

            if service_type != "aml":
                errors.combo_error("Distributed-training is currently only supported for AML jobs")

        return boxes, num_boxes

    def create_run(self, job_id, user_cmd_parts, box_name="local", parent_name=None, rerun_name=None, node_index=0, 
            using_hp=False, repeat=None, app_info=None, path=None, exper_name=None, pool_info=None, fake_submit=False, 
            search_style=None, args=None):
        '''
        'create_run' does the following:
            - creates a new run name (and matching run directory in the store)
            - logs a "created" record in the run log
            - logs a "created" record in the workspace summary log
            - logs a "cmd" record in the run log
            - log an optional "notes" record in the run log
            - captures the run's "before" files to the store's run directory

        '''
        console.diag("create_run: start")

        app_name = None   # app_info.app_name
        box_nane = args["box"]
        pool = args["pool"]
        run_name = ""
        log_to_store = self.config.get("logging", "log")
        aggregate_dest = args["aggregate_dest"]

        if log_to_store:
            if not exper_name:
                exper_name = input("experiment name (for grouping this run): ")

            #console.print("calling store.start_run with exper_name=", exper_name)
            username = args["username"]
            description = args["description"]
            workspace = args["workspace"]

            console.diag("create_run: before start_run")

            service_type = args["service_type"]
            compute = args["target"]
            search_type = args["search_type"]
            sku = args["sku"]

            if not sku:
                # make default sku explicit
                if pool_info and "sku" in pool_info:
                    sku = pool_info["sku"].lower()

            # create RUN in store
            if fake_submit:
                run_name = "fake_run123"
            else:
                if parent_name:
                    run_name = self.store.start_child_run(workspace, parent_name, box_name=box_name, username=username,
                        exper_name=exper_name, app_name=app_name, pool=pool, job_id=job_id, node_index=node_index, sku=sku,
                        description=description, aggregate_dest=aggregate_des, path=path, compute=compute, service_type=service_type, 
                        search_style=search_style)
                else:
                    is_parent = search_style != "single"

                    run_name = self.store.start_run(workspace, exper_name=exper_name, box_name=box_name, app_name=app_name, 
                        username=username, repeat=repeat, pool=pool, job_id=job_id, node_index=node_index, sku=sku,
                        description=description, aggregate_dest=aggregate_dest, path=path, compute=compute, service_type=service_type, 
                        search_style=search_style, is_parent=is_parent)

            console.diag("create_run: after start_run")

            # always log cmd (for re-run purposes)
            xt_cmd = args["xt_cmd"]

            if not fake_submit:
                self.store.log_run_event(workspace, run_name, "cmd", {"cmd": user_cmd_parts, "xt_cmd": xt_cmd })

            # for now, don't log args (contain private credentials and not clear if we really need it)
            # record all "args" (from cmd line, user config, default config) in log (for audit/re-run purposes)
            #self.store.log_run_event(workspace, run_name, "args", args)

            store_type = self.config.get_storage_type()
            full_run_name = utils.format_workspace_exper_run(store_type, workspace, exper_name, run_name)

            # log NOTES record
            if not fake_submit:
                if self.config.get("logging", "notes") in ["before", "all"]:
                    text = input("Notes: ")
                    if text:
                        self.store.log_run_event(workspace, run_name, "notes", {"notes": text})
        else:
            full_run_name = ""

        console.diag("create_run: after logging")
        workspace = args['workspace']

        return run_name, full_run_name, box_name, pool

    def upload_sweep_data(self, sweeps_text, exper_name, job_id, args):
        '''
        we have extracted/parsed HP sweeps data; write it to the experiment/job store
        where we can find it during dynamic HP searches (running in controller).
        '''
        # upload SWEEP file to job or experiment directory
        fn_sweeps = args["hp_config"]
        agg_dest = args["aggregate_dest"]

        if not fn_sweeps:
            # must have extracted sweeps data from cmd line options
            fn_sweeps = constants.HP_CONFIG_FN
            args["hp_config"] = fn_sweeps

        # upload to a known folder name (since value of fn_sweeps can vary) and we need to find it later (HX usage)
        target_name = file_utils.path_join(constants.HP_CONFIG_DIR, os.path.basename(fn_sweeps))
        
        if agg_dest == "experiment":
            self.store.create_experiment_file(workspace, exper_name, target_name, sweeps_text)
        else:
            self.store.create_job_file(job_id, target_name, sweeps_text)

    # def attach_if_needed(self, workspace, run_data_list_by_box, escape, attach):
    #     # ATTACH or provide attach cmd
    #     first_run = run_data_list_by_box[0][0]   

    #     if attach:
    #         time.sleep(1)
    #         self.core.client.monitor_attach_run(workspace, first_run["run_name"], show_waiting_msg=False, escape=escape)
    #     # else:
    #     #     box_name = first_run["box_name"]
    #     #     full_run_name = workspace + "/" + first_run["run_name"].upper()   
    #     #     console.print("To view output: xt attach {}".format(full_run_name))

    def build_runs_by_box(self, job_runs, workspace):
        # build box_name => runs dict for job info file
        runs_by_box = {}
        last_run = None

        # for each node
        for run_data_list in job_runs:
            for run_data in run_data_list:   
                box_name = run_data["box_name"]

                # process a run for box_name
                if not box_name in runs_by_box:
                    runs_by_box[box_name] = [] 

                # create as dict; we will later add "service_run_id" to the dict (for philly, batch, aml)
                rr = {"ws_name": workspace, "run_name": run_data["run_name"], "box_index": run_data["box_index"]}

                runs_by_box[box_name].append(rr)
                last_run = run_data["run_name"]

        return runs_by_box, last_run

    def remove_script_dir_from_parts(self, cmd_parts):
        '''
        NOTE: cmd_parts is modified directly.
        '''

        script_dir = "."    # default to the current directory

        parts = cmd_parts
        for i, part in enumerate(parts):
            path = os.path.realpath(part)
            if os.path.isfile(path):
                script_dir = os.path.dirname(path)

                # remove the path from the script 
                parts[i] = os.path.basename(path)
                break

        return script_dir

    def build_docker_cmd(self, docker_name, target_file, cmd_parts, script_dir, snapshot_dir, job_secret, args):
        for_windows = True

        docker_def = self.config.get("dockers", docker_name, default_value=None)
        if not docker_def:
            errors.config_error("docker '{}' not found in config file".format(docker_name))

        registry_name = docker_def["registry"]
        image = docker_def["image"]
        
        if registry_name:
            # get REGISTRY credentials
            registry_creds = self.config.get("external-services", registry_name, suppress_warning=True)
            if not registry_creds:
                config_error("'{}' must be specified in [external-services] section of XT config file".format(registry_name))

            login_server = registry_creds["login-server"]
        else:
            login_server = None

        #pwd = "%cd%" if for_windows else "$(pwd)"
        script_dir = file_utils.fix_slashes(script_dir, True)
        mappings = "-v {}:/usr/src".format(script_dir)
        options = "--rm"

        # collect env vars 
        env_vars = {"XT_IN_DOCKER": 1, "XT_USERNAME": pc_utils.get_username()}
        scriptor.add_controller_env_vars(env_vars, self.config, job_secret, "node0")

        # fixup backslash char for target_file
        if ".py" in target_file:
            app = "python -u"
            #target_file = file_utils.fix_slashes(target_file, True)
            target_file = os.path.basename(target_file)
        else:
            app = target_file
            target_file = ""

        full_image = login_server + "/" + image if login_server else image

        # build a mapping for data?
        data_local = args["data_local"]
        if data_local:
            if "$scriptdir" in data_local:
                data_local = data_local.replace("$scriptdir", script_dir)

            data_local = os.path.realpath(data_local)
            mappings += " -v {}:/usr/data".format(data_local)
            env_vars["XT_DATA_DIR"] = "/usr/data"

        # write env vars to file in snapshot dir
        FN_EV = "__dockev__.txt"
        fn_env_var = os.path.join(snapshot_dir, FN_EV)
        lines = [name + "=" + str(value) for name,value in env_vars.items()]
        text = "\n".join(lines)
        file_utils.write_text_file(fn_env_var, text)

        # specify env var file (in current directory) to docker
        options += " --env-file={}".format(FN_EV)

        # inherit ENV VARS from running environment
        options += " -e XT_RUN_NAME -e XT_WORKSPACE_NAME -e XT_EXPERIMENT_NAME"

        docker_cmd = "docker run {} {} {} {} /usr/src/{}".format(options, mappings, full_image, app, target_file)
        new_parts = utils.cmd_split(docker_cmd)
        return new_parts

    def adjust_pip_packages(self, args):
        '''
        convert any package=* in pip-packages to use local machine version (from pip freeze)
        '''
        pip_packages = args["pip_packages"]
        new_pip_packages = []

        for pp in pip_packages:
            if pp.endswith("==*"):
                package = pp[:-3]
                version = get_installed_package_version(package)
                if not version:
                    errors.env_error("version number for specified pip package not found in environment: " + package)
                pp = package + "==" + version

            new_pip_packages.append(pp)

        args["pip_packages"] = new_pip_packages

    def snapshot_all_code(self, snapshot_dir, cmd_parts, args):
        '''
        make local snapshot of each code_dir (and xtlib, if needed)
        '''
        code_dirs = args["code_dirs"]
        xtlib_capture = args["xtlib_upload"]
        code_omit = args["code_omit"]
        script_dir = None

        code_upload = args["code_upload"]
        
        # this step should always be done so that script_dir is removed from cmd_parts
        script_dir = self.remove_script_dir_from_parts(cmd_parts)

        if code_upload:
            for i, code_dir in enumerate(code_dirs):
                # fixup "$scriptdir" relative paths
                if "$scriptdir" in code_dir:
                    code_dir = code_dir.replace("$scriptdir", script_dir)

                if "::" in code_dir:
                    code_dir, dest_dir = code_dir.split("::")
                else:
                    dest_dir = "."
                self.make_local_snapshot(snapshot_dir, code_dir, dest_dir, code_omit)
        else:
            script_dir = snapshot_dir

        if xtlib_capture:
            # copy XTLIB directory to "xtlib" subdir of temp
            xtlib_dir = file_utils.get_xtlib_dir()
            dest_dir = snapshot_dir + "/xtlib"
            file_utils.ensure_dir_deleted(dest_dir)

            # don't copy the "demo_files" directory
            shutil.copytree(xtlib_dir, dest_dir, ignore=shutil.ignore_patterns("demo_files"))

        console.diag("after create local snapshot")
        return script_dir

    def process_run_command(self, args):
        self.args = args

        # ensure workspace exists
        workspace = args['workspace']
        dry_run = args['dry_run']
        fake_submit = args["fake_submit"]

        if not fake_submit:
            self.store.ensure_workspace_exists(workspace, flag_as_error=False)

        # PRE-PROCESS ARGS
        service_type, cmd_parts, ps_path, parent_script, target_file, run_script, run_cmd_from_script, compute, compute_def = \
            self.process_args(args)

        # create backend helper (pool, philly, batch, aml)
        cluster = utils.safe_value(compute_def, "cluster")
        vc = utils.safe_value(compute_def, "vc")
        self.backend = self.core.create_backend(compute, cluster=cluster, vc=vc, username=None)

        # add conda_packages and pip_packages from SETUP to ARGS
        setup_def = self.config.get_setup_from_target_def(compute_def)

        conda_packages = utils.safe_value(setup_def, "conda-packages")
        pip_packages = utils.safe_value(setup_def, "pip-packages")

        args["conda_packages"] = conda_packages if conda_packages else []
        args["pip_packages"] = pip_packages if pip_packages else []

        self.adjust_pip_packages(args)

        snapshot_dir = self.temp_dir

        if fake_submit:
            script_dir = snapshot_dir
        else:
            # note: always create a snapshot dir for backends to add needed files
            file_utils.ensure_dir_deleted(snapshot_dir)
            script_dir = self.snapshot_all_code(snapshot_dir, cmd_parts, args)

        self.script_dir = script_dir
        direct_run = args["direct_run"]

        # do we need to start the xt controller?
        use_controller = not direct_run
        adjustment_scripts = None

        # create a job_secret that can later be used to authenticate with the XT controller
        # NOTE: we currently log this secret as a job property, which allows all team members to view and control this job
        job_secret = str(uuid.uuid4())

        # do we need to build a "docker run" command?
        if not self.backend.provides_container_support():
            env = args["docker"]
            if not env:
                docker_name = utils.safe_value(compute_def, "docker")
            if docker_name and docker_name != "none":
                cmd_parts = self.build_docker_cmd(docker_name, target_file, cmd_parts, script_dir, snapshot_dir, job_secret, args)
                args["docker"] = docker_name     # for use in building run context info

        # BUILD CMDS (from static hparam search, user multi cmds, or single user cmd)
        cmds, total_run_count, repeat_count, run_specs, using_hp, using_aml_hparam, sweeps_text, pool_info, search_style = \
            self.build_cmds_with_search(service_type, cmd_parts, parent_script, run_script, run_cmd_from_script, use_controller, dry_run, args)

        if dry_run:
            return

        # make new values available
        args["search_style"] = search_style
        args["total_run_count"] = total_run_count

        resume_name = args['resume_name']
        keep_name = False  # args['keep_name']
        experiment = args['experiment']
        is_distributed = args['distributed']
        direct_run = args["direct_run"]

        # CREATE JOB to hold all runs
        if fake_submit:
            # use lastrun/lastjob info to get a fast incremental fake job number
            xtd = xt_dict.read_xt_dict()
            fake_job_num = xtd["fake_job_num"] if "fake_job_num" in xtd else 1
            xtd["fake_job_num"] = fake_job_num + 1
            xt_dict.write_xt_dict(xtd)
            job_id = "fake_job" + str(fake_job_num)
        else:
            job_id = self.store.create_job()
        fb.feedback(job_id)

        # start the feedback (by parts)
        fb.feedback("{}: {}".format("target", compute))

        # write hparams to FILES
        boxes, num_boxes = self.write_hparams_to_files(job_id, cmds, fake_submit, using_hp, args)

        if sweeps_text and not fake_submit:
            self.upload_sweep_data(sweeps_text, experiment, job_id, args=args)

        # if num_boxes > 1 and service_type != "batch":
        #     fb.feedback("", is_final=True)

        parent_name = None

        # BUILD RUNS, by box
        job_runs = []
        run_count = 1 if is_distributed else len(boxes) 
        secrets_by_node = {}
        remote_control = args["remote_control"]

        for i in range(run_count):
            box_name = boxes[i]

            # generate a box secret for talking to XT controller for this node
            box_secret =  str(uuid.uuid4()) if remote_control else ""

            # build runs for box_name
            run_data = self.build_first_run_for_node(i, boxes[i], target_file, ps_path, using_hp, using_aml_hparam, run_specs, job_id, 
                parent_name, cmds, pool_info, repeat_count, fake_submit, search_style, box_secret, args)

            # for now, adhere to the more general design of multiple runs per box
            box_runs = [run_data]      
            job_runs.append(box_runs)

            node_id = utils.node_id(i)            
            secrets_by_node[node_id] = box_secret

            # FEEDBACK 
            ptype = "single " if search_style == "single" else "parent "
            if is_distributed:
                ptype = "master "

            if run_count == 1:
                node_msg = "creating {}run".format(ptype)
            else:
                node_msg = "creating {}runs: {}/{}".format(ptype, i+1, run_count)

            if service_type == "pool":
                node_msg += ", box: " + box_name

            fb.feedback(node_msg, id="node_msg")  # , add_seperator=is_last)
            last_msg = node_msg

            # run the job

        # build box: runs dict for job info file
        runs_by_box, last_run = self.build_runs_by_box(job_runs, workspace)

        # now that we have run names for all static run names for all nodes, we can adjust cmds (and before files) for using the controller
        if use_controller:
            # we will create 2 temp. controller files in the CURRENT DIRECTORY (that will be captured to JOB)
            # this will also adjust commands for each node to run the XT controller
            adjustment_scripts = self.core.adjust_job_for_controller_run(job_id, job_runs, cmds, using_hp, experiment, service_type, snapshot_dir, 
                search_style, args=args)

        else:
            adjustment_scripts = self.core.adjust_job_for_direct_run(job_id, job_runs, cmds, using_hp, experiment, service_type, snapshot_dir, 
                search_style, args=args)

        # add env vars used by both controller and runs
        env_vars = args["env_vars"]

        # create a job guid to uniquely identify this job across all XT instances
        job_guid = str(uuid.uuid4())

        # we add with "node0" and "job_secret", but backend service will override for each node
        scriptor.add_controller_env_vars(env_vars, self.config, None, "node0")

        data_local = args["data_local"]
        if "$scriptdir" in data_local:
            data_local = os.path.realpath(data_local.replace("$scriptdir", script_dir))
            args["data_local"] = data_local

        model_local = args["model_local"]
        if "$scriptdir" in model_local:
            model_local = os.path.realpath(model_local.replace("$scriptdir", script_dir))
            args["model_local"] = model_local

        # ADJUST CMDS: this allows backend to write scripts to snapshot dir, if needed, as a way of adjusting/wrapping run commands
        self.backend.adjust_run_commands(job_id, job_runs, using_hp, experiment, service_type, snapshot_dir, args=args)

        # upload CODE from snapshot_dir
        code_upload = args["code_upload"]
        code_omit = args["code_omit"]
        code_zip = args["code_zip"]
    
        if not fake_submit:
            if code_upload:
                self.core.upload_before_files_to_job(job_id, snapshot_dir, "before/code", code_omit, code_zip, "code", args)

            # upload DATA from data_local (do we need to keep this?  should we upload to normal DATA location, vs. job?)
            data_upload = args["data_upload"]
            if data_upload:
                if not data_local:
                    errors.config_error("cannot do data-upload because no data-local path is defined in the XT config file")

                data_omit = args["data_omit"]
                data_zip = "none"

                self.core.upload_before_files_to_job(job_id, data_local, "before/data", data_omit, data_zip, "data", args)
        
        # dispatch to BACKEND submitters
        '''
        Note: backend submitter functions are responsible for:
            - submitting the job (for each node, queue runs for that node)
            - return service job id (or list of them if per node)

        NOTE: there is a timing issue where submitted job needs access to job info, but final piece
        of job info (service info) is only return after job is submitted.  Therefore, we structure steps as follows:

            - primary job info is logged
            - job is submitted thru backend
            - service info for job is logged
        '''

        # LOG PRIMARY JOB INFO
        dd = {}

        if not fake_submit:
            # mark runs as QUEUED
            for runs in runs_by_box.values():
                first_run = runs[0]
                self.store.log_run_event(workspace, first_run["run_name"], "status-change", {"status": "queued"}) 

            # write the job info file (now that backend has had a chance to update it)
            job_num = int(job_id[3:])

            xt_cmd = args["xt_cmd"]
            schedule = args["schedule"]
            concurrent = args["concurrent"]

            # this job property is used to ensure we don't exceed the specified # of runs when using repeat_count on each node
            dynamic_runs_remaining = None if search_style == "single" else total_run_count
            node_count = len(runs_by_box)

            # static_runs_by_node = None
            # if schedule == "static":
            #     static_runs_by_node = self.build_static_runs_by_node(total_run_count, node_count)
            #console.diag("static_runs_by_node=", static_runs_by_node)

            active_runs = mongo_run_index.build_active_runs(schedule, total_run_count, node_count)

            dd = {"job_id": job_id, "job_num": job_num, "compute": compute, "ws_name": workspace, "exper_name": experiment, 
                "pool_info": compute_def, "runs_by_box": runs_by_box, 
                "primary_metric": args["primary_metric"], 
                "run_count": total_run_count, "repeat": repeat_count, "search_type": args["search_type"], 
                "username": args["username"], "hold": args["hold"], "started": utils.get_time(),
                "job_status": "submitted", "running_nodes": 0, 
                "running_runs": 0, "error_runs": 0, "completed_runs": 0, "job_guid": job_guid, "job_secret": job_secret,
                "dynamic_runs_remaining": dynamic_runs_remaining, "search_style": search_style,     
                "active_runs": active_runs,  "connect_info_by_node": {}, "secrets_by_node": secrets_by_node,  
                "xt_cmd": xt_cmd, "schedule": schedule, "node_count": node_count, "concurrent": concurrent,
                "service_job_info": None, "service_info_by_node": None,
            }

            self.store.log_job_info(job_id, dd)

        # SUBMIT JOB 
        # NOTE: we use "pool_info" here (vs. compute_def, which has not been updated with explicit args)
        service_job_info, service_info_by_node = self.backend.submit_job(job_id, job_runs, workspace, pool_info, resume_name, 
            repeat_count, using_hp, runs_by_box, experiment, snapshot_dir, adjustment_scripts, args)

        # POST SUBMIT processing

        # update job info 
        if not fake_submit:
            dd["service_job_info"] = service_job_info
            dd["service_info_by_node"] = service_info_by_node
            self.store.log_job_info(job_id, dd)

        # update lastrun/lastjob info
        xtd = xt_dict.read_xt_dict()
        xtd["last_run"] = last_run
        xtd["last_job"] = job_id
        xt_dict.write_xt_dict(xtd)

        # return values for API support (X)
        return cmds, run_specs, using_hp, using_aml_hparam, sweeps_text, pool_info, job_id 

    def distribute_cmds_to_nodes(self, cmds, num_nodes):
        cmds_by_node = {}
        
        # set current node
        node_index = 0

        # build cmd_parts and distribute them among nodes
        for cmd in cmds:
            node_id = "node" + str(node_index)

            if not node_id in cmds_by_node:
                cmds_by_node[node_id] = []

            # split on unquoted spaces
            cmd_parts = utils.cmd_split(cmd)
            cmds_by_node[node_id].append(cmd_parts)

            node_index += 1

            if node_index >= num_nodes:
                node_index = 0

        return cmds_by_node

    def copy_cmds_to_nodes(self, cmds, num_nodes):
        cmds_by_node = {}

        for node_index in range(num_nodes):
            node_id = "node" + str(node_index)
            cmds_by_node[node_id] = cmds

        return cmds_by_node

    def fixup_script_in_cmd(self, cmd):
        cmd_parts = utils.cmd_split(cmd)
        self.remove_script_dir_from_parts(cmd_parts)

        # add "-u" for python cmds
        if len(cmd_parts) > 1 and cmd_parts[0].startswith("python") and cmd_parts[1] != "-u":
            cmd_parts.insert(1, "-u")

        new_cmd = " ".join(cmd_parts)
        return new_cmd

    def read_user_multi_commands(self, using_hp, run_script, cmd_parts, args):
        cmds = None
        
        lines = self.config.get("commands")
        if lines:
            # commands specified in the config file
            args["multi_commands"] = True
            multi_commands = True
        else:
            # did user specify --multi-commands
            multi_commands = args["multi_commands"]

        if multi_commands:
            if using_hp:
                errors.combo_error("Cannot specify both -multi-commands and hyperparameter search")

            # read MULTI CMDS
            if not lines:
                fn_cmds = args["script"]  # run_script if run_script else cmd_parts[0]
                lines = file_utils.read_text_file(fn_cmds, as_lines=True)
                lines = [line.strip() for line in lines if line and not line.strip().startswith("#")]

            cmds = [self.fixup_script_in_cmd(line) for line in lines]

        return cmds

    def build_cmds_with_search(self, service_type, cmd_parts, parent_script, run_script, run_cmd_from_script, use_controller, dry_run, args):
        '''
        args:
            - service_type: the type of backend service being used (aml, batch, etc.)
            - cmd_parts: list of the user's ML app and arg/options 
            - parent_script: user-specified script that needs to be run to configure box for all child runs
            - run_script: if user app is a shell script or command line .bat file, the text of file
            - run_cmd_from_script: if user's ML app is a shell or command line script, the run command located within it
            - use_controller: if False, XT controller is not being used (direct run)
            - dry_run: if True, job will not be submitted (user just wants to see list of static runs)

        processing:
            - determine the search_style needed, the associated list of user commands, and the total number of runs

        returns:
            - cmds: the list of 1 or more commands to be run
            - run_count: to total number runs to be executed
            - repeat_count: if number of runs per node (approximately)
            - run_specs: a dictionary of run information (easier to pass around)
            - using_hp: if True, a static or dynamic hyperparameter search is being done
            - using_aml_hparam: if True, we are doing a direct-run AML hyperparameter search
            - sweeps_text: hyperparameter search specs 
            - pool_info: information about the service/pool target
            - search_style: one of: single, multi, repeat, static, dynamic
        '''
        using_hp = False
        show_run_report = True
        repeat_count = None
        using_aml_hparam = False
        search_style = None
        cmds = None

        # get run_cmd
        run_cmd = run_cmd_from_script
        if not run_cmd:
            run_cmd = " ".join(cmd_parts)

        # by default, we return same cmd
        new_run_cmd = run_cmd

        is_aml = (service_type == "aml")        # self.is_aml_ws(workspace)
        use_aml_for_hparam = (is_aml and not use_controller)

        # get info about nodes/boxes
        boxes, pool_info, service_type = box_information.get_box_list(self.core, args=args)
        node_count = len(boxes)

        # HPARAM SEARCH
        cmds, sweeps_text, new_run_cmd = self.build_static_hparam_cmds(run_cmd, node_count, args)
            
        using_hp = not(not sweeps_text)
        if using_hp and use_aml_for_hparam:
            using_aml_hparam = True
            # for AML hyperdrive, we pass only constant args from cmd_parts
            #cmd_parts = [tp for tp in template_parts if tp != '{}']

        if cmds:
            # STATIC HPARAM SEARCH
            run_count = len(cmds)
            search_style = "static"

        runs = args["runs"]
        max_runs = args["max_runs"]

        # USER MULTI CMDS
        multi_cmds = self.read_user_multi_commands(using_hp, run_script, cmd_parts, args)
        if multi_cmds:
            if cmds:
                errors.ComboError("cannot specify both --multi with hyperparameter search")

            cmds = multi_cmds
            if runs:
                run_count = runs
            elif max_runs:
                run_count = min(max_runs, len(cmds))
            else:
                run_count = len(cmds)

            search_style = "multi"
            new_run_cmd = cmds[0]

        if not cmds:
            # SINGLE CMD 
            # DYNAMIC HPARAM or REPEAT or SINGLE search style

            # we will use repeat_count on each node, as needed, to reach specified runs
            run_count = runs if runs else node_count 
            
            if using_hp:
                search_style = "dynamic"
            else:
                search_style = "repeat" if run_count > 1 else "single"

            if search_style != "single":
                repeat_count = math.ceil(run_count / node_count)

            cmds = [new_run_cmd]
            show_run_report = False

        if show_run_report:
            console.print()   
            dr = " (dry-run)" if dry_run else ""
            search_type = args["search_type"]
            stype = "(search-type=" + search_type + ") " if search_style=="static" else ""

            console.print("{} {}runs{}:".format(search_style, stype, dr))

            for i, run_cmd_parts in enumerate(cmds):
                console.print("  {}. {}".format(i+1, run_cmd_parts))

            console.print()   

        # finally, package info into run_specs to make info easier to pass thru various APIs
        new_cmd_parts = utils.cmd_split(new_run_cmd)
        run_specs = {"cmd_parts": new_cmd_parts, "run_script": run_script, "run_cmd": new_run_cmd, "parent_script": parent_script}

        return cmds, run_count, repeat_count, run_specs, using_hp, using_aml_hparam, sweeps_text, pool_info, search_style

    def build_static_hparam_cmds(self, cmd_line, node_count, args):
        '''
        args:
            - cmd_line: user's ML app and its arguments
            - args: dictionary of XT run cmd args/options

        processing:
            - gather hyperparameter search specs from either ML app options or
              user-specified hp-config file
            - if doing random or grid search, generate the commands that comprise
              the search
             
        return:
            - generated run commands
            - the search specs (sweeps text)
            - the run cmd (with hp search options removed, if any found)
        '''
        run_cmds = []
        sweeps_text = None

        num_runs = args["runs"]
        max_runs = args["max_runs"]
        option_prefix = args["option_prefix"]
        search_type = args["search_type"]
        fn_sweeps = args["hp_config"]
        static_search = bool(option_prefix)    # enabled only if we use cmdline options for HP runsets

        if not cmd_line:
            cmd_line = " ".join(cmd_parts)

        # default return values
        run_cmd = cmd_line
        sweeps_text = None
        run_cmds = None

        # gather hyperparameters (command line options or hp-search.yaml file)
        if search_type != None:
            hp_client = HPClient()
            dd = {}
            
            if option_prefix:
                # see if hp search params specified in ML app's command line options
                dd, run_cmd = hp_client.extract_dd_from_cmdline(cmd_line, option_prefix)

            if not dd and fn_sweeps:
                # get hp search params from search.yaml file
                dd = hp_client.yaml_to_dist_dict(fn_sweeps)

            if dd:
                # write parameters to YAML file for run record 
                # and use by dynamic search, if needed
                sweeps_yaml = hp_client.dd_to_yaml(dd)
                sweeps_text = yaml.dump(sweeps_yaml)
                
                # should we preform the search now?
                if static_search and search_type in ["grid", "random"]:
                    hp_sets = hp_client.generate_hp_sets(dd, search_type, num_runs, max_runs, node_count)
        
                    if option_prefix and option_prefix in cmd_line:
                        cmd_line_base = run_cmd
                    else:
                        cmd_line_base = cmd_line

                    run_cmds = hp_client.generate_runs(hp_sets, cmd_line_base)
                else:
                    # dynamic HP
                    pass
                #print("{} commands generated".format(len(run_cmds)))

        return run_cmds, sweeps_text, run_cmd

