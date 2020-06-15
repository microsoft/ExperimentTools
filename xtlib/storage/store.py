#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# store.py - implements the STORE API of Experiment Tools
import numpy as np
import os
import sys
import time
import json
import uuid
import shutil
import socket 
import logging

from xtlib import utils
from xtlib import errors
from xtlib import pc_utils
from xtlib.storage import mongo_db
from xtlib import constants
from xtlib import file_utils

from xtlib.console import console
from xtlib.helpers.bag import Bag
from xtlib.helpers.part_scanner import PartScanner
from xtlib.constants import RUN_STDOUT, RUN_STDERR
from xtlib.helpers.stream_capture import StreamCapture
from xtlib.constants import WORKSPACE_DIR, WORKSPACE_LOG, RUN_LOG

from .store_objects import StoreBlobObjs

# access to AML
#from azureml.core import Workspace
#from azureml.core import Experiment

logger = logging.getLogger(__name__)

# public function
def store_from_context(context):
    store = Store(context.store_creds, provider_code_path=context.store_code_path, mongo_conn_str=context.mongo_conn_str)
    return store

# main class that implements the XT STORE API
class Store():
    '''This class provides access to the XT Store, which is based on a storage provider.
    Methods are provided to manage workspaces, experiments, runs, and related files.

    You can create an instance of XTStore by providing any of these:
        - a XTConfig instance (holds information from the XT configuration file)
        - the storage credentials dictionary containing the key, name, etc., as required by the provider

    :param storage_creds: storage credentials dict (specific to the current storage provider)
    :param config: an instance of the XTConfig class.
    :param max_retries: the number of times to return an Azure error before failing the associated call.
    :param mongo_conn_str: a MongoDB connection string.
    :param provider_code_path: a string containing a python module.class reference to the provider code

    :Example:

        >>> from store import Store
        >>> store = Store(config=my_config)
        >>> run_names = store.get_run_names("ws1")

    '''
    
    def __init__(self, storage_creds=None, config=None, max_retries=10, run_cache_dir=None, feedback_enabled=True,  mongo_conn_str=None, 
        provider_code_path=None, validate_creds=False):
        '''This is the constructor for the Store class. '''

        self.feedback_enabled = feedback_enabled

        if not mongo_conn_str and config:
            mongo_creds, mongo_name = config.get_mongo_creds()
            mongo_conn_str = mongo_creds["mongo-connection-string"]

        if config:
            if not storage_creds:
                storage_creds = config.get_storage_creds()

            if not provider_code_path:
                provider_code_path = config.get_storage_provider_code_path(storage_creds)

        self.helper = StoreBlobObjs(storage_creds, provider_code_path=provider_code_path, 
            max_retries=max_retries)

        # validate basic credentials
        if validate_creds:
            try:
                self.does_workspace_exist("test")
            except BaseException as ex:
                logger.exception("Error store.__init__, tried to test storage credentials, ex={}".format(ex))

                errors.service_error("Azure Storage service credentials not set correctly" + 
                    "; use 'xt config' to correct")

        self.mongo = mongo_db.MongoDB(mongo_conn_str, run_cache_dir) if mongo_conn_str else None
        self.mongo_conn_str = mongo_conn_str
        self.run_cache_dir = run_cache_dir
        self.provider_code_path = provider_code_path
        self.storage_creds = storage_creds

        self.store_type = storage_creds["provider"]

        self.cap_stdout = None
        self.cap_stderr = None

        self.helper.validate_storage_and_mongo(self.mongo)

    def get_name(self):
        return self.helper.get_name()
        
    def get_mongo(self):
        return self.mongo

    def get_props_dict(self):
        pd = {"storage_creds": self.storage_creds, "mongo_conn_str": self.mongo_conn_str, 
            "run_cache_dir": self.run_cache_dir, "provider_code_path": self.provider_code_path}
        return pd

    @staticmethod
    def create_from_props_dict(pd):
        return Store(**pd) 

    def _error(self, msg):
        raise Exception("Error - {}".format(msg))

    # ---- SHARES ----

    def _ensure_share_exists(self, share_name, flag_as_error=True):
        return self.helper.ensure_workspace_exists(share_name, flag_as_error)

    def does_share_exist(self, share_name):
        ''' returns True if the specified share exists in the Store; False otherwise.
        '''
        return self.helper.does_share_exist(share_name)

    def create_share(self, share_name, description=None):
        ''' create a new share using the specified name.
        '''
        self.helper.create_share(share_name, description)

    def delete_share(self, share_name):
        ''' delete the specified share, and all of the blobs stored within it
        '''
        result = self.helper.delete_share(share_name)
        if result:
            # remove associated summary cache
            self.mongo.remove_cache(share_name)

        return result
    
    def get_share_names(self):
        ''' return the names of all shares that are currently defined in the XT Store.
        '''
        return self.helper.get_share_names()

    # ---- WORKSPACE ----

    def ensure_workspace_exists(self, ws_name, flag_as_error=True):
        return self.helper.ensure_workspace_exists(ws_name, flag_as_error)

    def get_running_workspace(self):
        ''' returns the name of the workspace associated with the current XT run.
        '''
        return os.getenv("XT_WORKSPACE_NAME", None)

    def does_workspace_exist(self, ws_name):
        ''' returns True if the specified workspace exists in the Store; False otherwise.
        '''
        return self.helper.does_workspace_exist(ws_name)

    def create_workspace(self, ws_name, description=None):
        ''' create a new workspace using the specified name.
        '''
        self.helper.create_workspace(ws_name, description)

        # log some information
        self.log_workspace_event(ws_name, "created", {"description": description})

    def delete_workspace(self, ws_name):
        ''' delete the specified workspace, and all of the runs stored within it.
        '''
        job_names = self.mongo.get_job_names({"ws_name": ws_name})

        result = self.helper.delete_workspace(ws_name)
        if result:
            console.print("  workspace/run storage deleted")

            # remove mongo workspace
            self.mongo.remove_workspace(ws_name)
            console.print("  workspace/run mongo deleted")

            # remove each job on store/mongo
            for job_id in job_names:
                self.helper.delete_job(job_id)
                self.mongo.delete_job(job_id)
                console.print("  {} deleted".format(job_id))

        return result

    def log_workspace_event(self, ws_name, event_name, data_dict):
        ''' log the specifed event_name and key/value pairs in the data_dict to the workspace log file.
        '''
        record_dict = {"time": utils.get_time(), "event": event_name, "data": data_dict}
        rd_text = json.dumps(record_dict)

        # append to workspace log file
        self.append_workspace_file(ws_name, WORKSPACE_LOG, rd_text + "\n")

    def get_workspace_names(self):
        ''' return the names of all workspaces that are currently defined in the XT Store.
        '''
        return self.helper.get_workspace_names()

    def is_legal_workspace_name(self, name):
        ''' return True if 'name' is a legal workspace name for the current XT Store.
        '''
        return self.helper.is_legal_workspace_name(name)

    # ---- WORKSPACE FILES ----

    def create_workspace_file(self, ws_name, ws_fn, text):
        ''' create a workspace file 'ws_fn" containing 'text', within the workspace 'ws_name'.
        '''
        #return self.helper.create_workspace_file(ws_name, ws_fn, text)
        wf = self.workspace_files(ws_name, use_blobs=True)
        return wf.create_file(ws_fn, text)

    def append_workspace_file(self, ws_name, ws_fn, text):
        ''' append the 'text' to the 'ws_fn' workspace file, within the workspace 'ws_name'.
        '''
        #return self.helper.append_workspace_file(ws_name, ws_fn, text)
        wf = self.workspace_files(ws_name, use_blobs=True)
        return wf.append_file(ws_fn, text)

    def read_workspace_file(self, ws_name, ws_fn):
        ''' return the text contents of the specified workspace file.'
        '''
        #return self.helper.read_workspace_file(ws_name, ws_fn)
        wf = self.workspace_files(ws_name, use_blobs=True)
        return wf.read_file(ws_fn)

    def upload_file_to_workspace(self, ws_name, ws_fn, source_fn):
        ''' upload the file 'source_fn' from the local machine to the workspace 'ws_name' as file 'ws_fn'.
        '''
        #return self.helper.upload_file_to_workspace(ws_name, ws_fn, source_fn)
        wf = self.workspace_files(ws_name, use_blobs=True)
        return wf.upload_file(wf_fn, source_n)

    def upload_files_to_workspace(self, ws_name, ws_folder, source_wildcard):
        ''' upload the local files matching 'source_wildcard' to the workspace folder 'ws_folder' within the workspace 'ws_name'.
        '''
        #return self.helper.upload_files_to_workspace(ws_name, ws_folder, source_wildcard)
        wf = self.workspace_files(ws_name, use_blobs=True)
        return wf.upload_files(ws_folder, source_wildcard)

    def download_file_from_workspace(self, ws_name, ws_fn, dest_fn):
        ''' download the file 'ws_fn' from the workspace 'ws_name' as local file 'ws_fn'.
        '''
        #dest_fn = os.path.abspath(dest_fn)      # ensure it has a directory specified
        #return self.helper.download_file_from_workspace(ws_name, ws_fn, dest_fn)
        wf = self.workspace_files(ws_name, use_blobs=True)
        return wf.download_file(ws_fn, dest_fn)

    def download_files_from_workspace(self, ws_name, ws_wildcard, dest_folder):
        ''' download the workspace files matching 'ws_wildcard' to the local folder 'dest_folder'.
        '''
        #return self.helper.download_files_from_workspace(ws_name, ws_wildcard, dest_folder)
        wf = self.workspace_files(ws_name, use_blobs=True)
        return wf.download_files(ws_wildcard, dest_folder)

    def get_workspace_filenames(self, ws_name, ws_wildcard=None):
        ''' return the name of all workspace files matching 'ws_wildcard' in the workspace 'ws_name'.
        '''
        #return self.helper.get_workspace_filenames(ws_name, ws_wildcard)    
        wf = self.workspace_files(ws_name, use_blobs=True)
        return wf.get_filenames(ws_wildcard)
        
    def delete_workspace_file(self, ws_name, filename):
        ''' return the workspace files 'filename' from the workspace 'ws_name'.
        '''
        wf = self.workspace_files(ws_name, use_blobs=True)
        return wf.delete_file(filename)

    def does_workspace_file_exist(self, ws_name, ws_fn):
        ''' return True if the specified workspace file exists in the workspace 'ws_name'.
        '''
        #return self.helper.does_workspace_file_exist(ws_name, ws_fn)
        wf = self.workspace_files(ws_name, use_blobs=True)
        return wf.does_file_exist(ws_fn)

    def get_job_workspace(self, job_id):
        return self.mongo.get_job_workspace(job_id)

    # ---- EXPERIMENT ----

    def does_experiment_exist(self, ws_name, exper_name):
        return self.helper.does_experiment_exist(ws_name, exper_name)

    def create_experiment(self, ws_name, exper_name):
        if self.does_experiment_exist(ws_name, exper_name):
            raise Exception("experiment already exists: workspace={}, experiment={}".format(ws_name, exper_name))
        return self.helper.create_experiment(ws_name, exper_name)

    def get_running_experiment(self):
        return os.getenv("XT_EXPERIMENT_NAME", None)

    def get_experiment_names(self, ws_name):
        ''' get list of all unique logged "exper_name" in the workspace. '''

        use_runs = False    # using runs is slower, but reads older experiment names (experiment names added to jobs 11/21/2019)
        if use_runs:
            fields_dict = {"exper_name": 1}
            items = self.get_all_runs(None, ws_name, None, None, fields_dict, use_cache=False)
            
            # convert dicts to run_names
            items = [item["exper_name"] for item in items]

            # needed as of 11/21/2019 (TEMP - handle bad records where xt bug caused exper_name to be logged as dict instead of str)
            items = [rec for rec in items if isinstance(rec, str) ]

            items = list(set(items))
        else:
            items = self.mongo.get_all_experiments_in_ws(ws_name)

        return items

    def get_run_names(self, ws_name):
        ''' get a flat list of all run_names in the workspace. '''
        return self.helper.get_run_names(ws_name)

    # def append_experiment_run_name(self, ws_name, exper_name, run_name):
    #     self.helper.append_experiment_run_name( ws_name, exper_name, run_name)

    def get_experiment_run_names(self, ws_name, exper_name):
        return self.helper.get_experiment_run_names(ws_name, exper_name)

    # ---- EXPERIMENT FILES ----

    def create_experiment_file(self, ws_name, exper_name, exper_fn, text):
        ''' create an experiment file 'exper_fn" containing 'text'.
        '''
        ef = self.experiment_files(ws_name, exper_name, use_blobs=True)
        return ef.create_file(exper_fn, text)

    def append_experiment_file(self, ws_name, exper_name, exper_fn, text):
        ''' append 'text' to the experiment file 'exper_name'.
        '''
        ef = self.experiment_files(ws_name, exper_name, use_blobs=True)
        return ef.append_file(exper_fn, text)

    def read_experiment_file(self, ws_name, exper_name, exper_fn):
        ''' return the text contents of the experiment file 'exper_name'.
        '''
        #return self.helper.read_experiment_file(ws_name, exper_name, exper_fn)
        ef = self.experiment_files(ws_name, exper_name, use_blobs=True)
        return ef.read_file(exper_fn)

    def upload_file_to_experiment(self, ws_name, exper_name, exper_fn, source_fn):
        ''' upload the local file 'source_fn' as the experiment file 'exper_fn'.
        '''
        # return self.helper.upload_file_to_experiment(ws_name, exper_name, exper_fn, source_fn)
        ef = self.experiment_files(ws_name, exper_name, use_blobs=True)
        return ef.upload_file(exper_fn, source_fn)

    def upload_files_to_experiment(self, ws_name, exper_name, exper_folder, source_wildcard):
        ''' upload the local files specified by 'source_wildcard' to the experiment file folder 'exper_folder'.
        '''
        #return self.helper.upload_files_to_experiment(ws_name, exper_name, exper_folder, source_wildcard)
        ef = self.experiment_files(ws_name, exper_name, use_blobs=True)
        return ef.upload_files(exper_folder, source_wildcard)

    def download_file_from_experiment(self, ws_name, exper_name, exper_fn, dest_fn):
        ''' download file file 'exper_fn' to the local file 'dest_fn'.
        '''
        dest_fn = os.path.abspath(dest_fn)      # ensure it has a directory specified
        #return self.helper.download_file_from_experiment(ws_name, exper_name, exper_fn, dest_fn)
        ef = self.experiment_files(ws_name, exper_name, use_blobs=True)
        return ef.download_file(exper_fn, dest_fn)

    def download_files_from_experiment(self, ws_name, exper_name, exper_wildcard, dest_folder):
        ''' download the experiment files matching 'ws_wildcard' to the  folder 'dest_folder'.
        '''
        ef = self.experiment_files(ws_name, exper_name, use_blobs=True)
        return ef.download_files(ws_wildcard, dest_folder)

    def get_experiment_filenames(self, ws_name, exper_name, exper_wildcard=None):
        ''' return the name of all experiment files matching 'exper_wildcard'.
        '''
        ef = self.experiment_files(ws_name, exper_name, use_blobs=True)
        return ef.get_filenames(exper_wildcard)
        
    def delete_experiment_file(self, ws_name, exper_name, filename):
        ''' delete the experiment file 'filename'.
        '''
        ef = self.experiment_files(ws_name, exper_name, use_blobs=True)
        return wf.delete_file(filename)

    def does_experiment_file_exist(self, ws_name, exper_name, exper_fn):
        ''' return True if the experiment file 'exper_fn' exists.
        '''
        #return self.helper.does_experiment_file_exist(ws_name, exper_name, exper_fn)
        ef = self.experiment_files(ws_name, exper_name, use_blobs=True)
        return ef.does_file_exist(exper_fn)
    
    # ---- RUN ----

    def get_running_run(self):
        return os.getenv("XT_RUN_NAME", None)

    def does_run_exist(self, ws_name, run_name):
        return self.helper.does_run_exist(ws_name, run_name)

    def get_job_id_of_run(self, ws_name, run_name):
        job_id = self.mongo.get_run_property(ws_name, run_name, "job_id")
        return job_id

    def _create_next_run_directory(self, ws_name, is_parent):

        # is this a legacy workspace?
        default_next = self.helper.get_legacy_next_run_id(ws_name)
        if not default_next:
            default_next = 1

        run_id = self.mongo.get_next_run_id(ws_name, default_next=default_next)
        run_name = "run{}".format(run_id)

        # ensure we are not somehow overwriting an existing run
        exists = self.does_run_exist(ws_name, run_name)
        assert not exists

        return self.helper.create_next_run_by_name(ws_name, run_name)

    def _create_next_child_directory(self, ws_name, parent_name, child_name):

        if not child_name:
            child_id = self.mongo.get_next_child_id(ws_name, parent_name, default_next=1)
            console.print("mongo returned child_id=" + str(child_id))

            child_name = "{}.{}".format(parent_name, child_id)
            console.print("child_run_name=" + str(child_name))

        return self.helper.create_next_run_by_name(ws_name, child_name)

    def gather_run_hyperparams(self, log_records):
        # get metric name/value to report
        cmd_records = [r for r in log_records if r["event"] == "cmd"]
        hp_records = [r for r in log_records if r["event"] == "hparams"]

        hparams = {}

        if len(cmd_records):
            # get last cmd record (app may have updated cmd line hp's)
            cr = cmd_records[-1]

        # now, allow app to overwrite/supplement with HP records
        for hp in hp_records:
            #console.print("hp=", hp)
            if "data" in hp:
                dd = hp["data"]
                for name, value in dd.items():
                    #console.print("found hp: ", name, ", value=", value)
                    # for hparams, we keep original str of value specified
                    hparams[name] = value

        #console.print("returning hparams=", hparams)
        return hparams

    def get_run_num(self, run_name):
        base = run_name[3:]

        if "." in base:
            parent, child = base.split(".")
            # allow for 1 million 
            run_num = 1000*1000*int(parent) + int(child)
        else:
            run_num = 1000*1000*int(base)

        return run_num

    def start_child_run(self, ws_name, parent_run_name, exper_name=None, cmd_line_args=None, all_args=None, description=None, 
            from_ip=None, from_host=None, app_name=None, repeat=None, box_name="local", job_id=None, pool=None, 
            node_index=None, username=None, aggregate_dest=None, path=None, is_aml=False, child_name=None, compute=None, 
            service_type=None, search_type=None, sku=None, search_style=None, run_index=None):
        '''
        This is usually called from the XT COMPUTE box, so we CANNOT get from_ip and from_computer_name from the local machine.
        '''

        if is_aml:
            # child_num = self.mongo.get_next_child_id(ws_name, parent_run_name)
            # child_name = parent_run_name + "_" + str(child_num)
            child_name = aml_child_name
        else:
            child_name = self._create_next_child_directory(ws_name, parent_run_name, child_name=child_name)

        # we are called from controller, so our box_name is the name of this machine
        hostname = pc_utils.get_hostname()

        # always log the true name of the box (since there can be multiple clients which would otherwise produce multiple "local"s)
        if box_name == "local":
            box_name = hostname

        # for cases where workspaces are deleted, renamed, etc, this gives a truely unique id for the run
        run_guid = str(uuid.uuid4())

        run_num = self.get_run_num(child_name)
        script = os.path.basename(path) if path else None
        create_time = utils.get_time()

        build_parts = constants.BUILD.split(",")
        xt_version = build_parts[0].split(":")[1].strip()
        xt_build = build_parts[1].split(":")[1].strip()

        dd = {"ws": ws_name, "run_name": child_name, "run_num": run_num, "run_guid": run_guid, "description": description, "exper_name": exper_name, 
            "job_id": job_id, "node_index": node_index, "is_outer": False, "is_parent": False, "is_child": True,
            "from_ip": from_ip, "from_computer_name": from_host, "username": username, 
            "box_name": box_name, "app_name": app_name, "repeat": None, "path": path, "script": script, "create_time": create_time,
            "compute": compute, "service_type": service_type, "sku": sku, "search_style": search_style,
            "search_type": search_type,  "xt_build": xt_build, "xt_version": xt_version, "run_index": run_index}

        self.mongo.create_mongo_run(dd)

        # log "created" event for child run
        self.log_run_event(ws_name, child_name, "created", dd, is_aml=is_aml)

        # append "start" record to workspace summary log
        dd["time"] = utils.get_time()
        dd["event"] = "created"
        text = json.dumps(dd) + "\n"    

        if not is_aml:
            # append to summary file in run dir
            self.append_run_file(ws_name, child_name, constants.RUN_SUMMARY_LOG, text)

        if cmd_line_args:
            self.log_run_event(ws_name, child_name, "cmd_line_args", {"data": cmd_line_args}, is_aml=is_aml)  
        if all_args:
            self.log_run_event(ws_name, child_name, "all_args", {"data": all_args}, is_aml=is_aml)
    
        # finally, add a "child_created" record to the parent
        self.log_run_event(ws_name, parent_run_name, "child_created", {"child_name": child_name}, is_aml=is_aml)
        
        return child_name

    def start_run(self, ws_name, exper_name=None, description=None, username=None,
            box_name=None, app_name=None, repeat=None, is_parent=False, job_id=None, pool=None, node_index=None,
            aggregate_dest="none", path=None, compute=None, service_type=None, search_type=None, sku=None,
            search_style=None):
        '''
        This is usually called from the XT client machine (where user is running XT), so we can get from_ip and
        from_computer_name from the local machine.
        '''

        console.diag("start_run: start")

        # helper uses a lock to ensure atomic operation here 
        run_name = self._create_next_run_directory(ws_name, is_parent)

        return self.start_run_core(ws_name, run_name=run_name, exper_name=exper_name, description=description, username=username,
            box_name=box_name, app_name=app_name, repeat=repeat, is_parent=is_parent, job_id=job_id, 
            node_index=node_index, aggregate_dest=aggregate_dest, path=path, compute=compute, service_type=service_type, 
            search_type=search_type, sku=sku, search_style=search_style)

    def start_run_core(self, ws_name, run_name, exper_name=None, description=None, username=None,
            box_name=None, app_name=None, repeat=None, is_parent=False, job_id=None, pool=None, node_index=None,
            aggregate_dest="none", path=None, aml_run_id=None, compute=None, service_type=None, search_type=None,
            sku=None, search_style=None):

        console.diag("start_run: after create_next_run_directory")

        # log "created" event for run
        ip = pc_utils.get_ip_address()
        hostname = pc_utils.get_hostname()
        is_aml = (aml_run_id is not None)

        # always log the true name of the box (since there can be multiple clients which would otherwise produce multiple "local"s)
        if box_name == "local":
            box_name = hostname

        if exper_name and not is_aml:
            # create the experiement, if it doesn't already exist
            if not self.does_experiment_exist(ws_name, exper_name):
                self.create_experiment(ws_name, exper_name)

        # for cases where workspaces are deleted, renamed, etc, this gives a truely unique id for the run
        run_guid = str(uuid.uuid4())
        run_num = self.get_run_num(run_name)
        script = os.path.basename(path) if path else None
        create_time = utils.get_time()

        build_parts = constants.BUILD.split(",")
        xt_version = build_parts[0].split(":")[1].strip()
        xt_build = build_parts[1].split(":")[1].strip()

        dd = {"ws": ws_name, "run_name": run_name, "run_num": run_num, "run_guid": run_guid, "description": description, "exper_name": exper_name, 
            "job_id": job_id, "node_index": node_index, "is_outer": True, "is_parent": is_parent, "is_child": False, 
            "from_ip": ip, "from_computer_name": hostname, "username": username, 
            "box_name": box_name, "app_name": app_name, "repeat": repeat, "path": path, "script": script, "create_time": create_time,
            "node": node_index, "compute": compute, "service_type": service_type, "search_type": search_type, "sku": sku,
            "xt_build": xt_build, "xt_version": xt_version, "search_style": search_style, "run_index": None}

        if aml_run_id:
            dd["aml_run_id"] = aml_run_id

        self.mongo.create_mongo_run(dd)

        self.log_run_event(ws_name, run_name, "created", dd, is_aml=is_aml)

        console.diag("start_run: after log_run_event")

        # append "start" record to workspace summary log
        dd["time"] = utils.get_time()
        dd["event"] = "created"
        text = json.dumps(dd) + "\n"

        # append to summary file in run dir
        if not is_aml:
            self.append_run_file(ws_name, run_name, constants.RUN_SUMMARY_LOG, text)

        console.diag("start_run: after append_workspace_file")

        return run_name

    def get_ws_run_names(self, ws_name, filter_dict=None):
        fields_dict = {"_id": 1}
        items = self.get_all_runs(None, ws_name, None, filter_dict, fields_dict, use_cache=False)
        
        # convert dicts to run_names
        items = [item["_id"] for item in items]
        return items

    def end_run(self, ws_name, run_name, status, exit_code, hparams_dict, metrics_rollup_dict, end_time=None, 
        restarts=0, aggregate_dest=None, dest_name=None, is_aml=False):
        if not end_time:
            end_time = utils.get_time()

        self.log_run_event(ws_name, run_name, "ended", {"status": status, "exit_code": exit_code, \
            "metrics_rollup": metrics_rollup_dict}, event_time=end_time, is_aml=is_aml)

        if not is_aml:
            # append "end" record to workspace summary log
            end_record = {"ws_name": ws_name, "run_name": run_name, "time": end_time, "event": "end", 
                "status": status, "exit_code": exit_code, "hparams": hparams_dict, "metrics": metrics_rollup_dict, 
                "restarts": restarts}

            text = json.dumps(end_record) + "\n"

            # append to summary file in run dir
            self.append_run_file(ws_name, run_name, constants.RUN_SUMMARY_LOG, text)

    def delete_run(self, ws_name, run_name):
        return self.helper.delete_run(ws_name, run_name)

    def nest_run_records(self, ws_name, run_name):
        ''' return a single record that includes the all of the run_log in the data dictionary '''
        records = self.get_run_log(ws_name, run_name)    
        last_end_time = records[-1]["time"]

        log_record = {"run_name": run_name, "log": records}
        text = json.dumps(log_record) + "\n"
        #console.print("\ntext=", text)
        return text, last_end_time

    def rollup_and_end_run(self, ws_name, run_name, aggregate_dest, dest_name, status, exit_code, primary_metric, maximize_metric, 
        report_rollup, use_last_end_time=False, is_aml=False):

        #console.print("rollup_and_end_run: is_aml=", is_aml)

        if use_last_end_time:
            end_time = last_end_time
        else:
            end_time = utils.get_time()

        if is_aml:
            log_records = []
            hparams = {}
            metrics = {}
            restarts = 0
        else:
            # write run to ALLRUNS file
            if aggregate_dest and aggregate_dest != "none":
                # convert entire run log to a single nested record
                text, last_end_time = self.nest_run_records(ws_name, run_name)

                # append nested record to the specified all_runs file
                if dest_name:
                    if aggregate_dest == "experiment":
                        self.append_experiment_file(ws_name, dest_name, constants.ALL_RUNS_FN, text)
                    elif aggregate_dest == "job":
                        self.append_job_file(dest_name, constants.ALL_RUNS_FN, text)

            # LOG END RUN
            log_records = self.get_run_log(ws_name, run_name)
        
            hparams = self._roll_up_hparams(log_records) 
            metrics = self.rollup_metrics_from_records(log_records, primary_metric, maximize_metric, report_rollup) 
            restarts = len([rr["event"] for rr in log_records if rr["event"] == "restarted"])

        self.end_run(ws_name, run_name, status, exit_code, hparams, metrics, restarts=restarts, 
            end_time=end_time, aggregate_dest=aggregate_dest, dest_name=dest_name, is_aml=is_aml)

        self.mongo.update_mongo_run_at_end(ws_name, run_name, status, exit_code, restarts, end_time, log_records, hparams, metrics)

    def _roll_up_hparams(self, log_records):
        hparams_dict = {}

        for record in log_records:
            if record["event"] == "hparams":
                dd = record["data"]
                for key,value in dd.items():
                    hparams_dict[key] = value
                    
        return hparams_dict

    def rollup_metrics_from_records(self, log_records, primary_metric, maximize_metric, report_rollup):

        # this causes confusion when applied here; keep it OFF for now
        report_rollup = False

        metrics_records = [record for record in log_records if record["event"] == "metrics"]

        # collect valid records and values for primary_metric
        records = []
        values = []
        last_record = None

        for mr in metrics_records:
            if "data" in mr:
                dd = mr["data"]
                last_record = dd

                if primary_metric in dd:
                    value = dd[primary_metric]
                    if value:

                        try:
                            # ---- some strings may be invalid ints/floats - just ignore them for now
                            if isinstance(value, str):
                                #console.print("string found: key=", key, ", value=", value)  # , ", ex=", ex)
                                if "." in value or value == 'nan':
                                    value = float(value)
                                else:
                                    value = int(value)

                        except BaseException as ex:
                            logger.exception("Error in rollup_metrics_from_records, ex={}".format(ex))
                            #console.print("exception found: key=", key, ", value=", value, ", ex=", ex)

                        #console.print("rollup gather: key={}, value={}".format(key, value))
                        values.append(value)
                        records.append(dd)

        # find rollup-record
        if records:
            index = -1

            if report_rollup:
                try:
                    if maximize_metric:
                        index = np.argmax(values)
                    else:
                        index = np.argmin(values)
                except:
                    # when above fails, just use 'last' 
                    pass

            rollup_record = records[index]
        else:
            rollup_record = last_record        
    
        return rollup_record

    def copy_run(self, ws_name, run_name, ws_name2, run_name2):
        return self.helper.copy_run(ws_name, run_name, ws_name2, run_name2)

    def get_run_log(self, ws_name, run_name):
        return self.helper.get_run_log(ws_name, run_name)

    def log_run_event(self, ws_name, run_name, event_name, data_dict=None, event_time=None, is_aml=False):
        #console.print("log_run_event: ws_name={}, run_name={}, event_name={}".format(ws_name, run_name, event_name))

        if not event_time:
            event_time = utils.get_time()

        if data_dict and not isinstance(data_dict, dict):   
            raise Exception("data_dict argument is not a dict: " + str(data_dict))
        record_dict = {"time": event_time, "event": event_name, "data": data_dict}
        #console.print("record_dict=", record_dict)

        if not is_aml:
            rd_text = json.dumps(record_dict)
            # append to run log file
            self.append_run_file(ws_name, run_name, RUN_LOG, rd_text + "\n")

        # log all backend types to mongo
        self.mongo.add_run_event(ws_name, run_name, record_dict)

    def get_job_names(self, filter_dict=None, fields_dict=None):
        return self.mongo.get_job_names(filter_dict, fields_dict)

    def get_ws_runs(self, ws_name, filter_dict=None, include_log_records=False, first_count=None, last_count=None, sort_dict=None):
        return self.mongo.get_ws_runs(ws_name, filter_dict, include_log_records, first_count, last_count, sort_dict)

    def get_all_runs(self, aggregator_dest, ws_name, job_or_exper_name, filter_dict=None, fields_dict=None, use_cache=False, 
        fn_cache=None, first_count=None, last_count=None, sort_dict=None):

        return self.mongo.get_all_runs(aggregator_dest, ws_name, job_or_exper_name, filter_dict, fields_dict, use_cache,
            fn_cache, first_count, last_count, sort_dict)

    def wrapup_run(self, ws_name, run_name, aggregate_dest, dest_name, status, exit_code, primary_metric, maximize_metric, 
        report_rollup, rundir, after_files_list, log_events=True, capture_files=True, job_id=None, is_parent=False, 
        after_omit_list=None, node_id=None, run_index=None):

        #console.print("wrapup_run: rundir=", rundir, ", exit_code=", exit_code)

        if log_events:  
            # LOG "ENDED" to run_log, APPEND TO ALLRUNS
            self.rollup_and_end_run(ws_name, run_name, aggregate_dest, dest_name, status, exit_code, 
                primary_metric=primary_metric, maximize_metric=maximize_metric, report_rollup=report_rollup)

        if rundir and capture_files:
            # CAPTURE OUTPUT FILES
            started = time.time()
            copied_files = []

            for output_files in after_files_list:
                
                from_path = os.path.dirname(output_files)
                to_path = "after/" + os.path.basename(from_path) if from_path else "after" 
                output_files = os.path.abspath(file_utils.path_join(rundir, output_files))
                console.print("\nprocessing AFTER: ws_name=", ws_name, ", run_name=", run_name, ", output_files=", output_files, ", from_path=", from_path, ", to_path=", to_path)

                copied = self.upload_files_to_run(ws_name, run_name, to_path, output_files, exclude_dirs_and_files=after_omit_list)
                #console.print("AFTER files copied=", copied)
                copied_files += copied

                console.print("captured {} AFTER files from: {}".format(len(copied), output_files))

            elapsed = time.time() - started
            self.log_run_event(ws_name, run_name, "capture_after", {"elapsed": elapsed, "count": len(copied_files)})

        # tell mongo RUNS that this run has completed
        console.diag("calling MONGO run_exit: ws={}, run_name={}".format(ws_name, run_name))
        self.mongo.run_exit(ws_name, run_name)

        if not is_parent:
            # tell mongo this job has a completed run
            console.diag("calling MONGO job_run_exit: job_id={}".format(job_id))
            self.mongo.job_run_exit(job_id, exit_code)

    def copy_run_files_to_run(self, ws_name, from_run, run_wildcard, to_run, to_path):
        return self.helper.copy_run_files_to_run(ws_name, from_run, run_wildcard, to_run, to_path)

    def update_mongo_run_at_end(self, ws_name, run_name, status, exit_code, restarts, end_time, log_records, hparams, metrics):
        return self.mongo.update_mongo_run_at_end(ws_name, run_name, status, exit_code, restarts, end_time, log_records, hparams, metrics)

    #---- LOW LEVEL ----
            
    def list_blobs(self, container, blob_path, return_names=True):
        return self.helper.list_blobs(container, blob_path, return_names=return_names)

    # ---- RUN FILES ----

    def create_run_file(self, ws_name, run_name, run_fn, text):
        '''create the specified run file 'run_fn' from the specified 'text'.
        '''
        #return self.helper.create_run_file(ws_name, run_name, run_fn, text)
        rf = self.run_files(ws_name, run_name, use_blobs=True)
        return rf.create_file(run_fn, text)

    def append_run_file(self, ws_name, run_name, run_fn, text):
        '''append 'text' to the run file 'run_fn'.
        '''
        #return self.helper.append_run_file(ws_name, run_name, run_fn, text)
        rf = self.run_files(ws_name, run_name, use_blobs=True)
        return rf.append_file(run_fn, text)

    def read_run_file(self, ws_name, run_name, run_fn):
        '''return the contents of the run file 'run_fn'.
        '''
        #return self.helper.read_run_file(ws_name, run_name, run_fn)
        rf = self.run_files(ws_name, run_name, use_blobs=True)
        return rf.read_file(run_fn)

    def upload_file_to_run(self, ws_name, run_name, run_fn, source_fn):
        '''upload the local file 'source_fn' as the run file 'run_fn'.
        '''
        #return self.helper.upload_file_to_run(ws_name, run_name, run_fn, source_fn)
        rf = self.run_files(ws_name, run_name, use_blobs=True)
        return rf.upload_file(run_fn, source_fn)

    def upload_files_to_run(self, ws_name, run_name, run_folder, source_wildcard, exclude_dirs_and_files=[]):
        '''upload the local files specified by 'source_wildcard' to the run folder 'run_folder'.
        '''
        #return self.helper.upload_files_to_run(ws_name, run_name, run_folder, source_wildcard, exclude_dirs)
        rf = self.run_files(ws_name, run_name, use_blobs=True)
        return rf.upload_files(run_folder, source_wildcard, exclude_dirs_and_files=exclude_dirs_and_files)

    def download_file_from_run(self, ws_name, run_name, run_fn, dest_fn):
        '''download the run file 'run_fn' to the local file 'dest_fn'.
        '''
        dest_fn = os.path.abspath(dest_fn)      # ensure it has a directory specified
        #return self.helper.download_file_from_run(ws_name, run_name, run_fn, dest_fn)
        rf = self.run_files(ws_name, run_name, use_blobs=True)
        return rf.download_file(run_fn, dest_fn)

    def download_files_from_run(self, ws_name, run_name, run_wildcard, dest_folder):
        '''download the run files specified by 'run_wildcard' to the local folder 'dest_folder'.
        '''
        #return self.helper.download_files_from_run(ws_name, run_name, run_wildcard, dest_folder)
        rf = self.run_files(ws_name, run_name, use_blobs=True)
        return rf.download_files(run_wildcard, dest_folder)

    def get_run_filenames(self, ws_name, run_name, run_wildcard=None, full_paths=False):
        '''return the names of the run files specified by 'run_wildcard'.
        '''
        #return self.helper.get_run_filenames(ws_name, run_name, run_wildcard)    
        rf = self.run_files(ws_name, run_name, use_blobs=True)
        return rf.get_filenames(run_wildcard, full_paths=full_paths)
        
    def delete_run_file(self, ws_name, run_name, filename):
        '''delete the run file specified by 'filename'.
        '''
        rf = self.run_files(ws_name, run_name, use_blobs=True)
        return rf.delete_file(filename)

    def does_run_file_exist(self, ws_name, run_name, run_fn):
        '''return True if the specified run file 'run_fn' exists.
        '''
        #return self.helper.does_run_file_exist(ws_name, run_name, run_fn)
        rf = self.run_files(ws_name, run_name, use_blobs=True)
        return rf.does_file_exist(run_fn)

    #---- JOBS ----

    def create_job(self):
        # read legacy next_job_info in case we are first to run w/mongo-sequence numbers
        default_next = self.helper.read_legacy_next_job_id()
        if not default_next:
            default_next = 1
            
        job_id = self.mongo.get_next_job_id(default_next=default_next)

        job_name = "job{}".format(job_id)
        return job_name

    def get_job_secret(self, job_id):
        records = self.mongo.get_info_for_jobs( filter_dict={"_id": job_id}, fields_dict={"job_secret": 1} )
        value = records[0]["job_secret"] if len(records) else None
        return value

    def read_job_info_file(self, job_id):
        return self.helper.read_job_info_file(job_id)

    def write_job_info_file(self, job_id, text):
        # write to XT store
        self.helper.write_job_info_file(job_id, text)

        # update mongo-db for fast access
        dd = json.loads(text)
        self.mongo.update_job_info(job_id, dd)

    def write_runs_by_box(self, job_id, runs_by_box):
        docs = []
        for box_id, info in runs_by_box.items():
            dd = {'box_id': box_id, 'job_id': job_id}
            dd.update(info[0])
            docs.append(dd)

        self.mongo.mongo_with_retries("insert_runs_by_box", lambda: self.mongo.mongo_db["__runs_by_box__"].insert_many(docs))

    def write_service_job_info(self, job_id, service_job_info):
        service_job_info['job_id'] = job_id
        self.mongo.mongo_with_retries("insert_service_job_info", lambda: self.mongo.mongo_db["__service_job_info__"].insert_one(service_job_info))

    def write_service_info_by_node(self, job_id, service_info_by_node):
        docs = []
        for node_id, info in service_info_by_node.items():
            dd = {'node_id': node_id, 'job_id': job_id}
            dd.update(info)
            docs.append(dd)

        self.mongo.mongo_with_retries("insert_service_info_by_node", lambda: self.mongo.mongo_db["__service_info_by_node__"].insert_many(docs))

    def write_active_runs(self, job_id, active_runs):
        for run in active_runs:
            run['job_id'] = job_id

        self.mongo.mongo_with_retries("insert_active_runs", lambda: self.mongo.mongo_db["__active_runs__"].insert_many(active_runs))

    def log_job_info(self, job_id, dd):
        runs_by_box = dd['runs_by_box']
        service_job_info = dd['service_job_info']
        service_info_by_node = dd['service_info_by_node']
        active_runs = dd['active_runs']

        del dd['runs_by_box']
        del dd['service_job_info']
        del dd['service_info_by_node']
        del dd['active_runs']

        text = json.dumps(dd, indent=4)
        self.write_job_info_file(job_id, text)

        self.write_runs_by_box(job_id, runs_by_box)
        self.write_service_job_info(job_id, service_job_info)
        self.write_service_info_by_node(job_id, service_info_by_node)
        self.write_active_runs(job_id, active_runs)

    def log_job_event(self, job_id, event_name, data_dict=None, description=None, event_time=None):
        if not event_time:
            event_time = utils.get_time()

        if data_dict and not isinstance(data_dict, dict):   
            raise Exception("data_dict argument is not a dict: " + str(data_dict))
        record_dict = {"time": event_time, "event": event_name, "data": data_dict, "description": description}
        #console.print("record_dict=", record_dict)

        rd_text = json.dumps(record_dict)
        # append to run log file
        self.append_job_file(job_id, constants.JOB_LOG, rd_text + "\n")

    def get_job_log(self, job_id):
        text = self.read_job_file(job_id, constants.JOB_LOG)
        records = utils.load_json_records(text)
        return records

    #---- JOB FILES ----

    def create_job_file(self, job_name, job_path, text):
        '''create a job file specified by 'job_path' from the text 'text'.
        '''
        #self.helper.create_job_file(job_name, job_path, text)
        jf = self.job_files(job_name, use_blobs=True)
        return jf.create_file(job_path, text)

    def append_job_file(self, job_name, job_path, text):
        '''append text 'text' to the job file 'job_path'.
        '''
        #self.helper.append_job_file(job_name, job_path, text)
        jf = self.job_files(job_name, use_blobs=True)
        return jf.append_file(job_path, text)

    def read_job_file(self, job_name, job_path):
        '''return the contexts of the job file 'job_path'.
        '''
        #return self.helper.read_job_file(job_name, job_path)
        jf = self.job_files(job_name, use_blobs=True)
        return jf.read_file(job_path)

    def upload_file_to_job(self, job_name, fn_job, fn_source):
        '''upload the local file 'fn_source' as the job file 'fn_job'.
        '''
        #return self.helper.upload_file_to_job(job_name, job_folder, fn_source)
        jf = self.job_files(job_name, use_blobs=True)
        return jf.upload_file(fn_job, fn_source)

    def upload_files_to_job(self, job_name, job_folder, source_wildcard, recursive=False, exclude_dirs_and_files=[]):
        '''upload the local files specified by 'source_wildcard' to the job folder 'job_folder'.
        '''
        #return self.helper.upload_files_to_job(job_name, job_folder, source_wildcard)
        jf = self.job_files(job_name, use_blobs=True)
        return jf.upload_files(job_folder, source_wildcard, recursive=recursive, exclude_dirs_and_files=exclude_dirs_and_files)

    def download_file_from_job(self, job_name, job_fn, dest_fn):
        '''download the job file 'job_fn' to the local file 'dest_fn'.
        '''
        #return self.helper.download_file_from_job(job_name, job_fn, dest_fn)
        jf = self.job_files(job_name, use_blobs=True)
        return jf.download_file(job_fn, dest_fn)

    def download_files_from_job(self, job_name, job_wildcard, dest_folder):
        #return self.helper.download_files_from_job(job_name, job_wildcard, dest_folder)
        jf = self.job_files(job_name, use_blobs=True)
        return jf.download_files(job_wildcard, dest_folder)

    def get_job_filenames(self, job_name, job_wildcard=None, full_paths=False):
        '''return the names of the job files specified by 'job_wildcard'.
        '''
        #return self.helper.get_run_filenames(ws_name, run_name, run_wildcard)    
        jf = self.job_files(job_name, use_blobs=True)
        return jf.get_filenames(job_wildcard, full_paths=full_paths)

    def delete_job_file(self, job_name, filename):
        '''delete the job files specified by 'job_wildcard'.
        '''
        #return self.helper.delete_run_files(ws_name, run_name, run_wildcard)
        jf = self.job_files(job_name, use_blobs=True)
        return jf.delete_file(filename)

    def does_job_file_exist(self, job_name, job_path):
        '''return True if the job file 'job_path' exists.
        '''
        #return self.helper.does_job_file_exist(job_name, job_path)
        jf = self.job_files(job_name, use_blobs=True)
        return jf.does_file_exist(job_path)

    # def append_job_run_name(self, job_name, run_name):
    #     return self.helper.append_job_run_name(job_name, run_name)

    def get_job_run_names(self, job_name):
        return self.helper.get_job_run_names(job_name)

    # ---- DIRECT ACCESS ----
    
    def read_store_file(self, ws, path):
        return self.helper.read_store_file(ws, path)

    # ---- CAPTURE OUTPUT ----

    # def capture_stdout(self, fn=RUN_STDOUT):
    #     self.cap_stdout = StreamCapture(sys.stdout, fn)
    #     sys.stdout = self.cap_stdout

    # def capture_stderr(self, fn=RUN_STDERR):
    #     self.cap_stderr = StreamCapture(sys.stderr, fn)
    #     sys.stderr = self.cap_stderr

    def release_stdout(self):
        if self.cap_stdout:
            sys.stdout = self.cap_stdout.close()

    def release_stderr(self):
        if self.cap_stderr:
            sys.stderr = self.cap_stderr.close()

    # ---- FILES OBJECTS ----

    def root_files(self, root_name, use_blobs=False):
        return self.helper.root_files(root_name, use_blobs)

    def workspace_files(self, ws_name, use_blobs=False):
        return self.helper.workspace_files(ws_name, use_blobs)

    def run_files(self, ws_name, run_name, use_blobs=False):
        return self.helper.run_files(ws_name, run_name, use_blobs)

    def experiment_files(self, ws_name, exper_name, use_blobs=False):
        return self.helper.experiment_files(ws_name, exper_name, use_blobs)

    def job_files(self, job_name, use_blobs=False):
        return self.helper.job_files(job_name, use_blobs)

# sample code for path objects
#   wp = store.WorkspaceFiles(ws_name="ws1")  
#   wp.create_file("test.txt", "this is test.txt contents")

