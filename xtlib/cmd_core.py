#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# cmd_core.py: support code for the commands used by XT.
import os
import sys
import json
import time
import math
import shutil
import psutil
import requests
import datetime
import importlib

from .client import Client
from .console import console 
from .helpers.bag import Bag
from .helpers import file_helper
from .backends.backend_batch import AzureBatch
from .report_builder import ReportBuilder   
from .helpers.feedbackParts import feedback as fb

from xtlib import qfe
from xtlib import utils
from xtlib import errors
from xtlib import capture
from xtlib import pc_utils
from xtlib import scriptor
from xtlib import constants
from xtlib import file_utils
from xtlib import process_utils
from xtlib import box_information

# from xtlib import backend_aml 
# from xtlib import backend_pool
# from xtlib import backend_batch
# from xtlib import backend_philly

class CmdCore():
    ''' this class contains state-based (config/store/client) helper functions related mostly to impl-compute'''
    def __init__(self, config, store, client):

        self.config = config
        self.store = store
        self.client = client

    def keygen(self, overwrite=False, fn=constants.LOCAL_KEYPAIR_PRIVATE):
        fn = os.path.expanduser(fn)

        # prevent "overwrite?" msg by first removing file
        if os.path.exists(fn):
            if overwrite:
                os.remove(fn)   
            else:
                errors.user_exit("existing XT keypair found (use --overwrite to force a new keypair to be generated)")

        # call ssh-keygen to do the GENERATION
        cmd_parts = ['ssh-keygen', '-q', '-f', fn]
        exit_code, output = process_utils.sync_run(cmd_parts)
        if exit_code:
            console.print(output)
            return False

        # ensure ssh-agent is ENABLED
        #cmd = "sc config ssh-agent start=demand"
        cmd_parts = ["sc", "config", "ssh-agent", "start=demand"]
        exit_code, output = process_utils.sync_run(cmd_parts, shell=True)
        if exit_code:
            # this call will FAIL unless running in a ADMINISTRATOR command window
            console.print(output)
            return False

        # ensure ssh-agent is RUNNING
        cmd_parts = ["ssh-agent", "s"]
        exit_code, output = process_utils.sync_run(cmd_parts)
        if exit_code:
            console.print(output)
            return False

        # finally, ADD the generated key to the ssh repository
        cmd_parts = ['ssh-add', fn]
        #console.print("keygen: cmd=", cmd)
        exit_code, output = process_utils.sync_run(cmd_parts)
        if exit_code:
            console.print(output)
            return False

        return True

    def keysend(self, box_name):
        box_addr = self.config.get("boxes", box_name, dict_key="address", default_value=box_name)
        box_os = self.config.get("boxes", box_name, dict_key="os", default_value="linux")

        #console.print("box_addr=", box_addr)
        fn_local_key = os.path.expanduser(constants.LOCAL_KEYPAIR_PUBLIC)
        #fn_log = utils.expand_vars(TEMP_SSH_LOG)

        if not os.path.exists(fn_local_key):
            errors.env_error("xt keypair not yet created; please run the 'xt keygen' command first")

        # copy the key to a temp file location on the box
        if box_os == "windows":
            temp_key_fn = "temp_key_file"
        else:
            temp_key_fn = "/tmp/temp_key_file"

        # NOTE: the "-o IdentitiesOnly=yes" option of is used to prevent the "too many authentication errors" problem 
        #cmd = 'scp -o IdentitiesOnly=yes "{}" {}:{}'.format(fn_local_key, box_addr, temp_key_fn)
        cmd_parts = ["scp", "-o", "IdentitiesOnly=yes", fn_local_key, "{}:{}".format(box_addr, temp_key_fn)]
        console.diag("  copying key file to box: cmd={}".format(cmd_parts))

        # SCP COPY
        exit_code, output = process_utils.sync_run(cmd_parts)
        if exit_code:
            console.print(output)
            return False

        # now, run commands on box to append the temp file to ~/.ssh/authorized_keys

        if box_os == "windows":
            AUTHORIZED_KEYS_FILE = ".ssh/authorized_keys"
            cmds = [
                "mkdir .ssh",    # ensure directory exists (if first key)
                "del {}".format(AUTHORIZED_KEYS_FILE),
                "type {} >> {}".format(temp_key_fn, AUTHORIZED_KEYS_FILE),   # append key to file
                "del {}".format(temp_key_fn)     # remove temp file
            ]
            cmdline = "&".join(cmds)
        else:
            AUTHORIZED_KEYS_FILE = "~/.ssh/authorized_keys"
            cmds = [
                "mkdir -p ~/.ssh",    # ensure directory exists (if first key)
                "cat {} >> {}".format(temp_key_fn, AUTHORIZED_KEYS_FILE),   # append key to file
                "rm {}".format(temp_key_fn)     # remove temp file
            ]
            cmdline = ";".join(cmds)

        # NOTE: the "-o IdentitiesOnly=yes" option of is used to prevent the "too many authentication errors" problem 
        #cmd = 'ssh -o IdentitiesOnly=yes {} "{}"'.format(box_addr, cmdline)
        cmd_parts = ['ssh', '-o', 'IdentitiesOnly=yes', box_addr, cmdline]
        console.diag("  running cmds on box={}".format(cmd_parts))

        # SSH COMMANDS
        exit_code, output = process_utils.sync_run(cmd_parts)
        if exit_code:
            console.print(output)
            return False

        return True

    def get_ip_addr_from_box_addr(self, box_addr):
        ip_addr = None

        if box_addr:
            if "@" in box_addr:
                ip_addr = box_addr.split("@")[1]
            else:
                ip_addr = box_addr
        return ip_addr

    def get_runs_by_boxes_from_job(self, job_id):
        cancel_results_by_boxes = {}

        if not job_helper.is_job_id(str(job_id)):
            errors.syntax_error("not a valid job id: " + str(job_id))

        #console.print("job_id=", job_id)
        text = self.store.read_job_info_file(job_id)
        job_info = json.loads(text)
        runs_by_box = job_info["runs_by_box"]

        return runs_by_boxes

    def cancel_runs_by_boxes(self, runs_by_box):
        cancel_results_by_boxes = {}

        for box_name, run_datas in runs_by_box.items():
            cancel_results = None

            try:
                if utils.is_azure_batch_box(box_name):
                    job_id, service, node_index = box_name.split("-")
                    azure_batch = AzureBatch(core=self)
                    cancel_results, _ = azure_batch.cancel_job_node(self.store, job_id, node_index, run_datas)
                else:
                    # connect to specified box
                    self.client.change_box(box_name)

                    cancel_results = self.client.cancel_runs(run_datas)
            except BaseException as ex:
                errors.report_exception(ex)
                pass

            cancel_results_by_boxes[box_name] = cancel_results

        return cancel_results_by_boxes


    def create_context_file_core(self, run_data_list, node_index, job_id, using_hp,  
        app_info, exper_name, args):
        ''' create a "node context" JSON data object describing all of the runs we need to do for the 
        current node.  the xt controller will use this file to queue up all of the
        runs when it starts.
        '''
        node_runs = []
        #upn = self.config.vault.keys["user_principle_name"]

        node_context = {"job_id": job_id, "node_index": node_index, "runs": node_runs}
        run_names = ""

        for run_data in run_data_list:

            run_specs = run_data["run_specs"]
            cmd_parts = run_specs["cmd_parts"]

            run_name = run_data["run_name"]
            box_name = run_data["box_name"]
            repeat = run_data["repeat"]
            box_info = run_data["box_info"]

            #exper_name, app_name, app_info = self.get_exper_name(cmd_parts)
            # exper_name = app_info.exper_name
            # app_name = app_info.app_name

            # build the context for this run
            run_context = self.get_client_context(exper_name, run_name, None, box_info, 
                node_index=node_index, job_id=job_id, run_specs=run_specs, using_hp=using_hp, repeat=repeat,
                args=args)

            run_context.cmd_parts = cmd_parts
            run_context = run_context.__dict__

            node_runs.append(run_context)
            if run_names == "":
                run_names = run_name
            else:
                run_names += ", " + run_name

        return node_context
        

    def create_context_file(self, run_data_list, node_index, job_id, tmp_dir, using_hp,  
        app_info, exper_name, args):
        ''' create a "node context" JSON file describing all of the runs we need to do for the 
        current node.  the xt controller will use this file to queue up all of the
        runs when it starts.
        '''
        node_context = self.create_context_file_data(run_data_list, node_index, job_id, using_hp, app_info, exper_name, args)
        
        fn_context = tmp_dir + "/" + constants.FN_MULTI_RUN_CONTEXT 
        text = json.dumps(node_context, indent=4)
        with open(fn_context, "wt") as tfile:
            tfile.write(text)

        return fn_context, run_names

    def get_client_context(self, exper_name, run_name, app_info, box_info, job_id, node_index, run_specs, resume_name=None, 
            using_hp=False, repeat=None, args=None):
        '''
        this function gathers up all of the job-level context needed to run the job on the specified node (node_index).
        '''
        config = self.config
        cmd_parts = run_specs["cmd_parts"]
        workspace = args['workspace']
        working_dir = args['working_dir']

        context = Bag()

        context.ws = workspace
        context.working_dir = working_dir
        context.exper_name = exper_name
        context.run_name = run_name
        context.job_id = job_id
        context.sku = args["sku"]
        context.app_name = app_info.app_name if app_info else None
        context.box = args["box"]
        context.from_ip = pc_utils.get_ip_address()
        context.from_host = pc_utils.get_hostname()
        context.box_name = box_info.box_name
        context.target_file, _, _ = self.get_target(cmd_parts)
        context.resume_name = resume_name
        context.generated_sweep_text = None             # will be conditionally set in controller 

        context.pool = args["pool"]
        context.node_index = node_index
        context.compute = args["target"]
        context.service_type = args["service_type"]

        # provide all provider info to controller 
        context.providers = config.get("providers")
        
        #context.run_specs = run_specs
        context.cmd_parts = cmd_parts
        context.xt_cmd = args["xt_cmd"]     # log our full cmd to support correct rerun's
        context.run_script = run_specs["run_script"]
        context.parent_script = run_specs["parent_script"]

        # for helping docker login to user's Azure Container Registry
        is_docker = (args["docker"] != None)
        # if cmd_parts:
        #     is_docker = (cmd_parts[0] == "docker") or (cmd_parts[0] == "sudo" and cmd_parts[1] == "docker")

        #registry = config.get("environment", "registry", suppress_warning=True)
        registry = None
        compute_def = args["compute_def"]
        if compute_def and "docker" in compute_def:
            docker_name = compute_def["docker"]
            docker_def = self.config.get_docker_def(docker_name)
            if docker_def and "registry" in docker_def:
                registry = docker_def["registry"]

        if registry:
            registry_creds = config.get("external-services", registry)
            needs_login = is_docker and utils.safe_value(registry_creds, "login")
            login_server = utils.safe_value(registry_creds, "login-server")
            username = utils.safe_value(registry_creds, "username")
            password = utils.safe_value(registry_creds, "password")
        else:
            needs_login = False
            login_server = None
            username = None
            password = None

        context.docker_login = needs_login
        context.docker_server = login_server
        context.docker_username = username
        context.docker_password = password

        context.username = self.config.get("general", "username")

        setup = self.config.get_setup_from_target_def(compute_def)
        activate_cmd = utils.safe_value(setup, "activate")
        context.activate_cmd = activate_cmd

        # config info
        #box_os = self.get_box_os(box_name)
        box_os = box_info.box_os
  
        after_files_list = args["after_dirs"]
        after_files_list = utils.parse_list_option_value(after_files_list)
        context.after_files_list = after_files_list

        after_omit_list = args["after_omit"]
        after_omit_list = utils.parse_list_option_value(after_omit_list)
        context.after_omit_list = after_omit_list

        context.primary_metric = args["primary_metric"]
        context.maximize_metric = args["maximize_metric"]
        context.report_rollup = args["report_rollup"]

        context.after_upload = args["after_upload"]
        #context.scrape = config.get("general", "scrape")
        context.log = args["log"]

        # PARENT/CHILD info
        context.repeat = repeat
        context.repeats_remaining = None      # will be set in controller
        context.total_run_count = args["total_run_count"]
        context.search_style = args["search_style"]
        context.is_parent = context.search_style != "single"

        # HPARAM search
        hp_config = args["hp_config"]
        if hp_config:
            hp_config = file_utils.path_join(constants.HP_CONFIG_DIR, os.path.basename(hp_config))

        context.hp_config = hp_config
        context.fn_generated_config = args["fn_generated_config"]
        context.using_hp = using_hp
        context.search_type = args["search_type"]
        context.option_prefix = args["option_prefix"]

        context.restart = False
        context.concurrent = args["concurrent"]
        context.xtlib_capture = args["xtlib_upload"]

        # for mirroring files to grok server or storage
        context.mirror_dest = args["mirror_dest"]
        context.mirror_files =  args["mirror_files"]
        context.grok_server = None   # args["grok_server"]

        context.aggregate_dest = args["aggregate_dest"]
        context.dest_name = exper_name if context.aggregate_dest == "experiment" else job_id

        store_creds = self.config.get_storage_creds()
        context.store_creds = store_creds
        context.store_code_path = config.get_storage_provider_code_path(store_creds)

        mongo_creds, mongo_name = self.config.get_mongo_creds()
        context.mongo_conn_str = mongo_creds["mongo-connection-string"]

        context.shell_launch_prefix = box_info.shell_launch_prefix
        
        #console.print("context=", context)
        return context

    def get_fn_run(self, args):
        # find first non-option at end of cmd to mark end of "fn_run"
        fn_run = ""

        #console.print("get_fn_run: args=", args)
        if not args:
            errors.internal_error("get_fn_run: args cannot be empty")

        if len(args) >= 2:
            if args[0] == "run":
                fn_run = os.path.abspath(args[1])
            elif args[0] == "python":
                # skip over python options
                index = 1
                while index < len(args) and args[index].startswith("-"):
                    index += 1
                if index < len(args):
                    fn_run = os.path.abspath(args[index])

        #console.print("fn_run=", fn_run)
        return fn_run

    def get_target(self, cmd_parts):
        target = None
        before_parts = None
        after_parts = None

        if cmd_parts:
            if cmd_parts[0] == "python":
                cmd_parts = cmd_parts[1:]
            elif cmd_parts[0] == "docker":
                cmd_parts = cmd_parts[1:]
                if cmd_parts[0] == "run":
                    cmd_parts = cmd_parts[1:]
    
            for i, arg in enumerate(cmd_parts):
                if len(arg) and not arg[0] in ["-", "$", "%"]:
                    target = arg
                    before_parts = cmd_parts[:i]
                    after_parts = cmd_parts[i+1:]
                    break

        return target, before_parts, after_parts

    def docker_login(self, server, username, password):
        exit_code, output = process_utils.sync_run(["docker", "login", server, "--username", username, "--password", password],  capture_output=True, shell=False, report_error=True)
        return output

    def docker_logout(self, server):
        exit_code, output = process_utils.sync_run(["docker", "logout", server],  capture_output=True, shell=False, report_error=True)
        return output
        
    def collect_logs_for_run(self, ws_name, run_name, log_wc_path, grok_server):
        _, blob_paths = self.store.get_run_filenames(ws_name, run_name, log_wc_path)
        temp_path = file_utils.make_tmp_dir("collect")
        count = 0

        for blob_path in blob_paths:
            # transfer one file at a time to grok server
            local_fn = os.path.join(temp_path, os.path.basename(blob_path))
            self.store.download_file_from_run(ws_name, run_name, blob_path, local_fn)

            with open(local_fn, 'rb') as fin:
                files = {'file': fin}

                # send to grok server
                payload = {"ws_name": ws_name, "run_name": run_name, "append": False, "rel_path": blob_path}
                #console.print("collect_logs_for_run: payload=", payload)

                result = requests.post(url="http://" + grok_server + "/write_file", files=files, params=payload)
                console.print("collect_logs_for_run: POST result=", result)
                count += 1

        return count

    def adjust_job_for_direct_run(self, job_id, job_runs, cmds, using_hp, experiment, service_type, 
            snapshot_dir, search_style, args):

        # write 1st file to SNAPSHOT (first run's context file)
        fn_run_context = snapshot_dir + "/" + constants.FN_RUN_CONTEXT 
        file_utils.ensure_dir_exists(file=fn_run_context)
        
        box_runs = job_runs[0]
        cfc = self.create_context_file_core(box_runs, 0, job_id, using_hp,  
            app_info=None, exper_name=experiment, args=args)
        context_data = cfc["runs"][0]
        
        text = json.dumps(context_data, indent=4)
        with open(fn_run_context, "wt") as tfile:
            tfile.write(text)

        utils.copy_to_submit_logs(args, fn_run_context)

        return [fn_run_context]
            
    def adjust_job_for_controller_run(self, job_id, job_runs, cmds, using_hp, experiment, service_type, 
            snapshot_dir, search_style, args):
        ''' 
        submit direct job:
            - backend.commands: some internal prep cmds and the run command(s) specified by the user
            - backend.env_var: these are set to pass a small subset of the context for the runs
            - backend.source_files: the user's source files, the run's context file

        submit controller job:
            - backend.commands: some internal prep cmds and a command line to run the XT controller
            - backend.env_var: not used
            - backend.source_files: the user's source files, controller MULTI_RUN_CONTEXT file, controller script file
        '''

        # for EACH NODE, collect and adjust runs 
        context_by_nodes = {}

        for i, box_runs in enumerate(job_runs):

            node_context = self.create_context_file_core(box_runs, i, job_id, using_hp,  
                app_info=None, exper_name=experiment, args=args)

            node_id = "node" + str(i)
            context_by_nodes[node_id] = node_context

            new_box_runs = self.adjust_box_runs_for_controller(i, box_runs)
            job_runs[i] = new_box_runs

        # write 1st file to SNAPSHOT (MRC file)
        fn_context = snapshot_dir + "/" + constants.FN_MULTI_RUN_CONTEXT 
        file_utils.ensure_dir_exists(file=fn_context)
        
        mrc_data = { "context_by_nodes": context_by_nodes, "cmds": cmds, "search_style": search_style }
        text = json.dumps(mrc_data, indent=4)
        with open(fn_context, "wt") as tfile:
            tfile.write(text)

        # also write the MRC file to the job store (to support wrapup of runs after job is cancelled)
        self.store.create_job_file(job_id, constants.FN_MULTI_RUN_CONTEXT, text)

        # write 2rd file to SNAPSHOT
        fn_script = snapshot_dir + "/" + constants.PY_RUN_CONTROLLER
        is_aml = (service_type == "aml")

        with open(fn_script, "wt") as outfile:
            external_controller_port = constants.CONTROLLER_PORT

            text = ""
            text += "import sys\n"
            text += "sys.path.insert(0, '.')    # support for --xtlib-upload \n"
            text += "from xtlib.controller import run\n"
            text += "run(multi_run_context_fn='{}', port={}, is_aml={})\n".format(constants.FN_MULTI_RUN_CONTEXT, external_controller_port, is_aml)

            outfile.write(text)

        utils.copy_to_submit_logs(args, fn_context)
        utils.copy_to_submit_logs(args, fn_script)

        return [fn_context, fn_script]

    def adjust_box_runs_for_controller(self, node_id, box_runs):
        first_box_run = box_runs[0]
        box_info = first_box_run["box_info"]

        # use first run_name as name of the controller-mode run
        run_name = first_box_run["run_name"]

        # these fields are not used when running controller
        repeat_count = None 
        run_script = None   
        parent_script = None

        target_fn = constants.PY_RUN_CONTROLLER
        cmd_parts = ["python", "-u", target_fn]
        run_cmd = " ".join(cmd_parts)

        run_specs = {"cmd_parts": cmd_parts, "run_script": run_script, "run_cmd": run_cmd, "parent_script": parent_script}

        # create a single run_data that will run the controller for this node
        run_data = {"box_info": box_info, "box_name": box_info.box_name, "repeat": repeat_count, "run_name": run_name, 
            "box_secret": first_box_run["box_secret"], "run_specs": run_specs}
        new_box_runs = [run_data]

        return new_box_runs

    def upload_before_files_to_job(self, job_id, source_dir, store_dir, omit_list, zip_type, upload_type, args):

        # holds all data needed for each run, on each box 
        job_runs = []
        resume_name = args['resume_name']
        omit_list = utils.parse_list_option_value(omit_list)
        remove_prefix_len = 1 + len(source_dir)

        if zip_type is True:
            zip_type = "fast"

        console.diag("before upload of {} to job".format(upload_type.upper()))
  
        copied_files = capture.capture_before_files_zip(self.store, source_dir=source_dir, omit_files=omit_list, store_dest=store_dir,
            rerun_name=resume_name, job_id=job_id, zip_before=zip_type, remove_prefix_len=remove_prefix_len, upload_type=upload_type)

        #fb.feedback("{} target file(s) uploaded to {}".format(len(copied_files), dest_name))
        fb.feedback("")    # just add comma to indicte current op has completed

        console.diag("after upload of {} to job".format(upload_type.upper()))
        return copied_files

    def create_backend(self, compute, username=None, cluster=None, vc=None):
        '''
        TODO: replace "cluster" and "vc" arguments with regularized 
        "compute_def" argument.
        '''

        compute_def = self.config.get_compute_def(compute)
        service = compute_def["service"]
        service_type = self.config.get_service_type(service)

        if not username:
            # not specified as an option; default to config file
            username = self.config.get("general", "username")

        if not cluster:
            # not specified as an option; default to compute-def
            if "cluster" in compute_def:
                cluster = compute_def["cluster"]

        if not vc:
            # not specified as an option; default to compute-def
            if "vc" in compute_def:
                vc = compute_def["vc"]

        # get code_path for service_name from compute_providers
        service_name = "pool" if service_type == "local" else service_type
        backend_ctr = self.config.get_provider_class_ctr("compute", service_name)

        # instantiate the associated backend class
        arg_dict = {"cluster": cluster, "vc": vc}

        '''
        TODO: eliminate "arg_dict" argument for backend CTR by regularizing all options into "compute_def".
        '''
        backend = backend_ctr(compute=compute, compute_def=compute_def, core=self, config=self.config, username=username, arg_dict=arg_dict)
        return backend

    def get_box_run_status_inner(self, box_name, ws=None, run_name=None, stage_flags=""):
        ''' requires that the desired box is the current box'''
        text = ""

        info = box_information.get_box_addr(self.config, box_name, self.store)
        box_addr = info["box_addr"]
        controller_port = info["controller_port"]

        if not self.client.is_controller_running(box_name, box_addr, controller_port):
            text += "box: " + box_name + "\n"
            text += "  controller is NOT running\n"
        else:
            self.client.change_box(box_name, port=controller_port)

            #text += self.get_core_status(ws) + "\n"
            text += "\n" + self.get_box_status(box_name=box_name) + "\n"

            text +=  "\n" + stage_flags + " runs on " + box_name.upper() + ":\n"
            text += self.client.jobs_report(ws=ws, run_name=run_name, stage_flags=stage_flags)

        return text

    def get_box_status(self, indent="", box_name=None):
        elapsed = self.client.get_controller_elapsed()
        elapsed = str(datetime.timedelta(seconds=elapsed))
        elapsed = elapsed.split(".")[0]   # get rid of decimal digits at end

        xt_version = self.client.get_controller_xt_version()

        cname = "localhost" if box_name=="local" else box_name
        max_runs = self.client.get_controller_max_runs()
        ip_addr = self.client.get_controller_ip_addr()
 
        text = indent + "{} controller (SSL, xtlib: {}, addr: {}, running time: {}, max-runs: {})".format(
            cname.upper(), xt_version, ip_addr, elapsed, max_runs)
        return text

    def filtered_out(self, status, active_only):
        if active_only and status not in ["created", "queued", "allocating", "spawning", "active", "running"]:
            return True
        return False

    def build_jobs_report(self, status_text):

        status_list = status_text.split("\n")[0:-1]

        # create helper for filtering runs to show
        builder = ReportBuilder(self.config, self.store, self)
        status = ""

        if status_list:
            records = []
            for stats in status_list:
                ws, name, status, elapsed = stats.split("^")
                full_name = ws + "/" + name
                #console.print("full_name=", full_name)

                if not self.filtered_out(status, False):
                    elapsed = utils.format_elapsed_hms(elapsed)
                    record = {"name": full_name, "status": status, "elapsed": elapsed}
                    records.append(record)

            result, rows = builder.build_formatted_table(records, avail_cols=["name", "status", "elapsed"])
        else:
            result = "  <none>" + "\n"

        return result

    @classmethod      
    def start_xt_server(cls, pid=None):
        # launch in visible window
        import subprocess
        DETACHED_PROCESS = 0x00000008
        CREATE_NO_WINDOW = 0x08000000
        MAKE_SERVER_VISIBLE = False

        xtlib_dir = os.path.dirname(__file__)
        fn_script = "{}/xt_server.py".format(xtlib_dir)
        fn_log = os.path.expanduser("~/.xt/tmp/quick_start_server.log")

        parts = ["python", fn_script]
        if pid:
            parts = ["python", fn_script, str(pid)] 

        if MAKE_SERVER_VISIBLE:
            #subprocess.Popen(parts, cwd=".", creationflags=DETACHED_PROCESS)     
            cmd = "start python " + fn_script
            if pid:
                cmd += " " + str(pid)

            #console.print("starting app with cmd=", cmd)
            os.system(cmd) 
        else:
            with open(fn_log, 'w') as output:
                subprocess.Popen(parts, cwd=".", creationflags=CREATE_NO_WINDOW, stdout=output, stderr=subprocess.STDOUT) 

        # give it time to start-up and receive commands
        time.sleep(2)

