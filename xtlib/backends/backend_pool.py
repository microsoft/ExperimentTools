#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# backend_pool.py: handles the platform submit/manage operations for service_types of pool and local
import os
import time
import uuid
import shutil
import stat
from interface import implements

from xtlib import utils
from xtlib import errors
from xtlib import attach
from xtlib import pc_utils
from xtlib import scriptor
from xtlib import constants
from xtlib import file_utils
from xtlib import run_helper
from xtlib import job_helper
from xtlib import process_utils
from xtlib import box_information
from xtlib.xt_client import XTClient

from xtlib.console import console
from xtlib.helpers.feedbackParts import feedback as fb
from xtlib.psm.local_psm_client import LocalPsmClient
from xtlib.psm.remote_psm_client import RemotePsmClient

from .backend_interface import BackendInterface
from .backend_base import BackendBase

class PoolBackend(BackendBase):
    def __init__(self, compute, compute_def, core, config, username=None, arg_dict=None):
        super(PoolBackend, self).__init__(compute, compute_def, core, config, username, arg_dict)

        self.compute = compute
        self.compute_def = compute_def
        self.core = core
        self.config = config
        self.username = username
        self.env_vars = None
        self.client = self.core.client

    def get_name(self):
        return "pool"

    def adjust_run_commands(self, job_id, job_runs, using_hp, experiment, service_type, snapshot_dir, 
        args):
        '''
        This method is called to allow the backend to inject needed shell commands before the user cmd.  This 
        base implementation does so by generating a new script file and adding it to the snapshot_dir.
        '''
        store_data_dir, data_action, data_writable, store_model_dir, model_action, model_writable,  \
            storage_name, storage_key = self.get_action_args(args)

        # local or POOL of vm's
        fn_wrapped = None     # we use same generated script on each box/job
        data_local = args["data_local"]
        model_local = args["model_local"]

        for i, box_runs in enumerate(job_runs):
            # wrap the user commands in FIRST RUN of each box (apply data/model actions)
            br = box_runs[0]
            box_info = br["box_info"]
            box_name = box_info.box_name
            box_secret = br["box_secret"]
            actions = box_info.actions
            node_id = utils.node_id(i)

            is_windows = box_info.box_os == "windows"

            run_specs = br["run_specs"]
            cmd_parts = run_specs["cmd_parts"]
            run_name = br["run_name"]

            if not fn_wrapped:

                # we only do this once (for the first box/job)
                using_localhost =  pc_utils.is_localhost(box_name, box_info.address)

                # data_local overrides store_data_dir for LOCAL machine
                if using_localhost and data_local:
                    store_data_dir = os.path.join(os.path.expanduser(data_local), store_data_dir)
                    data_action = "use_local"
                    if not "data" in actions:
                        actions.append("data")

                # model_local overrides store_model_dir for LOCAL machine
                if using_localhost and model_local:
                    store_model_dir = os.path.join(os.path.expanduser(model_local), store_model_dir)
                    model_action = "use_local"
                    if not "model" in actions:
                        actions.append("model")

                setup = self.config.get_setup_from_target_def(self.compute_def)

                env_vars = self.get_env_vars_for_box(box_name, box_info, i, box_secret)
                post_cmds = []

                # add env vars to script
                setter = "@set" if is_windows else "export"

                for name, value in env_vars.items():
                    cmd = "{} {}={}".format(setter, name, value)
                    post_cmds.append(cmd)

                #"xt download before/code --job={} --unzip "

                fn_wrapped = super().wrap_user_command(cmd_parts, snapshot_dir, store_data_dir, data_action, 
                    data_writable, store_model_dir, model_action, model_writable, storage_name, storage_key, actions, 
                    is_windows=is_windows, sudo_available=False, pip_freeze=False, setup=setup, post_setup_cmds=post_cmds, 
                    args=args, nonempty=True)

            # we update each box's command
            script_part = "{} {} {}".format(os.path.basename(fn_wrapped), node_id, run_name)
            if self.is_windows:
                sh_parts = [script_part]
            else:
                sh_parts = ['/bin/bash', '--login', script_part]
            run_specs["cmd_parts"] = sh_parts

    def submit_job(self, job_id, job_runs, workspace, compute_def, resume_name, 
           repeat_count, using_hp, runs_by_box, experiment, snapshot_dir, controller_scripts, args):

        fake_submit = args["fake_submit"]
        info_by_node = {}
        job_info = {"job": job_id}

        if not fake_submit:
            # first pass - ensure all boxes are NOT already running the controller
            # for i, box_runs in enumerate(job_runs):
            #     box_info = box_runs[0]["box_info"]

            #     box_name = box_info.box_name
            #     box_addr = box_info.address
            #     port = constants.CONTROLLER_PORT

                # if self.core.client.is_controller_running(box_name, box_addr, port):
                #     errors.config_error("XT controller already running on box: " + box_name)

            # second pass - transfer the main script to each box and start it
            for i, box_runs in enumerate(job_runs):
                box_info = box_runs[0]["box_info"]

                # start run on specified box
                service_node_info = self.run_job_on_box(job_id, box_runs, box_index=i, box_info=box_info, app_info=None, 
                    pool_info=compute_def,  resume_name=resume_name, repeat=repeat_count, 
                    using_hp=using_hp, exper_name=experiment, snapshot_dir=snapshot_dir, args=args)

                node_id = "node" + str(i)
                info_by_node[node_id] = service_node_info

        return job_info, info_by_node

    def run_job_on_box(self, job_id, run_data_list, box_index, box_info, app_info, pool_info,  
            resume_name=None, repeat=None, using_hp=None, exper_name=None, snapshot_dir=None, args=None):

        box_name = box_info.box_name
        box_addr = box_info.address
        box_os = box_info.box_os
        is_box_windows = (box_os == "windows")
        
        run_data = run_data_list[0]
        run_name = run_data["run_name"]

        if pc_utils.is_localhost(box_addr=box_addr):
            psm_client = LocalPsmClient()
        else:
            psm_client = RemotePsmClient(box_addr, is_box_windows)

        psm_client.restart_psm_if_needed()
        #print("psm created for box: " + box_addr)

        team = self.config.get("general", "xt-team-name")   
        node_id = utils.node_id(box_index)

        cwd_dir = os.path.expanduser(constants.CWD_DIR)
        fn_src_zip = file_utils.path_join(cwd_dir, constants.CODE_ZIP_FN)

        fn_entry = psm_client.enqueue(team, job_id, run_name, node_id, fn_src_zip)

        service_node_info = {"fn_entry": fn_entry, "box_addr": box_addr, "box_os": box_os, 
            "box_name": box_name, "job_id": job_id, "run_name": run_name}

        fb.feedback("submitted", is_final=True) 

        return service_node_info

    # def old_run_job_on_box(self, job_id, run_data_list, box_index, box_info, app_info, pool_info,  
    #         resume_name=None, repeat=None, using_hp=None, exper_name=None, snapshot_dir=None, args=None):
    #     '''
    #     copy the startup script to the specified box (using SCP) and run it (using SSH)
    #     '''
    #     box_name = box_info.box_name
    #     workspace = args["workspace"]
    #     #console.print("box_name=", box_name, ", box_index=", box_index)

    #     box_addr = box_info.address
    #     is_local = box_addr == "localhost"

    #     src_windows = pc_utils.is_windows()
    #     dst_windows = box_info.box_os == "windows"

    #     hold_open = args["hold"]
    #     run_data = run_data_list[0]
    #     run_name = run_data["run_name"]
    #     ws = args["workspace"]

    #     # kill any running instances of the controller on the box (those that didn't shut down cleanly)
    #     self.client.cancel_thru_os(box_name, False)

    #     # send over files to box
    #     dest_dir = utils.get_controller_cwd(dst_windows, is_local=False)
    #     fn_bootstrap = file_utils.path_join(dest_dir, os.path.basename(self.fn_wrapped))

    #     visible = args["show_controller"]
    #     hold_open = True

    #     if is_local:
    #         # create the directory on the local machine
    #         os.makedirs(os.path.expanduser(dest_dir), exist_ok=True)

    #         # LOCAL box
    #         # COPY the snapshot directory (localhost)
    #         dest_dir = os.path.expanduser(dest_dir)
    #         file_utils.copy_tree(snapshot_dir, dest_dir, omit_dirs="__pycache__")
    #         fb.feedback("files copied to box")
    #         fb.feedback("{}/{}".format(ws, run_name))

    #         # Make the wrapper script executable
    #         if not src_windows:
    #             wrapper_cmd = "{}/{}".format(
    #                 dest_dir,
    #                 constants.FN_WRAPPED_CMDS)
    #             st = os.stat(wrapper_cmd)
    #             os.chmod(wrapper_cmd, st.st_mode | stat.S_IEXEC)

    #         # start controller  (localhost)
    #         fn_log = os.path.expanduser("~/.xt/controller.log")
    #         fn_bootstrap = os.path.expanduser(fn_bootstrap)

    #         if hold_open and visible:
    #             if src_windows:
    #                 os.system("start cmd /K " + fn_bootstrap)
    #             else:
    #                 process_utils.start_async_run_detached(fn_bootstrap, os.path.expanduser(dest_dir), fn_log, visible=visible)
    #         else:            
    #             process_utils.start_async_run_detached(fn_bootstrap, os.path.expanduser(dest_dir), fn_log, visible=visible)

    #     else:
    #         # REMOTE box
    #         # copy the .zip file using scp
    #         src_dir = os.path.expanduser(constants.CWD_DIR)
    #         fn_src = file_utils.path_join(src_dir, constants.CODE_ZIP_FN)
    #         fn_src = os.path.expanduser(fn_src)

    #         fn_dest = file_utils.path_join(dest_dir, constants.CODE_ZIP_FN)

    #         # create the directory on the pool machine thru SSH
    #         cmd = "mkdir -p {}".format(dest_dir)
    #         fb.feedback("[md")
    #         err_code2, output2 = process_utils.sync_run_ssh(self, box_addr, cmd)

    #         # run the COPY thru SCP
    #         fb.feedback("cp")
    #         process_utils.scp_copy_file_to_box(self, box_addr, fn_src, fn_dest)

    #         # unzip the file
    #         # 1. we need the remote box expanded fn_dest
    #         err_code, output = process_utils.sync_run_ssh(self, box_addr, "ls " + fn_dest)
    #         full_fn_dest = output.strip().split("\n")[-1]

    #         #cmd = ''' python -c \\"import zipfile;  zip = zipfile.ZipFile('{}', 'r'); zip.extractall('{}')\\" '''.format(full_fn_dest, os.path.dirname(full_fn_dest))
    #         py_cmd = "import zipfile; zip = zipfile.ZipFile('{}', 'r'); zip.extractall('{}')".format(full_fn_dest, os.path.dirname(full_fn_dest))
    #         ssh_cmd = 'python -c "{}"'.format(py_cmd)
    #         fb.feedback("unzip]")
    #         err_code2, output2 = process_utils.sync_run_ssh(self, box_addr, ssh_cmd)

    #         fb.feedback("files copied to box")
    #         fb.feedback("{}/{}".format(ws, run_name))

    #         # start the run
    #         run_in_cmd_window = visible

    #         if run_in_cmd_window:
    #             # for debugging, open a new cmd window and watch real-time output from remote box
    #             cmd = "bash --login " + fn_bootstrap
    #             ssh_parts = process_utils.make_ssh_cmd_parts(box_addr, cmd)
    #             ssh_cmd = " ".join(ssh_parts)

    #             local_cwd = utils.get_controller_cwd(True, is_local=True)
    #             fn_ssh = os.path.join(local_cwd, "run_ssh.bat")
    #             fn_log = os.path.join(local_cwd, "run_ssh.log")
    #             file_utils.write_text_file(fn_ssh, ssh_cmd)

    #             if hold_open and visible:
    #                 os.system("start cmd /K " + fn_ssh)
    #             else:
    #                 process_utils.start_async_run_detached(fn_ssh, local_cwd, fn_log, visible=True)
    #         else:
    #             # normal run 
    #             #cmd = "bash --login " + fn_bootstrap
    #             cmd = 'nohup bash --login {} </dev/null > ~/.xt/controller.log 2>&1 &'.format(fn_bootstrap) 

    #             process_utils.sync_run_ssh(self, box_addr, cmd)

    #     fb.feedback("submitted", is_final=True)  
        
    #     monitor_url = None

    #     service_node_info = {"job_id": job_id, "node_index": box_index, "box_name": box_name, "monitor_url": monitor_url}

    #     return service_node_info

    def get_env_vars_for_box(self, box_name, box_info, nodex_index, box_secret):
        #box_secrets.set_secret(box_name, box_secret)

        box_os = box_info.box_os
        max_runs = box_info.max_runs

        node_id = "node" + str(nodex_index)
        env_vars = {}
        scriptor.add_controller_env_vars(env_vars, self.config, box_secret, node_id)

        return env_vars

    def get_client_cs(self, service_node_info):
        '''
        Args:
            service_node_info: info that service maps to a compute node for a job
        Returns:
            {"ip": value, "port": value, "box_name": value}
        '''
        box_name = service_node_info["box_name"]
        controller_port = constants.CONTROLLER_PORT
        tensorboard_port = None
        ssh_port = 22

        if not box_name in self.config.get("boxes"):
            if pc_utils.is_localhost(box_name):
                box_name = "local"

        box_addr = self.config.get("boxes", box_name, dict_key="address", default_value=box_name, 
            prop_error="box not defined in config file: " + box_name)

        if "@" in box_addr:
            # strip off the username
            _, box_addr = box_addr.split("@", 1)
        #console.print("box_addr=", box_addr)

        if not "." in box_addr and box_addr != "localhost":
            raise Exception("box option must specify a machine by its IP address: " + str(box_addr))

        cs = {"ip": box_addr, "port": controller_port, "box_name": box_name}
        return cs
    
    def view_status(self, run_name, workspace, job, monitor, escape_secs, auto_start, 
            stage_flags, status, max_finished):

        # boxes, pool_info, service_type = box_information.get_box_list(self.core, job_id=job, pool=self.compute)

        # def monitor_work():
        #     # BOX LOOP
        #     text = ""
        #     for b, box_name in enumerate(boxes):
        #         # make everyone think box_name is our current controller 
        #         self.client.change_box(box_name)

        #         if run_name in ["tensorboard", "mirror"]:
        #             text += self.get_box_process_status_inner(box_name, wworkspaces, run_name)
        #         else:
        #             text += self.core.get_box_run_status_inner(box_name, workspace, run_name, stage_flags)

        #     return text

        # # MONITOR-ENABLED COMMAND
        # attach.monitor_loop(monitor, monitor_work, escape_secs=escape_secs)
        results = []
        job_info = job_helper.get_job_record(self.core.store, "job12070")
        service_info_by_node = job_info.get("service_info_by_node", {})
        for _, service_node_info in service_info_by_node.items():
            result = self.get_service_queue_entries(service_node_info)
            results.append(result)

        return results

    def cancel_runs_by_names(self, workspace, run_names, box_name):
        '''
        Args:
            workspace: the name of the workspace containing the run_names
            run_names: a list of run names
            box_name: the name of the box the runs ran on (pool service)
        Returns:
            cancel_results: a list of kill results records 
                (keys: workspace, run_name, exper_name, killed, status, before_status)
        '''

        # our strategy for this API: 
        #   - use the XT controller to kill specified runs (when controller is available)
        #   - use batch_client "cancel node" if controller not available

        # we build service-based box names to have 3 parts
        active_jobs = self.get_active_jobs()
        cancel_results = []
        if active_jobs:
            for job_record in active_jobs:
                service_job_info = job_record["service_job_info"]
                service_info_by_node = job_record["service_info_by_node"]
                for node, node_service_info in service_info_by_node.items():
                    if node_service_info.get("run_name") in run_names:
                        cancel_result = self.cancel_node(node_service_info)
                        cancel_results.append(cancel_result)

        return cancel_results

    def cancel_runs_by_property(self, prop_name, prop_value, box_name):
        cancel_results = None

        try:
            # connect to specified box
            if self.client.change_box(box_name):
                cancel_results = self.client.cancel_runs_by_property(prop_name, prop_value)
            else:
                console.print("couldn't connect to controller for {}".format(box_name))
        except BaseException as ex:
            errors.report_exception(ex)
            pass

        return cancel_results
        
    def cancel_runs_by_job(self, job_id, runs_by_box):
        '''
        Args:
            job_id: the name of the job containing the run_names
            runs_by_box: a dict of box_name/run lists
        Returns:
            cancel_results_by box: a dict of box_name, cancel_result records
                (keys: workspace, run_name, exper_name, killed, status, before_status)
        '''
        cancel_results_by_box = {}

        for box_name, runs in runs_by_box.items():
            cancel_results = self.cancel_runs_by_property("job_id", job_id, box_name)
            cancel_results_by_box[box_name] = cancel_results

        return cancel_results_by_box

    def cancel_runs_by_user(self, box_name):
        '''
        Args:
            box_name: the name of the box the runs ran on (pool service)
        Returns:
            cancel_results: a list of kill results records 
                (keys: workspace, run_name, exper_name, killed, status, before_status)
        '''
        active_jobs = self.get_active_jobs()
        cancel_results = []
        if active_jobs:
            for job_record in active_jobs:
                service_job_info = job_record["service_job_info"]
                service_info_by_node = job_record["service_info_by_node"]
                for node, node_service_info in service_info_by_node.items():
                    cancel_result = self.cancel_node(node_service_info)
                    cancel_results.append(cancel_result)

        return cancel_results

    def get_psm_client(self, service_node_info):
        box_os = service_node_info["box_os"]
        box_addr = service_node_info["box_addr"]
        is_box_windows = (box_os == "windows")

        if pc_utils.is_localhost(box_addr=box_addr):
            psm_client = LocalPsmClient()
        else:
            psm_client = RemotePsmClient(box_addr, is_box_windows)

        return psm_client

    # BACKEND API
    def read_log_file(self, service_node_info, log_name, start_offset=0, end_offset=None, 
        encoding='utf-8', use_best_log=True):
        '''
        returns subset of specified log file as text.
        '''
        job_id = service_node_info["job_id"]
        fn_entry = service_node_info["fn_entry"]

        psm_client = self.get_psm_client(service_node_info)

        next_offset = 0
        new_text = None

        # read LOG FILE
        #start = time.time()
        new_bytes = psm_client.read_log_file(fn_entry, start_offset, end_offset)
        next_offset = start_offset + len(new_bytes)
        #utils.report_elapsed(start, "read log")

        new_text = new_bytes.decode(encoding)

        if new_text:
            service_status = "running"
        else:
            # refresh STATUS (takes 1.5, 4.5, or 6 secs)
            #start = time.time()
            service_status = psm_client.get_status(fn_entry)
            #utils.report_elapsed(start, "status")

        simple_status = self.get_simple_status(service_status)

        return {"new_text": new_text, "simple_status": simple_status, "log_name": log_name, "next_offset": next_offset, 
            "service_status": service_status}

    # API call
    def get_simple_status(self, status):
        # translates an BATCH status to a simple status (queued, running, completed)

        queued = ["queued"]
        running = ["running"]
        completed = ["completed"]

        if status in queued:
            ss = "queued"
        elif status in running:
            ss = "running"
        elif status in completed:
            ss = "completed"
        else:
            errors.internal_error("unexpected Pool status value: {}".format(status))

        return ss

    # API call
    def cancel_job(self, service_job_info, service_info_by_node):
        result_by_node = {}

        for node_id, node_info in service_info_by_node.items():
            result = self.cancel_node(node_info)
            result_by_node[node_id] = result

        return result_by_node

    # API call
    def cancel_node(self, service_node_info):

        psm_client = self.get_psm_client(service_node_info)
        fn_entry = service_node_info["fn_entry"]

        service_status = psm_client.get_status(fn_entry)
        simple_status = self.get_simple_status(service_status)
        cancelled = False

        if simple_status != "completed":
            
            cancelled, service_status = psm_client.cancel(fn_entry)
            simple_status = self.get_simple_status(service_status)

        result = {"cancelled": cancelled, "service_status": service_status, "simple_status": simple_status}
        return result

    # API call
    def get_service_queue_entries(self, service_node_info):

        psm_client = self.get_psm_client(service_node_info)
        entries, current = psm_client.enum_queue()

        queue = []
        
        if entries:
            queue = [{"name": entry, "current": False} for entry in entries]

        if current:
            queue.insert(0, {"name": current, "current": True})

        return queue

    def get_active_jobs(self):
        ''' return a list of job_id's running on this instance of Azure Batch '''
        mongo = self.client.store.get_mongo()

        filter_dict = {
            "username": self.username,
            "compute": "local",
            "ws_name": self.config.get("general", "workspace"),
            "job_status": {
                "$nin": ["created", "completed"]
            }
        }

        fields_dict = {"job_id": 1, "service_info_by_node": 1, "service_job_info": 1}

        job_records = mongo.get_info_for_jobs(filter_dict, fields_dict)

        return job_records
