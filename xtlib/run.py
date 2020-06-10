#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# run.py - simple API for ML apps to log info and get info related to current run
import os
import sys
import json
import arrow
import random
from collections import OrderedDict

# xtlib
from xtlib import utils
from xtlib import errors
from xtlib import constants
from xtlib import file_utils
from xtlib import impl_storage

from xtlib.storage.store import Store
from xtlib.console import console
from xtlib.helpers.xt_config import get_merged_config

FN_CHECKPOINT_FILE = "checkpoints/file.dat"
FN_CHECKPOINT_DICT = "checkpoints/dict_cp.json"
FN_CHECKPOINT_WILD = "checkpoints/*"

class Run():

    def __init__(self, config=None, store=None, xt_logging=True, aml_logging=True, checkpoints_enabled=True,
        tensorboard_path=None, supress_normal_output=False):
        ''' 
        this initializes an XT Run object so that ML apps can use XT services from within their app, including:
            - hyperparameter logging
            - metrics logging
            - uploading files to an XT share
            - downloading files from an XT share
            - checkpoint support
            - explict HP search calls

        note: Azure ML child runs seem to get their env variables inherited from their parent run 
        correctly, so we no need to use parent run for info. '''

        self.store = None
        self.xt_logging = False
        self.metric_report_count = 0
        self.metric_names = OrderedDict()
        self.supress_normal_output = supress_normal_output

        # tensorboard writers
        self.train_writer = None
        self.test_writer = None

        # 2nd set of writers for Philly
        self.train_writer2 = None
        self.test_writer2 = None

        self.tensorboard_path = tensorboard_path
        if self.tensorboard_path:
            # TENSORBOARD WORKAROUND: this code causes tensorboard files to be closed when they are appended to
            # this allow us to just write the files to MOUNTED output dir (and not have to mirror them)
            try:
                from tensorboard.compat import tf
                delattr(tf.io.gfile.LocalFileSystem, 'append')
            except:
                import tensorflow as tf
                import tensorboard as tb
                tf.io.gfile = tb.compat.tensorflow_stub.io.gfile
                delattr(tf.io.gfile.LocalFileSystem, 'append')

            self.init_tensorboard()

        self.ws_name = os.getenv("XT_WORKSPACE_NAME", None)
        self.exper_name = os.getenv("XT_EXPERIMENT_NAME", None)
        self.run_name = os.getenv("XT_RUN_NAME", None)
        self.resume_name = os.getenv("XT_RESUME_NAME")

        # load context, if present
        self.context = None

        if self.run_name:
            fn_context = os.path.abspath(constants.FN_RUN_CONTEXT)

            if os.path.exists(fn_context):
                json_context = file_utils.read_text_file(fn_context)

                context_dict = json.loads(json_context)
                self.context = utils.dict_to_object(context_dict)
                if not supress_normal_output:
                    console.print("run context loaded: {}".format(self.context.run_name))
            else:
                if not supress_normal_output:
                    console.print("run context file not found: {}".format(fn_context))

        mc = os.getenv("XT_MONGO_CONN_STR")
        self.mongo_conn_str = utils.base64_to_text(mc)

        # convert store_creds from string to dict
        sc = os.getenv("XT_STORE_CREDS")
        self.store_creds = utils.base64_to_text(sc)
        if self.store_creds:
            self.store_creds = json.loads(self.store_creds)

        provider_code_path = os.getenv("XT_STORE_CODE_PATH")

        run_cache_dir = None
        self.config = config

        if config:
            run_cache_dir = config.get("general", "run-cache-dir")

        is_aml_run = bool(os.getenv("AML_WORKSPACE_NAME"))
        
        if is_aml_run:
            # load azure libraries on demand
            from .backends.backend_aml import AzureML
            from azureml.core import Run as AmlRun

            self.aml_run = AmlRun.get_context()     # assumes app is running under AML
        else:
            self.aml_run = None

        self.aml_logging = aml_logging
        self.is_aml_child = False    
        self.is_aml = False   # TODO: remove need for this since we now treat AML runs normally

        if True:    # self.run_name:
            if not self.store_creds and not config:
                # if store_creds not set, this app is running outside of XT control
                # provide access to XT store for dev/test purposes
                config = get_merged_config(suppress_warning=True)
                
            self.config = config

            self.store = Store(self.store_creds, provider_code_path=provider_code_path, run_cache_dir=run_cache_dir, 
                mongo_conn_str=self.mongo_conn_str, config=config)

            # if not supress_normal_output:
            #     console.print("XT logging enabled: ", self.run_name)

        # distributed training support
        self.rank = None
        self.world_size = None
        self.master_ip = None
        self.master_port = None

        self.xt_logging = xt_logging and self.run_name !=  None
        self.checkpoints_enabled = checkpoints_enabled

        self.direct_run = not os.getenv("XT_CONTROLLER")

        if  self.xt_logging and self.direct_run and self.store:
            # log stuff normally done by controller at start of run
            self.store.log_run_event(self.ws_name, self.run_name, "started", {})   
            self.store.mongo.run_start(self.ws_name, self.run_name)
            if self.context:
                self.store.mongo.job_run_start(self.context.job_id)

    def init_tensorboard(self):
        # as of Oct-04-2019, to use torch.utils.tensorboard on DSVM systems, we need to do one of the following:
        #   - clear the env var PYTHONPATH (before running this app)
        #   - remove the caffe2/build path from sys.path
        path = "/opt/caffe2/build"
        if path in sys.path:
            sys.path.remove(path)
        from torch.utils.tensorboard import SummaryWriter

        # to use tensorboardX, it needs to be in our install requirements.txt
        #from tensorboardX import SummaryWriter

        # since tensorboard doesn't close their files between writes (just flushes), the
        # changes won't be pushed thru blobfuse mnt_output_dir, so write them to 
        # local_output_dir where we will use XT mirroring to push their changes to "mirroring" path 
        # in run's storage
        serial_num = random.randint(1,100000)
        log_dir = "{}/logs/{}".format(self.tensorboard_path, serial_num)

        # tensorboard: SummaryWriter will output to ./runs/ directory by default
        log_path = os.path.expanduser(log_dir)
        self.train_writer = SummaryWriter(log_path + "/train")
        self.test_writer = SummaryWriter(log_path + "/test")

        philly_path = os.getenv("PHILLY_JOB_DIRECTORY")
        if philly_path:
            self.train_writer2 = SummaryWriter(philly_path + "/train")
            self.test_writer2 = SummaryWriter(philly_path + "/test")

    def get_child_run(self, parent_run, child_run_number):
        target_run = None

        runs = parent_run.get_children()
        runs = [run for run in runs if run.number == child_run_number]
        child_run = runs[0] if len(runs) else None

        return child_run

    def close(self):
        if self.xt_logging and self.direct_run and self.store and self.context:
            context = self.context
            status = "completed"
            exit_code = 0
            rundir = "."
            node_id = utils.node_id(context.node_index)

            # wrap up the run (usually done by controller)
            self.store.wrapup_run(context.ws, self.run_name, context.aggregate_dest, context.dest_name, 
                status=status, exit_code=exit_code, primary_metric=context.primary_metric, 
                maximize_metric=context.maximize_metric, report_rollup=context.report_rollup, rundir=rundir, 
                after_files_list=context.after_files_list, after_omit_list=context.after_omit_list, log_events=context.log, 
                capture_files=context.after_upload, job_id=context.job_id, is_parent = True, node_id=node_id, 
                run_index=None)

        if self.train_writer:
            self.train_writer.close()
            self.test_writer.close()

        if self.train_writer2:
            self.train_writer2.close()
            self.test_writer2.close()

        if self.is_aml and self.store:
            # partially log the end of the run

            # TODO: how to do this partial log for killed/error runs?
            status = "completed"   
            exit_code = 0
            restarts = None
            hparams_dict = None
            metrics_rollup_dict = None
            end_time = utils.get_time()
            log_records = []

            self.store.end_run(self.ws_name, self.run_name, status, exit_code, hparams_dict, metrics_rollup_dict, end_time=None, 
                restarts=restarts, aggregate_dest=None, dest_name=None, is_aml=True)

            self.store.update_mongo_run_at_end(self.ws_name, self.run_name, status, exit_code, restarts, end_time, log_records, 
                hparams_dict, metrics_rollup_dict)

    def get_store(self):
        return self.store

    def log_hparam(self, name, value):
        if self.store and self.xt_logging:
            self.store.log_run_event(self.ws_name, self.run_name, "hparams", {name: value}, is_aml=self.is_aml)

        if self.is_aml and self.aml_logging:
            self.aml_run.log(name, value, description)

    def log_hparams(self, data_dict):
        #console.print("log_hparam, self.store=", self.store)

        if self.store and self.xt_logging:
            self.store.log_run_event(self.ws_name, self.run_name, "hparams", data_dict, is_aml=self.is_aml)

        if self.is_aml and self.aml_logging:
            self.aml_run.log_row("hparams", **data_dict)

    # for simplicity, only support log_metrics
    # def log_metric(self, name, value):
    #     if self.store and self.xt_logging:
    #         self.store.log_run_event(self.ws_name, self.run_name, "metrics", {name: value}, is_aml=self.is_aml)

    #     if self.is_aml and self.aml_logging:
    #         self.aml_run.log(name, value)

    def log_metrics(self, data_dict, step_name=None, stage=None):
        #console.print("log_metrics: self.store=", self.store, ", xt_logging=", self.xt_logging)

        dd = dict(data_dict)
        if step_name and step_name in dd:
           step_num = dd[step_name]
        else:
            self.metric_report_count += 1
            step_num = self.metric_report_count
            step_name = constants.INDEX
            dd[step_name] = step_num

        # add stage- in front of metric names
        if stage:
            orig_dd = dict(dd)
            dd = {}
            for name, value in orig_dd.items():
                if name == step_name:
                    dd[name] = value
                else:
                    dd[stage+"-"+name] = value

        # update ordered list of metric names
        metric_names_changed = False

        for name in dd.keys():
            if not name in self.metric_names:
                self.metric_names[name] = 1
                metric_names_changed = True

        # each metric set may have a unique step name so log it each time with metrics
        dd[constants.STEP_NAME] = step_name

        if self.store and self.xt_logging:
            #console.print("logging run_event for metrics...")
            self.store.log_run_event(self.ws_name, self.run_name, "metrics", dd, is_aml=self.is_aml)

            if metric_names_changed:
                ddx = {"metric_names": list(self.metric_names)}
                # if not self.supress_normal_output:
                #     console.print("updating metric_names: {}".format(ddx))

                self.store.mongo.update_mongo_run_from_dict(self.ws_name, self.run_name, ddx)

        if self.is_aml and self.aml_logging:
            for name, value in dd.items():
                self.aml_run.log(name, value)

        if stage is None or stage == "train":

            # log TRAIN metrics
            if self.train_writer:
                for name, value in data_dict.items():
                    if name != step_name:
                        self.train_writer.add_scalar(name, value, global_step=step_num)
                self.train_writer.flush()

            if self.train_writer2:
                for name, value in data_dict.items():
                    if name != step_name:
                        self.train_writer2.add_scalar(name, value, global_step=step_num)
                self.train_writer2.flush()

        elif stage in ["eval", "test"]:

            # log TEST metrics
            if self.test_writer:
                for name, value in data_dict.items():
                    if name != step_name:
                        self.test_writer.add_scalar(name, value, global_step=step_num)
                self.test_writer.flush()

            if self.test_writer2:
                for name, value in data_dict.items():
                    if name != step_name:
                        self.test_writer2.add_scalar(name, value, global_step=step_num)
                self.test_writer2.flush()

    def log_event(self, event_name, data_dict):
        if self.store and self.xt_logging:
            self.store.log_run_event(self.ws_name, self.run_name, event_name, data_dict, is_aml=self.is_aml)

    def is_resuming(self):
        # return a bool using not not
        return not not self.resume_name 

    def set_checkpoint(self, dict_cp, fn_cp=None):
        if self.store and self.checkpoints_enabled and not self.is_aml:
            if fn_cp:
                #console.print("uploading checkpoint file: ws={}, run={}, file={}".format(self.ws_name, self.run_name, FN_CHECKPOINT_FILE))
                self.store.upload_file_to_run(self.ws_name, self.run_name, FN_CHECKPOINT_FILE, fn_cp)
            text = json.dumps(dict_cp)
            #console.print("uploading checkpoint dict: ws={}, run={}, file={}".format(self.ws_name, self.run_name, FN_CHECKPOINT_DICT))
            self.store.create_run_file(self.ws_name, self.run_name, FN_CHECKPOINT_DICT, text)

            # also log the checkpoint
            self.store.log_run_event(self.ws_name, self.run_name, "set_checkpoint", dict_cp, is_aml=self.is_aml)
            return True
        return False

    def clear_checkpoint(self):
        if self.store and self.checkpoints_enabled and not self.is_aml:
            self.store.delete_run_files(self.ws_name, self.run_name, FN_CHECKPOINT_WILD)
            self.store.log_run_event(self.ws_name, self.run_name, "clear_checkpoint", dict_cp, is_aml=self.is_aml)
            return True
        return False

    def get_checkpoint(self, fn_cp_dest=None):
        dict_cp = None

        if self.store and self.is_resuming() and self.checkpoints_enabled and not self.is_aml:
            if self.store.does_run_file_exist(self.ws_name, self.resume_name, FN_CHECKPOINT_DICT):
                if fn_cp_dest:
                    #console.print("downloading checkpoint file: ws={}, run={}, file={}".format(self.ws_name, self.resume_name, FN_CHECKPOINT_FILE))
                    self.store.download_file_from_run(self.ws_name, self.resume_name, FN_CHECKPOINT_FILE, fn_cp_dest)
                #console.print("downloading checkpoint dict: ws={}, run={}, file={}".format(self.ws_name, self.resume_name, FN_CHECKPOINT_DICT))
                text = self.store.read_run_file(self.ws_name, self.resume_name, FN_CHECKPOINT_DICT)
                dict_cp = json.loads(text)
                # log that we retreived the checkpoint
                self.store.log_run_event(self.ws_name, self.run_name, "get_checkpoint", dict_cp, is_aml=self.is_aml)

        return dict_cp

    def upload_files_to_share(self, share, store_path, local_path, show_feedback):
        '''
        note: show_feedback not implemented; caller should call console.set_level() to control type of output
        emitted by XTLib API.
        '''
        storage = impl_storage.ImplStorage(self.config, self.store)

        count = storage.upload(local_path=local_path, store_path=store_path, share=share, feedback=show_feedback, 
            workspace=None, run=None, experiment=None, job=None)

        path = "store://{}/{}".format(utils.make_share_name(share), store_path)


        return {"count": count, "path": path}

    def download_files_from_share(self, share, store_path, local_path, show_feedback, snapshot=True):
        storage = impl_storage.ImplStorage(self.config, self.store)
        
        count = storage.download(local_path=local_path, store_path=store_path, share=share, 
            feedback=show_feedback, snapshot=snapshot, workspace=None, run=None, experiment=None, job=None)
            
        path = "store://{}/{}".format(utils.make_share_name(share), store_path)
        return {"count": count, "path": path}

    def get_next_hp_set_in_search(self, hp_space_dict, search_type=None, hparam_search=None):
        '''
        args:
            hp_space_dict: a dict of HP name/space_text pairs (space_text specifies search space for HP)
            search_type: type of search to perform (None will default to search_type specified for job)

        processing:
            1. extract the HP name and search spaces from hp_space_dict.  Valid space expressions:
                - single value (string, number)
                - list of values, e.g.: [.01, 02, .03]
                - $linspace() to generate specified # of discrete values: $linspace(.01, .98, 10)
                - hyperopt search space functions, e.g.: $randint() or $uniform(32, 256)

            2. call the HP search alrorithm identified by search_type

        return:
            the resulting HP set (dict) of name/value pairs, returned by the search algorithm
        '''

        from xtlib.hparams.hparam_search import HParamSearch
        
        if not search_type:
            search_type = self.context.search_type

        if not hparam_search:
            hparam_search = HParamSearch()
            
        space_records = hparam_search.parse_hp_config_yaml(hp_space_dict, search_type)

        hp_dict = hparam_search.hp_search_core(self.context, search_type, self.store, run_name=self.run_name, space_records=space_records)
        return hp_dict

    def tag_run(self, tag_dict):
        if not self.run_name:
            errors.api_error("tag_run requires app to be run under XT")

        # convert tag dict to tag list
        tag_list = []
        for key, value in tag_dict.items():
            if value is None:
                tag_list.append(key)
            else:
                tag_list.append("{}={}".format(key, value))

        storage = impl_storage.ImplStorage(self.config, self.store)
        storage.set_tags([self.run_name], tag_list, self.ws_name)

    def tag_job(self, tag_dict):
        if not self.context:
            errors.api_error("tag_job requires app to be run under XT")

        # convert tag dict to tag list
        tag_list = []
        for key, value in tag_dict.items():
            if value is None:
                tag_list.append(key)
            else:
                tag_list.append("{}={}".format(key, value))

        storage = impl_storage.ImplStorage(self.config, self.store)
        storage.set_tags([self.context.job_id], tag_list, self.ws_name)
