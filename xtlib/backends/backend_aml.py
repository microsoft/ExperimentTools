#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# backend_aml.py: support for running jobs under Azure Machine Learning
import os
import json
import shutil
import logging
import urllib.request
from interface import implements

from xtlib import utils
from xtlib import errors
from xtlib import scriptor
from xtlib import file_utils

from xtlib.console import console
from xtlib.hparams import hp_helper
from xtlib.report_builder import ReportBuilder
from xtlib.helpers.feedbackParts import feedback as fb
from xtlib.helpers.notebook_builder import NotebookBuilder
from xtlib.hparams.hp_client import DistWrapper, ListWrapper

from .backend_base import BackendBase
from .backend_interface import BackendInterface

SECTION = "external-services"

# azure library loaded on demand
Workspace = None 
Experiment = None

class AzureML(BackendBase):

    def __init__(self, compute, compute_def, core, config, username=None, arg_dict=None, disable_warnings=True):
        super(AzureML, self).__init__(compute, compute_def, core, config, username, arg_dict)

        self.compute = compute
        self.compute_def = compute_def
        self.core = core
        self.config = config
        self.username = username

        self.store = self.core.store
        self.request = None

        # load azure libraries on demand
        global Workspace, Experiment, Run
        import azureml.core
        from azureml.core import Experiment, Run
        from azureml.core.workspace import Workspace

        if disable_warnings:
            # turn off all azure warnings
            logging.getLogger("azureml").setLevel(logging.ERROR)

    def get_name(self):
        return "aml"

    def adjust_run_commands(self, job_id, job_runs, using_hp, experiment, service_type, snapshot_dir, args):
        '''
        This method is called to allow the backend to inject needed shell commands before the user cmd.  At the
        time this is called, files can still be added to snapshot_dir.
        '''
        store_data_dir, data_action, data_writable, store_model_dir, model_action, model_writable,  \
            storage_name, storage_key = self.get_action_args(args)

        # local or POOL of vm's
        fn_wrapped = None     # we use same script for each box (but with different ARGS)
        username = args["username"]

        for i, box_runs in enumerate(job_runs):
            # wrap the user commands in FIRST RUN of each box (apply data/model actions)
            br = box_runs[0]
            box_info = br["box_info"]
            actions = ["data", "model"]
            run_name = br["run_name"]
            is_windows = False
            node_id = utils.node_id(i)

            run_specs = br["run_specs"]
            cmd_parts = run_specs["cmd_parts"]

            if not fn_wrapped:
                # just wrap the user cmd once (shared by all boxes/nodes)
                assert cmd_parts[0] == "python"
                assert cmd_parts[1] == "-u"
                assert len(cmd_parts[2]) > 0 

                # update the target_fn (might have been switched to the xt controller)
                target_fn = cmd_parts[2]
                arg_parts = cmd_parts[3:]

                setup = self.config.get_setup_from_target_def(self.compute_def)

                # we only do this once (for the first box/job)
                fn_wrapped = super().wrap_user_command(cmd_parts, snapshot_dir, store_data_dir, data_action, 
                    data_writable, store_model_dir, model_action, model_writable, storage_name, storage_key, actions, 
                    is_windows=is_windows, sudo_available=False, username=username, use_username=False, 
                    install_blobfuse=True, setup=setup, change_dir=False, args=args)

                # AML wants a python script, so use our tiny python shim to run wrapped.sh 
                fn_shim = "aml_shim.py"
                fn_from = file_utils.get_xtlib_dir() + "/backends/" + fn_shim
                fn_to = snapshot_dir + "/" + fn_shim
                shutil.copyfile(fn_from, fn_to)

                # copy to submit-logs
                utils.copy_to_submit_logs(args, fn_from)

            # we update each box's command (passing RUN_NAME as arg to wrapped.sh)
            script_part = "{} {} {}".format(os.path.basename(fn_wrapped), node_id, run_name)
            sh_parts = ['/bin/bash', '--login', script_part]

            # pass sh_parts as a single argument to avoid wierd "arg": 1 problems with AML estimators
            wrapped_parts = ["python", "-u", fn_shim, " ".join(sh_parts)]
            run_specs["cmd_parts"] = wrapped_parts

    def provides_container_support(self):
        '''
        Returns:
            returns True if docker run command is handled by the backend.
        '''
        return True
        
    def match_stage(self, run, stage_flags):
        
        status = run["status"]

        if status in ["NotStarted", "Starting", "Provisioning", "Preparing", "Queued"]:
            match = "queued" in stage_flags
        elif status == "Running":
            match = "active" in stage_flags
        else:
            match = "completed" in stage_flags

        return match

    def view_status(self, run_name, workspace, job, monitor, escape_secs, auto_start, 
            stage_flags, status, max_finished):

        # collect all runs by experiment
        aml_ws_name = self.get_service_name()
        experiments = self.get_experiments(aml_ws_name)
        runs_by_exper = {}

        for exper_name, experiment in experiments.items():
            # apply username filter
            if not exper_name.startswith(self.username + "__"): 
                continue

            # request RUNS from AML
            runs = list(experiment.get_runs())

            # convert to a list of dict items
            #runs = [run.__dict__ for run in runs]
            columns = ["number", "id", "status", "xt_run_name", "PORTAL_URL", "tags"]
            runs = [self.object_to_dict(run, columns) for run in runs]

            for run in runs:
                if "tags" in run and "xt_run_name" in run["tags"]:
                    run["xt_run_name"] = run["tags"]["xt_run_name"]
                    del run["tags"]

            runs_by_exper[exper_name] = runs

        # report by stage
        if "queued" in stage_flags:
            self.report_on_runs(runs_by_exper, "queued")

        if "active" in stage_flags:
            self.report_on_runs(runs_by_exper, "active")

        if "completed" in stage_flags:
            self.report_on_runs(runs_by_exper, "completed", max_finished)

    def report_on_runs(self, runs_by_exper, stage, max_items=None):
        runs_reported = 0

        console.print("target={} runs: {}".format(self.compute, stage))

        exper_names = list(runs_by_exper.keys())
        exper_names.sort()

        for exper_name in exper_names:
            runs = runs_by_exper[exper_name]

            # filter runs for this stage
            runs = [run for run in runs if self.match_stage(run, stage)]
            if runs:
                console.print("\nruns for experiment {}:".format(exper_name))

                columns = ["xt_run_name", "status", "id", "number", "PORTAL_URL"]
                lb = ReportBuilder(self.config, self.store, client=None)

                if max_items and len(runs) > max_items:
                    runs = runs[:max_items]

                text, rows = lb.build_formatted_table(runs, columns, max_col_width=100)
                console.print(text)
                runs_reported += len(runs)

        if runs_reported:
            console.print("total runs {}: {}".format(runs_reported, stage))
        else:
            console.print("  no {} runs found\n".format(stage))

    def does_ws_exist(self, ws_name):
        return self.config.name_exists(SECTION, ws_name)
        
    def get_workspaces(self):
        ''' return aml workspaces registered in config file
        '''
        services = self.config.get_group_properties(SECTION)
        names = [ name for name,value in services.items() if "type" in value and value["type"] == "aml"  ]
        return names

    def get_experiments(self, ws_name):
        ws = self.get_aml_ws(ws_name)
        return ws.experiments

    def attach_to_run(self, ws, run_name):
        run = self.get_run(ws, run_name)
        run.wait_for_completion(show_output=True)

    def get_run(self, ws_name, run_name):
        if not "." in run_name:
            errors.general_error("Azure ML run name must be of the form: exper.runname")

        ws = self.get_aml_ws(ws_name)
        console.diag("after get_aml_ws() call")

        exper_name, run_part = run_name.split(".")
        experiment = Experiment(ws, name=exper_name)
        runs = experiment.get_runs(properties={"xt_run_name": run_name})
        console.diag("after experiment.get_runs() call")

        runs = list(runs)
        console.diag("after list(runs), len={}".format(len(runs)))

        # run_number = int(run_part[3:])
        # target_run = None

        #runs = [run for run in runs if run.number == run_number]
        target_run = runs[0] if len(runs) else None
    
        return target_run

    def get_run_files(self, ws_name, run_name):
        run = self.get_run(ws_name, run_name)
        files = run.get_file_names()
        return files

    def download_run_files(self, ws_name, run_name, store_path, local_path):
        run = self.get_run(ws_name, run_name)
        if store_path in [".", "*"]:
            store_path = None
        run.download_files(store_path, local_path)

    def make_monitor_notebook(self, ws_name, run_name):
        lines =  \
        [
            "from xtlib.backend_aml import AzureML \n",
            "from xtlib.helpers.xt_config import XTConfig\n",
            "from azureml.widgets import RunDetails\n",
            "\n",
            "config = XTConfig()\n",
            "azure_ml = AzureML(config, True)\n",
            'run = azure_ml.get_run("{}", "{}")\n'.format(ws_name, run_name),
            "\n",
            "RunDetails(run).show()\n"
        ]

        kernel_name = pc_utils.get_conda_env()
        kernel_display = file_utils.get_kernel_display_name(kernel_name)
        #console.print("kernel_display=", kernel_display)

        builder = NotebookBuilder(kernel_name, kernel_display)
        builder.add_code_cell(lines)
        fn = os.path.expanduser("~/.xt/notebooks/monitor.ipynb")
        builder.save_to_file(fn)
        return fn

    def cancel_run(self, ws_name, run_name):
        console.diag("start of azure_ml.cancel_run()")

        target_run = self.get_run(ws_name, run_name)
        if not target_run:
            errors.store_error("run not found: {}".format(run_name))

        console.diag("after get_run() call")

        before_status = target_run.status.lower()
        if before_status in ["preparing", "queued"]:
            target_run.cancel()
            killed = True
            status = "cancelled"
        elif before_status in ["starting", "running"]:
            target_run.cancel()
            killed = True
            status = "cancelled"
        else:
            killed = False
            status = target_run.status

        console.diag("after run.cancel() call")

        return {"workspace": ws_name, "run_name": run_name, "cancelled": killed, "status": status}
        
    def cancel_runs(self, exper_name, run_names):
        results = []

        for ws_run_name in run_names:
            if "/" in ws_run_name:
                run_name = ws_run_name.split("/")[1]
            else:
                run_name = ws_run_name

            if run_name.startswith("run"):
                run_name = exper_name + "." + run_name
            result = self.cancel_run(ws_name, run_name)
            results.append(result)

        results_by_aml = {"Azure ML": results}
        return results_by_aml

    def get_active_jobs(self):
        ''' return a list of job_id's running on this instance of Azure Batch '''
        mongo = self.store.get_mongo()

        filter_dict = {
            "username": self.username,
            "compute": "aml",
            "job_status": {
                "$nin": ["created", "completed"]
            }
        }

        fields_dict = {"job_id": 1, "service_info_by_node": 1, "service_job_info": 1}

        job_records = mongo.get_info_for_jobs(filter_dict, fields_dict)

        return job_records

    def cancel_runs_by_user(self, box_name):
        '''
        Args:
            box_name: the name of the box the runs ran on (pool service)
        Returns:
            cancel_results: a list of kill results records 
                (keys: workspace, run_name, exper_name, killed, status, before_status)
        '''
        cancel_results = []

        # get list of active jobs from batch
        active_jobs = self.get_active_jobs()
        console.diag("after get_active_jobs()")

        if active_jobs:
            for job_record in active_jobs:
                # watch out for older jobs that didn't have service_job_info/service_info_by_node properties
                service_job_info = utils.safe_value(job_record, "service_job_info")
                service_info_by_node = utils.safe_value(job_record, "service_info_by_node")

                if service_job_info and service_info_by_node:
                    job_id = job_record["job_id"]
                    cancel_result = self.cancel_job(service_job_info, service_info_by_node)
                    for _, node_result in cancel_result.items():
                        cancel_results.append(node_result)

        return cancel_results

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
        job_id, service_name, node_index = box_name.split("-")
        active_jobs = self.get_active_jobs()
        cancel_results = []
        if active_jobs:
            for job_record in active_jobs:
                # watch out for older jobs that didn't have service_job_info/service_info_by_node properties
                service_info_by_node = utils.safe_value(job_record, "service_info_by_node")
                
                if service_info_by_node:
                    for node, node_service_info in service_info_by_node.items():
                        if node_service_info.get("run_name") in run_names:
                            cancel_result = self.cancel_node(node_service_info)
                            cancel_results.append(cancel_result)

        return cancel_results


    def build_env_vars(self, workspace, aml_ws_name, xt_exper_name, aml_exper_name, run_name, job_id, 
        compute_target, username, description, aggregate_dest, node_id, args):

        vars = dict(args["env_vars"])            
        vars["XT_NODE_ID"] = node_id
        
        vars["XT_WORKSPACE_NAME"] = workspace
        vars["XT_EXPERIMENT_NAME"] = xt_exper_name
        vars["XT_RUN_NAME"] = run_name
        vars["XT_RESUME_NAME"] = None

        vars["AML_WORKSPACE_NAME"] = aml_ws_name
        vars["AML_EXPERIMENT_NAME"] = aml_exper_name

        vars["XT_USERNAME"] = username
        vars["XT_DESCRIPTION"] = description
        vars["XT_AGGREGATE_DEST"] = aggregate_dest
        vars["XT_JOB_ID"] = job_id
        vars["XT_COMPUTE_TARGET"] = compute_target

        return vars

    def get_aml_ws(self, ws_name):

        creds = self.config.get("external-services", ws_name, suppress_warning=True)
        if not creds:
            errors.config_error("Azure ML workspace '{}' is not defined in [external-services] section of the XT config file".format(ws_name))

        subscription_id = self.config.get_required_service_property(creds, "subscription-id", ws_name)
        resource_group = self.config.get_required_service_property(creds, "resource-group", ws_name)

        #from azureml.core.authentication import ServicePrincipalAuthentication
        # ws_ex = ws_name + "-ex"
        # svc_pr = None
        # if self.config.name_exists(section, ws_ex):
        #     client_id = self.config.get(section, ws_ex, "client-id")
        #     tenant_id = self.config.get(section, ws_ex, "tenant-id")
        #     client_secret = self.config.get(section, ws_ex, "client-secret")
        #     svc_pr = ServicePrincipalAuthentication(tenant_id=tenant_id, service_principal_id=client_id, service_principal_password=client_secret)

        ws = Workspace(subscription_id, resource_group, ws_name)     # , auth=svc_pr)
        return ws

    def get_aml_ws_sizes(self, aml_ws_name):
        ws = get_aml_ws(self.config, aml_ws_name)

        # TODO: make this an xt cmd: xt list sizes
        from azureml.core.compute import ComputeTarget, AmlCompute
        sizes = AmlCompute.supported_vmsizes(workspace=ws)
        # for size in sizes:
        #     if size["gpus"] > 0:
        #         console.print(size)

        return sizes

    def build_hyperdrive_dict(self, hp_sets):
        hd = {}

        for name, value in hp_sets.items():
            if isinstance(value, HPList):
                hd[name] = choice(*value.values)
            elif isinstance(value, HPDist):
                # convert from comma sep. string to list of float values
                values = utils.get_number_or_string_list_from_text(value.values)

                dist_name = value.dist_name
                #hd[name] = self.make_distribution(dist_name, values)
                hd[name] = hp_helper.build_dist_func_instance(name, dist_name, values)

        return hd

    def build_hyperdrive_dict_from_file(self, fn):
        ''' parse hyperdrive params from text file '''
        hd = {}

        with open(fn, "rt") as infile:
            text_lines = infile.readlines()

        for text in text_lines:
            text = text.strip()
            if not text or text.startswith("#"):
                continue

            if "#" in text:
                # remove comment part of line
                index = text.index("#")
                text = text[0:index].strip()

            name, value = text.split("=")   
            name = name.strip()
            value = value.strip()

            if value.startswith("@"):
                dist_name, values = value[1:].split("(")
                if not dist_name in utils.distribution_types:
                    errors.config_error("Unsupported distribution type: " + dist_name)

                assert values.endswith(")")
                values = values[:-1]   # remove ending paren

                # convert from comma sep. string to list of float values
                values = utils.get_number_or_string_list_from_text(values)

                #hd[name] = self.make_distribution(dist_name, values)
                hd[name] = hp_helper.build_dist_func_instance(name, dist_name, values)
            else:
                # convert from comma sep. string to list of float values
                values = utils.get_number_or_string_list_from_text(value)
                # treat as "choice"
                #hd[name] = self.make_distribution("choice", values)
                hd[name] = hp_helper.build_dist_func_instance(name, "choice", values)

        return hd

    def make_early_term_policy(self, policy_type, eval_interval=1, delay_eval=0, truncation_percentage=.1, slack_factor=None, slack_amount=None):
        from azureml.train.hyperdrive import BanditPolicy, MedianStoppingPolicy, TruncationSelectionPolicy, NoTerminationPolicy

        if policy_type == "bandit":
            policy = BanditPolicy(evaluation_interval=eval_interval, slack_factor=slack_factor, slack_amount=slack_amount, delay_eval=delay_eval)
        elif policy_type == "median":
            policy = MedianStoppingPolicy(evaluation_interval=eval_interval, delay_evaluation=delay_eval)
        elif policy_type == "truncation":
            policy = TruncationSelectionPolicy(truncation_percentage=truncation_percentage, evaluation_interval=eval_interval, delay_evaluation=delay_eval)
        elif policy_type == "none":
            policy = NoTerminationPolicy()
        else:
            errors.config_error("Unrecognized policy type=" + policy_type)
        
        return policy

    def create_hyperdrive_trainer(self, estimator, hd_dict, search_type, metric_name, maximize_metric, early_term_policy, max_total_runs, 
        max_concurrent_runs, max_minutes):

        from azureml.train.hyperdrive import RandomParameterSampling, GridParameterSampling , BayesianParameterSampling

        if search_type == "random":
            ps = RandomParameterSampling(hd_dict)
        elif search_type == "grid":
            ps = GridParameterSampling (hd_dict)
        elif search_type == "bayesian":
            ps = BayesianParameterSampling(hd_dict)
        else:
            errors.config_error("Azure ML Hyperdrive search_type not supported: " + search_type)

        max_concurrent_runs = min(max_total_runs, max_concurrent_runs)

        from azureml.train.hyperdrive import HyperDriveConfig, PrimaryMetricGoal

        trainer = HyperDriveConfig(estimator=estimator, 
            hyperparameter_sampling=ps, 
            policy=early_term_policy, 
            primary_metric_name=metric_name, 
            primary_metric_goal=PrimaryMetricGoal.MAXIMIZE if maximize_metric else PrimaryMetricGoal.MINIMIZE, 
            max_total_runs=max_total_runs,
            max_concurrent_runs=max_concurrent_runs,
            max_duration_minutes=max_minutes)     

        return trainer

    def create_estimator(self, job_id, workspace, aml_ws_name, xt_exper_name, aml_exper_name, run_name, code_dir, target_fn, arg_dict, 
        compute_target, node_id, nodes, fake_submit, args):

        config = self.config
        ps = None

        if not aml_exper_name:
            errors.config_error("experiment name must be specified (thru config file or command line option '--experiment')")

        if fake_submit:
            # for speed of testing, avoid creating real Workspace, Experiment instances
            ws = {"name": aml_ws_name}
            experiment = {"ws": ws, "name": aml_exper_name}
        else:
            ws = self.get_aml_ws(aml_ws_name)
            experiment = Experiment(ws, name=aml_exper_name)

        if compute_target == "amlcompute":
            actual_target = "amlcompute"    # AmlCompute(ws, None)
        else:
            if fake_submit:
                actual_target = "amlcompute"
            else:
                if not compute_target in ws.compute_targets:
                    errors.config_error("compute target '{}' does not exist in AML workspace '{}'".format(compute_target, aml_ws_name))

                actual_target = ws.compute_targets[compute_target]

        # build ENV VARS
        store_creds = self.config.get_storage_creds()

        # store_name = store_creds["name"]
        # store_key = store_creds["key"]

        provider_code_path = config.get_storage_provider_code_path(store_creds)
        
        mongo_creds, mongo_name = self.config.get_mongo_creds()
        mongo_conn_str = mongo_creds["mongo-connection-string"]

        username = args["username"]
        description = args["description"]
        aggregate_dest = args["aggregate_dest"]
        
        env_vars = self.build_env_vars(workspace, aml_ws_name, xt_exper_name, aml_exper_name, run_name, job_id=job_id, 
            compute_target=compute_target, username=username, description=description, aggregate_dest=aggregate_dest, 
            node_id=node_id, args=args)

        framework = args["framework"]
        framework = framework.lower()

        is_distributed = args['distributed']
        dist_training = args["distributed_training"]
        dist_training = dist_training.lower()

        from azureml.train.estimator import Estimator, Mpi, Gloo, Nccl
        from azureml.train.dnn import PyTorch, Chainer, TensorFlow

        fw_dict = {"pytorch": PyTorch, "tensorflow": TensorFlow, "chainer": Chainer, "estimator": Estimator}
        dt_dict = {"mpi": Mpi, "gloo": Gloo, "nccl": Nccl}

        if not framework in fw_dict:
            errors.user_config_errorerror("framework must be set to 'pytorch', 'tensorflow', 'chainer', or 'estimator'")

        estimator_ctr = fw_dict[framework]

        if is_distributed:
            if not dist_training in dt_dict:
                errors.config_error("distributed-training must be set to 'mpi', 'gloo', or 'nccl'")

            distributed_ctr = dt_dict[dist_training]
            distributed_obj = distributed_ctr()
        else:
            distributed_obj = None

        compute_def = args["compute_def"]
        direct_run = args["direct_run"]

        if direct_run:
            # relying on AML for full control (not using XT controller)
            node_count = utils.safe_value(compute_def, "nodes")

            # did cmd line overwrite nodes?
            if args["nodes"]:
                node_count = args["nodes"]

            if node_count is None:
                errors.config_error("must specify 'nodes' property for Azure ML service '{}' in XT config file or as --nodes option in cmd line".format(args["target"]))
        else:
            # run as separate AML runs, each with a single node
            node_count = 1

        vm_size = args["vm_size"]
        conda_packages = args["conda_packages"]
        pip_packages = args["pip_packages"]
        use_gpu = args["use_gpu"]
        framework_version = args["fw_version"]
        max_secs = args["max_seconds"]
        user_managed = args["user_managed"]

        activate_cmd = self.get_activate_cmd()
        if activate_cmd:
            # we have no way of running this on AML before conda_packages and pip_packages are installed (or used to build a docker image)
            errors.config_error("setup.activate property cannot be specified for AML targets")

        #max_secs = 10080 if max_secs <= 0 else max_secs
        
        use_docker = False      
        environment_name = utils.safe_value(compute_def, "docker")
        if environment_name:
            envrionment_def = self.config.get_docker_def(environment_name)
            if envrionment_def:
                use_docker = (envrionment_def["type"] == "docker")

        # workaround AML warning
        if not use_docker:
            use_docker = None

        if self.submit_logs:
            # for testing (this should match exact args used in estimator ctr below)
            self.serializable_estimator = {"source_directory": code_dir, "script_params": arg_dict, "compute_target": actual_target, 
                "vm_size": vm_size, "entry_script": target_fn, "conda_packages": conda_packages, "pip_packages": pip_packages, 
                "use_gpu": use_gpu, "use_docker": use_docker, "framework_version": framework_version, "user_managed": user_managed, 
                "environment_variables": env_vars, "node_count": node_count, "distributed_training": {},
                "max_run_duration_seconds": max_secs}

        if fake_submit:
            estimator = self.serializable_estimator
        else:
            estimator = estimator_ctr(source_directory=code_dir, script_params=arg_dict, compute_target=actual_target, 
                vm_size=vm_size, entry_script=target_fn, conda_packages=conda_packages, pip_packages=pip_packages, 
                use_gpu=use_gpu, use_docker=use_docker, framework_version=framework_version, user_managed=user_managed, 
                environment_variables=env_vars, node_count=node_count, distributed_training=distributed_obj, 
                max_run_duration_seconds=max_secs)

        return estimator, experiment

    def submit_job(self, job_id, job_runs, workspace, compute_def, resume_name, 
            repeat_count, using_hp, runs_by_box, experiment, snapshot_dir, controller_scripts, args):

        username = args["username"]
        aml_exper_name = "{}__{}__{}".format(username, workspace, experiment)
        cwd = os.getcwd()

        compute = args["target"]
        compute_def = args["compute_def"]
        aml_ws_name = compute_def["service"]
        show_aml_run_name = True

        if show_aml_run_name:
            fb.stop_feedback()

        nodes = len(job_runs)
        service_info_by_node = {}

        for i, node_runs in enumerate(job_runs):
            node_info = self.submit_node_runs(job_id, node_runs, workspace, aml_ws_name, experiment, aml_exper_name, compute_def, resume_name, 
                repeat_count, using_hp, compute, runs_by_box, snapshot_dir, i, show_aml_run_name, nodes, args)

            node_id = "node" + str(i)
            service_info_by_node[node_id] = node_info

        fb.feedback("job submitted", is_final=True)

        service_run_info = {}
        return service_run_info, service_info_by_node     

    def submit_node_runs(self, job_id, node_runs, workspace, aml_ws_name, xt_exper_name, aml_exper_name, 
        compute_def, resume_name, repeat_count, using_hp, compute, runs_by_box, code_dir, node_index, 
        show_aml_run_name, nodes, args):

        first_run = node_runs[0]
        first_run_name = first_run["run_name"]
        fake_submit = args["fake_submit"]

        # this indicates we should make serializable versions of estimator and trainer
        self.submit_logs = True or fake_submit  # must be true if we are using fake_submit

        self.serializable_estimator = None
        self.serializable_trainer = None
        
        box_name = first_run["box_name"]

        run_specs = first_run["run_specs"]
        cmd_parts = run_specs["cmd_parts"]
        target_fn = args["script"]
        node_id = "node" + str(node_index)

        assert cmd_parts[0] == "python"
        assert cmd_parts[1] == "-u"
        assert len(cmd_parts[2]) > 0 

        # update the target_fn (might have been switched to the xt controller)
        target_fn = cmd_parts[2]
        arg_parts = cmd_parts[3:]

        # parse target's cmdline args
        arg_dict = {} 
        for ap in arg_parts:
            # arg name can start with or without "-" here
            if "=" in ap:
                name, value = ap.split("=")
                if not value.startswith('"[') and not value.startswith('"@'):
                    arg_dict[name] = value
            else:
                # for unspecified values
                arg_dict[ap] = 1

        compute_target = utils.safe_value(compute_def, "compute")
        if not compute_target:
            errors.config_error("'compute' property missing on compute target '{}' in XT config file".format(compute))

        estimator, experiment = self.create_estimator(job_id, workspace, aml_ws_name, xt_exper_name, aml_exper_name, first_run_name, 
            code_dir, target_fn, arg_dict, compute_target, node_id, nodes, fake_submit, args)

        hp_config = args["hp_config"]
        direct_run = args["direct_run"]

        if using_hp and direct_run:
            # EXPERIMENT with hyperdrive
            max_runs = args["max_runs"]
            max_minutes = args["max_minutes"]

            policy_name = args["early_policy"]
            eval_interval = args["evaluation_interval"]
            delay_eval = args["delay_evaluation"]
            truncation_percentage = args["truncation_percentage"]
            slack_factor = args["slack_factor"]
            slack_amount = args["slack_amount"]

            primary_metric = args["primary_metric"]
            maximize_metric = args["maximize_metric"]
            search_type = args["search_type"]
            concurrent = args["concurrent"]

            max_concurrent_runs = nodes * concurrent

            if max_minutes <= 0:
                #max_minutes = 43200   # aml workaround: None not supported, either is -1 or 0, so use max value
                max_minutes = 10080   # aml workaround: documented max not supported

            if hp_sets:
                hd_dict = self.build_hyperdrive_dict(hp_sets)
            else:
                hd_dict = self.build_hyperdrive_dict_from_file(hp_config)

            if not policy_name:
                # use default policy (not that same as no policy)
                early_term = None
            else:
                if self.submit_logs:
                    early_term = {"policy_type": policy_name, "eval_interval": eval_interval, "delay_eval": delay_eval, 
                        "truncation_percentage": truncation_percentage, "slack_factor": slack_factor, "slack_amount": slack_amount}

                    self.serializable_trainer = {"estimator": serializable_estimator, "hd_dict": hd_dict, "search_type": search_type, "primary_metric": primary_metric, 
                        "maximize_metric": maximize_metric, "early_term": serializable_early_term, "max_total_runs": max_runs, "max_concurrent_runs": max_concurrent_runs, 
                        "max_minutes": max_minutes}

                if fake_submit:
                    trainer = self.serializable_trainer
                else:
                    early_term = self.make_early_term_policy(policy_type=policy_name, eval_interval=eval_interval, delay_eval=delay_eval, 
                        truncation_percentage=truncation_percentage, slack_factor=slack_factor, slack_amount=slack_amount)

                    trainer = self.create_hyperdrive_trainer(estimator, hd_dict, search_type, primary_metric, maximize_metric, early_term, 
                        max_total_runs=max_runs, max_concurrent_runs=max_concurrent_runs, max_minutes=max_minutes)
        else:
            # not using AML hyperdrive
            trainer = estimator

        run_name, monitor_cmd, aml_run_name, aml_run_number, aml_run_id = \
            self.run_aml_job(job_id, workspace, aml_ws_name, trainer, experiment, xt_exper_name, aml_exper_name, compute_target, code_dir, first_run_name, 
                box_name, node_index, repeat_count, fake_submit, args)

        if show_aml_run_name:
            fb.feedback("[aml: {}/Run {}], xt: {}/{} ".format(aml_exper_name, aml_run_number, workspace, run_name), is_final=True)
        else:
            fb.feedback("{}/{}".format(aml_exper_name, aml_run_number, workspace, run_name))

        mongo = self.store.get_mongo()
        run_names = []
        for run in node_runs:
            run_name = run["run_name"]
            run_names.append(run_name)

        node_info = {"ws": workspace}

        for run_name in run_names:
            # we only have 1 run, so OK to hold info in flat dict here
            node_info["aml_exper_name"] = aml_exper_name
            node_info["aml_run_number"] = aml_run_number
            node_info["aml_run_id"] = aml_run_id
            node_info["run_name"] = run_name

            # update mongo db info for run with cluster and service_job_id
            mongo.update_mongo_run_from_dict(workspace, run_name, {"aml_exper_name": aml_exper_name, "aml_run_number": aml_run_number})

        if monitor_cmd:
            console.print("monitoring notebook created; to run:")
            console.print("  " + monitor_cmd)

        return node_info

    def run_aml_job(self, job_id, workspace, aml_ws_name, trainer, experiment, xt_exper_name, aml_exper_name, compute_target, cwd, run_name, box_name, 
            node_index, repeat, fake_submit, args):
        monitor_cmd = None

        console.diag("before AML experiment.submit(trainer)")

        # SUBMIT the run and return an AML run object
        if fake_submit:
            aml_run = None 
            aml_run_id = "fake_aml_id"
            aml_run_number = 999
        else:
            aml_run = experiment.submit(trainer)
            aml_run_id = aml_run.id
            aml_run_number = aml_run.number

        # copy to submit-logs
        utils.copy_data_to_submit_logs(args, self.serializable_trainer, "aml_submit.json")

        console.diag("after AML experiment.submit(trainer)")

        config = self.config
        username = args["username"]
        description = args["description"]
        aggregate_dest = args["aggregate_dest"]
        jupyter_monitor = args["jupyter_monitor"]

        aml_run_name = aml_exper_name + ".{}".format(run_name)

        # set "xt_run_name" property for fast access to run in future
        if not fake_submit:
            aml_run.add_properties({"xt_run_name": aml_run_name})
            aml_run.set_tags({"xt_run_name": aml_run_name})

        # # partially log the start of the RUN
        # self.store.start_run_core(workspace, run_name, exper_name=xt_exper_name, description=description, username=username,
        #         box_name=box_name, app_name=None, repeat=repeat, is_parent=False, job_id=job_id, pool=compute_target, node_index=node_index,
        #         aggregate_dest=aggregate_dest, path=cwd, aml_run_id=aml_run_id)

        if jupyter_monitor:
            fn = self.make_monitor_notebook(aml_ws_name, aml_run_name)
            dir = os.path.dirname(fn)
            #console.print("jupyter notebook written to: " + fn)
            monitor_cmd = "jupyter notebook --notebook-dir=" + dir
        
        return run_name, monitor_cmd, aml_run_name, aml_run_number, aml_run_id

    def get_client_cs(self, service_node_info):
        '''
        Args:
            service_node_info: info that service maps to a compute node for a job
        Returns:
            {"ip": value, "port": value, "box_name": value}
        '''
        errors.general_error("support for talking to XT controller for AML jobs not yet supported")

    def mount(self, storage_name, storage_key, container):

        ws = Workspace(subscription_id, resource_group, ws_name)     # , auth=svc_pr)

        from azureml.core import Datastore
        datastore = Datastore.register_azure_blob_container(workspace=ws, 
            datastore_name=container, container_name=container,
            account_name=storage_name, account_key=storage_key,
            create_if_not_exists=True)

        console.print("datastore=", datastore)

        dataref = datastore.as_mount()
        dir_name = dataref.path_on_compute
        console.print("daatastore MOUNT dir_name=", dir_name)
        return dir_name

    # API call
    def read_log_file(self, service_node_info, log_name, start_offset=0, end_offset=None, 
        encoding='utf-8', use_best_log=True):

        run = self.get_node_run(service_node_info)

        # aml bug workaround
        run._output_logs_pattern = "azureml-logs/[\d]{2}.+\.txt"

        # this is the style of log output we want, but as a pull-model
        # stream log to console
        #run.wait_for_completion(show_output=True)

        new_text = None
        node_status = "queued"
        next_offset = None

        # refresh run details (status and logs)
        current_details = run.get_details() 
        aml_status = current_details["status"] 
        simple_status = self.get_simple_status(aml_status)

        if use_best_log:
            # list of currently available logs
            available_logs = run._get_logs(current_details)

            # get highest priority (most relevant to user) log name
            next_log = Run._get_last_log_primary_instance(available_logs) if available_logs else None

            if available_logs and log_name != next_log:
                # switching logs, so reset offset and remember new name
                start_offset = 0
                log_name = next_log

        if log_name:
            # reuse request for better perf (hopefully)
            url = current_details["logFiles"][log_name]

            if not self.request:
                self.request = urllib.request.Request(url)
            elif self.request.full_url != url:
                #self.request.close()
                self.request = urllib.request.Request(url)

            try:
                with urllib.request.urlopen(self.request) as response:
                    all_bytes = response.read()
            except:
                # treat any error as "log not yet available"
                all_bytes = b""

            if end_offset:
                new_bytes = all_bytes[start_offset:1+end_offset]
            else:
                new_bytes = all_bytes[start_offset:]

            next_offset = start_offset + len(new_bytes)
            new_text = new_bytes.decode(encoding)

        return {"new_text": new_text, "simple_status": simple_status, "log_name": log_name, "next_offset": next_offset, 
            "service_status": aml_status}

    # API call
    def get_simple_status(self, status):
        # translates an AML status to a simple status (queued, running, completed)

        queued = ["NotStarted", "Starting", "Provisioning", "Preparing", "Queued"]
        running = ["Running"]
        completed = ["Finalizing", "CancelRequested", "Completed", "Failed", "Canceled", "NotResponding"]

        if status in queued:
            ss = "queued"
        elif status in running:
            ss = "running"
        elif status in completed:
            ss = "completed"
        else:
            errors.internal_error("unexpected Auzre ML status value: {}".format(status))

        return ss

    def get_node_run(self, service_node_info):
        # create aml workspace
        aml_ws_name = utils.safe_value(self.compute_def, "service")
        ws = self.get_aml_ws(aml_ws_name)

        # create aml experiment
        aml_exper_name = service_node_info["aml_exper_name"]
        experiment = Experiment(ws, name=aml_exper_name)

        # create aml run
        aml_run_id = service_node_info["aml_run_id"]
        run = Run(experiment, aml_run_id)

        return run

    # API call
    def cancel_job(self, service_job_info, service_info_by_node):
        result_by_node = {}

        for node_id, node_info in service_info_by_node.items():
            result = self.cancel_node(node_info)
            if result is not None:
                result_by_node[node_id] = result

        return result_by_node

    # API call
    def cancel_node(self, service_node_info):
        result = None
        if "aml_run_id" in service_node_info:
            run = self.get_node_run(service_node_info)

            service_status = run.get_status()
            simple_status = self.get_simple_status(service_status)
            before_status = simple_status
            cancelled = False

            if simple_status != "completed":
                
                run.cancel()

                service_status = run.get_status()
                simple_status = self.get_simple_status(service_status)
                cancelled = (service_status == "completed")     

            result = {"cancelled": cancelled, "service_status": service_status, "simple_status": simple_status}

        return result
