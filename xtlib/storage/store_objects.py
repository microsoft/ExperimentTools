#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# store_objects.py: implements container/blob storage API and store objects APIs

from contextlib import redirect_stderr
#import azure.storage.common.retry as retry

import re
import os
import uuid
import sys
import time
import json
import shutil
import logging
import numpy as np
import importlib
from fnmatch import fnmatch

from xtlib import utils
from xtlib import errors
from xtlib import constants
from xtlib import file_utils

from xtlib.console import console

class StoreBlobObjs():
    '''
    Implements STORE blob access for Azure storage.  Note, we use "redirect_stderr" to 
    suppress the STDERR output from Azures API's when they have an _error to keep our
    console output a bit cleaner (easier to follow what's happening).
    '''
    def __init__(self, storage_creds, provider_code_path, max_retries=10):

        self.provider_name = storage_creds["provider"]

        # instantiate the provider
        class_ctr = utils.get_class_ctr(provider_code_path)
        self.provider = class_ctr(storage_creds)

        # Basic configuration: configure the root logger, including 'azure.storage'
        #logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s', level=logging.INFO)

        self.max_retries = max_retries
        self.set_retries(max_retries)

    def get_name(self):
        storage_name = self.provider.get_service_name()
        return storage_name
        
    def validate_storage_and_mongo(self, mongo):
        '''
        1. ensure storage has been initialized for XT
        2. ensure mongo and storage point to each other
        3. update storage format if needed
        4. update mongo format if needed
        '''

        # ensure storage has been initialized for XT
        self._create_info_container_if_needed()

        # ensure mongo points to our storage
        storage_name = self.provider.get_service_name()
        connected_mongo = mongo.get_service_name()

        mongo_info = mongo.get_mongo_info()
        paired_storage = utils.safe_value(mongo_info, "paired_storage")
        if paired_storage and storage_name != paired_storage:
            errors.combo_error("mongo paired with storage service='{}', but passed XT storage service='{}'".format(  \
                paired_storage, storage_name))

        storage_info = self._get_storage_info()
        paired_mongo = utils.safe_value(storage_info, "paired_mongo")
        if paired_mongo and connected_mongo != paired_mongo:
            errors.combo_error("this storage paired with mongo service='{}', but passed connection string for mongo service='{}'".format(  \
                connected_mongo, paired_mongo))

        if not paired_storage:
            mongo_info = {"paired_storage": storage_name, "storage_version": constants.STORAGE_VERSION}
            mongo.set_mongo_info(mongo_info)

        if not paired_mongo:
            storage_info = {"paired_mongo": connected_mongo, "storage_version": constants.STORAGE_VERSION}
            self._set_storage_info(storage_info)

        # only check once, (takes .5 secs if already imported)
        # remove this check after all XT users have imported (approx. Dec 2019)
        # but keep around (good for mongodb repair, if needed)
        self.import_jobs_to_mongo_if_needed(mongo)

    def import_jobs_to_mongo_if_needed(self, mongo):
        console.diag("before mongo import check")
        found = mongo.does_jobs_exist()
        console.diag("after mongo import check")

        if not found:
            # first time we have seen this data; import all jobs into mongo-db now
            console.print("one-time import of jobs data into mongo-db:")
            job_names = self.get_job_names()
            if job_names:
                console.print("  {:,} jobs will be imported".format(len(job_names)))
                count = 0
                for job_id in job_names:
                    job_json = self.read_job_info_file(job_id)
                    dd = json.loads(job_json)
                    mongo.update_job_info(job_id, dd)
                    count += 1
                    if count % 100 == 0:
                        console.print("  " + job_id)

                console.print("  {} jobs imported".format(count))

    def _get_storage_info(self):
        text = self._read_blob(constants.INFO_CONTAINER, constants.STORAGE_INFO_FILE)
        info = json.loads(text)
        return info

    def _set_storage_info(self, info):
        # write back to blob
        text = json.dumps(info)
        self._create_blob(constants.INFO_CONTAINER, constants.STORAGE_INFO_FILE, text)

    def _create_info_container_if_needed(self):
        info_container = constants.INFO_CONTAINER

        container_exists = self.provider.does_container_exist(info_container)
        if not container_exists or not self.provider.does_blob_exist(info_container, constants.STORAGE_INFO_FILE):

            # create container
            if not container_exists:
                self.provider.create_container(info_container)

            # create storage info file
            info = {"version": constants.STORAGE_VERSION, "paired_mongo": None}
            text = json.dumps(info)
            self._create_blob(info_container, constants.STORAGE_INFO_FILE, text)

            # create the DATA SHARE if needed
            if not self.provider.does_container_exist(utils.DATA_STORE_ROOT):
                self.provider.create_container(utils.DATA_STORE_ROOT)

            # create the MODELS SHARE if needed
            if not self.provider.does_container_exist(utils.MODELS_STORE_ROOT):
                self.provider.create_container(utils.MODELS_STORE_ROOT)

    # ---- INTERNAL HELPERS ----
    def _check_ws_name(self, ws_name):
        if not self.is_legal_workspace_name(ws_name):
           errors.syntax_error("error: Illegal Azure workspace name (must be >= 3 alphanumeric chars, dashes OK, no space or underscore chars)")

    def _get_job_dir(self, job_name):
        return constants.JOBS_DIR + "/" + job_name 

    def _get_job_path_fn(self, job_name, blob_path):
        return constants.JOBS_DIR + "/" + job_name + "/" + blob_path

    def _make_workspace_path_fn(self, ws, fn):
        # note: path does not include the "ws"
        return constants.WORKSPACE_DIR + "/" + fn

    def _exper_path(self, exper_name):
        return constants.EXPERIMENTS_DIR + "/" + exper_name 

    def _exper_path_fn(self, exper_name, fn):
        return constants.EXPERIMENTS_DIR + "/" + exper_name + "/" + fn

    def _run_path(self, run_name):
        return constants.RUNS_DIR + "/" + run_name 

    def _make_run_path_fn(self, run_name, fn):
        return constants.RUNS_DIR + "/" + run_name + "/" + fn

    def _remove_first_node(self, path):
        ''' remove first node of path '''
        new_path = "/".join(path.split("/")[1:])
        return new_path

    def _create_blob(self, ws_name, blob_path, text, fail_if_exists=False):
        self.provider.create_blob(ws_name, blob_path, text, fail_if_exists=fail_if_exists)

    def _append_blob(self, ws_name, blob_path, text, append_with_rewrite=False):
        #console.print("append: ws_name=", ws_name, ", blob_path=", blob_path, ", text=", text)
        self.provider.append_blob(ws_name, blob_path, text, append_with_rewrite=append_with_rewrite)

    def _read_blob(self, ws_name, blob_path):
        console.diag("_read_blob: ws_name={}, blob_path={}".format(ws_name, blob_path))

        if not self.does_workspace_exist(ws_name):
            # avoid 10 retries and unfriendly storage errors
            errors.store_error("container doesn't exist: " + ws_name)

        if not self.provider.does_blob_exist(ws_name, blob_path):
            # avoid 10 retries and unfriendly storage errors
            errors.store_error("blob doesn't exist: container={}, path={}".format(ws_name, blob_path))

        blob_text = self.provider.get_blob_text(ws_name, blob_path)
        return blob_text

    def _list_wild_blobs(self, container, path, wc_target, include_folder_names=False):
        '''
        return a list of full blob names in the container 'container'
        and in the path specified by 'path' and wildcards spec in 'wc_target':

           case 1: path/folder       - return all blobs in folder
           case 2: path/folder/foo*  - return matching blobs in folder
           case 3: path/folder/**    - return all blobs in folder and in child directories

        if "include_folder_names" is True, for the cases 1-2 (where subfolder blobs are not being returned), the
        subfolder names are returned as "path/folder/subfolder/" (ending with a slash).

        NOTE: this means that if you want to list the blobs in child directories, you must use the "/**" on the 
        end of the "wc_target" arg.
        '''

        if path is None:
            path = ""

        if "**" in wc_target:
            # case 3: return all blobs for target and child directories
            names = list(self.provider.list_blobs(container, path=path))
        elif wc_target and ("*" in wc_target or "?" in wc_target):
            # case 2: normal wildcards specified (for target directory only)
            # use delimiter-trick to limit listing to target directory only
            if path:
                path += "/"
            #console.print("case 2   : prefix=", wild_dir)
            names = self.provider.list_blobs(container, path=path, recursive=False)
            #console.print("before fnmatch, names=", names)
            names = [name for name in names if fnmatch(name, wc_target)]
        else:
            # case 1: wild_base has no wildcards
            # use delimiter-trick to limit listing to target directory only
            if path:
                path += "/"
            #console.print("case 1: prefix=", ws_wildcard)
            names = [name for name in self.provider.list_blobs(container, path=path, recursive=False)]

        #console.print("_list_wild_blobs: include_folder_names=", include_folder_names, ", names=", names)
        if not include_folder_names:
            # filter OUT folder names
            names = [name for name in names if not name.endswith("/")]
        return names        

    def _delete_blobs(self, container, path, wc_target):
        delete_count = 0

        for bn in self._list_wild_blobs(container, path, wc_target, include_folder_names=True):
            self.provider.delete_blob(container, bn)
            delete_count += 1

        return delete_count

    def _wildcard_match_in_list(self, source, name_list):
        matches = []

        if name_list:
            matches = [name for name in name_list if fnmatch(source, name)]
            
        return len(matches) > 0

    def _upload_files(self, ws_name, ws_path, source_wildcard, recursive=False, exclude_dirs_and_files=[]):
        copied_files = []

        # ensure the container exists
        if not self.does_workspace_exist(ws_name):
            self.create_workspace(ws_name, description=None)

        if source_wildcard.endswith("**"):
            # handle special "**" for recursive copy
            recursive = True
            source_wildcard = source_wildcard[:-1]   # drop last "*"
        elif os.path.isdir(source_wildcard):
            # simple dir name; make it glob-compatible
            # if source_wildcard != ".":
            #     ws_path += "/" + source_wildcard
            source_wildcard += "/*"
            recursive = True

        console.detail("_upload_files: source_wildcard={}, ws_path={}, recursive={}".format(source_wildcard, ws_path, recursive))
        console.detail("exclude_dirs_and_files={}".format(exclude_dirs_and_files))
        
        for source_fn in file_utils.glob(source_wildcard):
            console.detail("source_fn=".format(source_fn))
            source_name = os.path.basename(source_fn)
            if self._wildcard_match_in_list(source_name, exclude_dirs_and_files):
                # omit processing this file or directory
                console.detail("skipping upload of file/dir: {}".format(source_name))
                continue

            if os.path.isfile(source_fn):
                console.detail("uploading FILE: " + source_fn)
                blob_path = ws_path + "/" + source_name
                #console.print("ws_name=", ws_name, ", blob_path=", blob_path, ", source_fn=", source_fn)
                result = self.provider.create_blob_from_path(ws_name, blob_path, source_fn)
                #console.print("after bs.create_blob_from_path, result=", result)
                copied_files.append(source_fn)
            elif os.path.isdir(source_fn) and recursive:
                # copy subdir
                console.detail("uploading DIR: " + source_fn)
                copied  = self._upload_files(ws_name, ws_path + "/" + source_name, source_fn + "/*", recursive=recursive, 
                    exclude_dirs_and_files=exclude_dirs_and_files)
                copied_files = copied_files + copied

        #console.print("copied_files=", copied_files)
        return copied_files

    def _get_blob_dir(self, path):
        index = path.rfind("/")
        index2 = path.rfind("\\")
        index = max(index, index2)

        if index > -1:
            path = path[index+1:]
        return path

    def _download_files(self, container, path, wc_target, dest_folder):
        #console.print("ws_name=", ws_name, ", ws_wildcard=", ws_wildcard)
        files_copied = []

        names = self._list_wild_blobs(container, path, wc_target, include_folder_names=True)
        console.diag("_download_files: names=", names)

        blob_dir = path
        bd_index = 1 + len(blob_dir)   # add for for trailing slash
        #console.print("blob_dir=", blob_dir, ", bd_index=", bd_index)

        for bn in names:
            base_bn = bn[bd_index:]
            dest_fn = dest_folder + "/" + base_bn
            console.detail("_download_files: bn=", bn, ", dest_fn=", dest_fn)

            file_utils.ensure_dir_exists(file=dest_fn)
            self.provider.get_blob_to_path(container, bn, dest_fn)
            files_copied.append(dest_fn)    

        return files_copied

    def _copy_files(self, container, from_path, from_wc_target, to_path):
        ''' copy files from one blob folder to another, within the same workspace/container.
        example call:  _copy_files("ws1", "runs/run8/before*", "runs/run13/before")
        ''' 
        files_copied = []

        #console.print("_copy_files: container=", container, ", ws_wildcard=", ws_wildcard, ", to_path=", to_path)
        names = self._list_wild_blobs(container, from_path, from_wc_target)
        #console.print("names=", names)
        blob_dir = path
        bd_index = 1 + len(blob_dir)   # add for for trailing slash
        #console.print("blob_dir=", blob_dir, ", bd_index=", bd_index)

        for bn in names:
            base_bn = bn[bd_index:]
            #console.print("blob_dir=", blob_dir, ", bd_index=", bd_index, ", base_bn=", base_bn)
            dest_path = to_path + "/" + base_bn

            # COPY BLOB
            self.provider.copy_blob(container, bn, container, dest_path)

            files_copied.append(base_bn)

        return files_copied

    def _list_directories(self, container, path, wc_target, subdirs=0):
        console.diag("_list_directories: container={}, path={}, wc_target={}, subdirs={}".format(
            container, path, wc_target, subdirs))

        service_name = self.provider.get_service_name()
        dd = {"store_name": "XT Store ({})".format(service_name)}
        #console.print("dd=", dd)

        if not container:
            # get a list of all containers is a special case 
            if path:
                errors.syntax_error("path can not be set when the container is set to '/'")
                
            folder, folder_names = self._get_root_folders()
            folders = [ folder ]

            if subdirs:
                base_path = ""
                for ws_name in folder_names:
                    # get blobs from AZURE
                    console.diag("reading blobs for ws={}".format(ws_name))
                    blobs  = self.provider.list_blobs(ws_name, path=None, return_names=False)
                    blobs = list(blobs)

                    ws_folders = self._build_folders_from_blobs(blobs, ws_name, 
                        base_path, subdirs)

                    folders += ws_folders
        else:
            # get blobs from AZURE
            actual_path = path if path else None
            blobs  = self.provider.list_blobs(container, path=actual_path, return_names=False)
            blobs = list(blobs)

            if wc_target:
                # apply filter
                blobs = [blob for blob in blobs if fnmatch(blob.name, wc_target)]

            console.diag("list_blobs returned: len(blobs)={}".format(len(blobs)))

            folders = self._build_folders_from_blobs(blobs, container, path, subdirs)
        
        # filter folders as per subdirs
        if not subdirs is True:
            # subdirs is set to an int value
            #console.print("filtering by subdirs=", subdirs)
            folders = [f for f in folders if f["level"] <= subdirs]
 
        dd["folders"] = folders
        return dd

    def _get_first_dir(self, path):
        first_dir = None
        rest = None

        if path:
            if path.startswith("/"):
                path = path[1:]
            if "/" in path:
                index = path.index("/")
                first_dir = path[0:index]
                rest = path[index+1:]
                #console.print("path=", path, ", first_dir=", first_dir)
            else:
                first_dir = path
                if first_dir.endswith("/*"):
                    first_dir = first_dir[0:-2]
                rest = ""

        return first_dir, rest

    def _build_folders_from_blobs(self, blobs, ws_name, base_path, subdirs):
        folders_by_name = {}
        folders = []    # ordered list of folders

        base_len = len(base_path)
        if base_path.endswith("*"):
            base_len -= 1
        if base_path:
            base_len += 1    # for trailing slash
            
        base_folder = self._get_folder(folders, folders_by_name, ws_name, base_path, base_len)
        #console.print("base_folder=", base_folder)

        for i, blob in enumerate(blobs):

            full_blob_path = blob.name
            #console.print("full_blob_path=", full_blob_path)

            file_path = os.path.dirname(full_blob_path)
            parent_path = os.path.dirname(file_path)

            if subdirs or file_path == base_path:
                # add file to its folder
                folder = self._get_folder(folders, folders_by_name, ws_name, file_path, base_len)
                
                # create a new file entry
                fi = {"name": os.path.basename(blob.name)}
                fi["size"] = blob.properties.content_length 
                fi["modified"] = blob.properties.last_modified.timestamp()
                folder["files"].append(fi)

            if subdirs:
                # add all path parts to their parent folders
                child_path = file_path

                while len(parent_path) >= len(base_path):    # and parent_path != "/":
                    #console.print("  parent_path=", parent_path, ", child_path=", child_path, ", base_path=", base_path)
                    if parent_path:
                        parent_folder = self._get_folder(folders, folders_by_name, ws_name, parent_path, base_len)
                    else:
                        parent_folder = base_folder

                    # add child dir, if needed
                    child_name = os.path.basename(child_path)
                    dirs = parent_folder["dirs"]
                    if not child_name in dirs:
                        dirs.append(child_name)

                    # stop when base_path folder has been added to
                    if parent_path == base_path:
                        break

                    # process next level up
                    child_path = parent_path
                    parent_path = os.path.dirname(parent_path)
            else:
                # just process the left-most directory part of rel_path
                rel_file_path = file_path[base_len:]
                left_most_path, rest = self._get_first_dir(rel_file_path)
                #console.print("FIRST left_most_path=", left_most_path, ", rest=", rest)
                if left_most_path:
                    # add child dir, if needed
                    dirs = base_folder["dirs"]
                    child_name = os.path.basename(left_most_path)
                    if not child_name in dirs:
                        dirs.append(child_name)
        
        return folders

    def _get_folder(self, folders, folders_by_name, ws_name, path, base_name_len):
        if not path in folders_by_name:
            # create a new folder
            display_name = "/" + ws_name 
            if path and path != "/":
                display_name += "/" + path
            rel_path = path[base_name_len:]
            #console.print("rel_path=", rel_path)

            folder = {"folder_name": display_name}
            folder["dirs"] = []
            folder["files"] = []
            folder["level"] = 1 + rel_path.count("/") if rel_path else 0
            folders_by_name[path] = folder
            folders.append(folder)

            #console.print("folder added: name=", display_name, ", level=", folder["level"])
        
        folder = folders_by_name[path]
        return folder

    def _get_root_folders(self):
        folder_names = self.provider.list_containers()

        folder = {"folder_name": "/"}
        folder["level"] = 0
        folder["files"] = []
        folder["dirs"] = folder_names

        return folder, folder_names

    # ---- MISC FUNCTIONS ----

    def set_retries(self, count):

        old_count = self.max_retries
        self.max_retries = count

        # bug workaround: standard Retry classes don't retry status=409 (container is being deleted)
        #import azure.storage.common.retry as retry
        #self.bs.retry = retry.LinearRetry(backoff=5, max_attempts=count).retry

        self.provider.set_retry(utils.make_retry_func(count))

        return old_count
        
    def list_blobs(self, container, blob_path, return_names=True):
        blobs  = self.provider.list_blobs(container, path=blob_path, return_names=return_names)
        return blobs

    # ---- SHARES ----

    def does_share_exist(self, share_name):
        container_name = utils.make_share_name(share_name)
        #console.print("does_share_exist: ws_name=", ws_name)
        self._check_ws_name(container_name)
        return self.provider.does_container_exist(container_name)

    def ensure_share_exists(self, share_name, flag_as__error=True):
        container_name = utils.make_share_name(share_name)
        self._check_ws_name(container_name)
        exists = self.does_share_exist(share_name)
        if not exists:
            if flag_as__error:
                errors.store_error("Share not found: {}".format(share_name))
            self.create_share(share_name)

    def create_share(self, share_name, description=None):
        ''' create share as top level container '''

        container_name = utils.make_share_name(share_name)
        self._check_ws_name(container_name)

        # note: this operation often must retry several times if same container has just been deleted
        #console.print("creating share=", ws_name)

        # MULTIPROCESS: this is the step that will fail (if any)  
        result = self.provider.create_container(container_name)
        if not result:
             errors.store_error("could not create share: " + share_name)

    def delete_share(self, share_name):
        container_name = utils.make_share_name(share_name)
        self._check_ws_name(container_name)

        result = self.provider.delete_container(container_name)    

        if not result:
             errors.store_error("could not delete share: " + share_name)

        return result

    def get_share_names(self):
        containers = self.provider.list_containers()
        names = [name[4:-4] for name in containers if utils.is_share_name(name)]
        return names

    # ---- WORKSPACES ----

    def is_legal_workspace_name(self, ws_name):

        if not ws_name:
            return False
            
        if not bool(re.match('^[a-zA-Z0-9-]+$', ws_name)):
           return False
        
        if len(ws_name) < 3:
           return False

        return True

    def does_workspace_exist(self, ws_name):
        #console.print("does_workspace_exist: ws_name=", ws_name)
        self._check_ws_name(ws_name)
        return self.provider.does_container_exist(ws_name)

    def ensure_workspace_exists(self, ws_name, flag_as__error=True):
        self._check_ws_name(ws_name)
        exists = self.does_workspace_exist(ws_name)
        if not exists:
            if flag_as__error:
                 errors.store_error("Workspace not found: {}".format(ws_name))
            self.create_workspace(ws_name)

    def create_workspace(self, ws_name, description=None):
        ''' create workspace as top level container '''
        self._check_ws_name(ws_name)

        if self.does_workspace_exist(ws_name):
            errors.store_error("workspace already exists: {}".format(ws_name))

        # note: this operation often must retry several times if same container has just been deleted
        #console.print("creating workspace=", ws_name)

        # MULTIPROCESS: this is the step that will fail (if any)  
        result = self.provider.create_container(ws_name)
        if not result:
             errors.store_error("could not create workspace: " + ws_name)

        # MULTIPROCESS: safe now

        # create a holder file for RUNS directory
        runs_holder_fn = constants.RUNS_DIR + "/" + constants.HOLDER_FILE
        self._create_blob(ws_name, runs_holder_fn, "1", True)

        # create a holder file for EXPERIMENTS directory
        experiments_holder_fn = constants.EXPERIMENTS_DIR + "/" + constants.HOLDER_FILE
        self._create_blob(ws_name, experiments_holder_fn, "1", True)

        # create NEXT_RUN_NAME (for extra safety, ensure file doesn't already exist)
        blob_fn = constants.WORKSPACE_DIR + "/" + constants.WORKSPACE_NEXT
        self._create_blob(ws_name, blob_fn, "1", True)

    def delete_job(self, job_id):
        '''
        for use with "delete workspace" command, this
        only deletes the storage directory for the specified job 
        (not any of its runs or releated experiments).
        '''
        blob_names = self.provider.list_blobs(constants.INFO_CONTAINER, "jobs/" + job_id)
        for name in blob_names:
            self.provider.delete_blob(constants.INFO_CONTAINER, name)

    def delete_workspace(self, ws_name):
        result = self.provider.delete_container(ws_name)    

        if not result:
             errors.store_error("could not delete workspace: " + ws_name)

        return result

    def get_workspace_names(self):
        containers = self.provider.list_containers()

        names = [name for name in containers if self.workspace_files(name, use_blobs=True).does_file_exist(constants.WORKSPACE_NEXT)]
        return names

    # ---- EXPERIMENTS ----
    
    def does_experiment_exist(self, ws_name, exper_name):
        path = self._exper_path_fn(exper_name, constants.HOLDER_FILE)
        return self.provider.does_blob_exist(ws_name, path)

    def create_experiment(self, ws_name, exper_name):
        path = self._exper_path_fn(exper_name, constants.HOLDER_FILE)
        #console.print("create_experiment: path=", path)
        return self._create_blob(ws_name, path, "1")

    def append_experiment_run_name(self, ws_name, exper_name, run_name):
        path = self._exper_path_fn(exper_name, constants.AGGREGATED_RUN_NAMES_FN)
        self._append_blob(ws_name, path, run_name + "\n", append_with_rewrite=True)

    def get_experiment_run_names(self, ws_name, exper_name):
        path = self._exper_path_fn(exper_name, constants.AGGREGATED_RUN_NAMES_FN)
        if self.provider.does_blob_exist(ws_name, path):
            text = self._read_blob(ws_name, path)
            text = text[:-1]    # remove last \n char
            run_names = text.split("\n")
        else:
            run_names = []
        return run_names

    # ---- RUNS ----

    def does_run_exist(self, ws_name, run_name):
        # we cannot ensure the run directory exists since it's a virtual directory for blob
        # so we test for the run log file
        blob_path = self._run_path(run_name) + "/run.log"
        #console.print("ws_name=", ws_name, ", blob_path=", blob_path)
        return self.provider.does_blob_exist(ws_name, blob_path)

    def get_run_names(self, ws_name):
        # enumerate all blobs in workspace (ouch)
        run_names = self.provider.list_blobs(ws_name, path=constants.RUNS_DIR + "/run*", recursive=False)
        run_names = [name[0:-1] for name in run_names]

        # remove returned prefix on names
        plen = len(constants.RUNS_DIR + "/")
        run_names = [name[plen:] for name in run_names]

        #console.print("get_run_names: names=", names)
        return run_names

    def delete_run(self, ws_name, run_name):
        # run dir is a virtual directory that cannot be directly deleted
        # so, we need to enumerate and delete each one
        
        # since we are deleting from the list we are enumerating, safest to grab the whole list up frong
        blobs = list(self.provider.list_blobs(ws_name, path=self._run_path(run_name) + "/"))
        for blob in blobs:
            self.provider.delete_blob(ws_name, blob)   

    def copy_run(self, source_workspace_name, source_run_name, dest_workspace_name, dest_run_name):
        if self.does_run_exist(dest_workspace_name, dest_run_name):
             errors.store_error("destination run already exists: ws={}, run={}".format(dest_workspace_name, dest_run_name))

        # copy a single blob at a time
        #for source_blob_path in self.bs.list_blob_names(source_workspace_name, source_run_name):
        for source_blob in self.provider.list_blobs(source_workspace_name, path=self._run_path(source_run_name)  + "/"):
            dest_blob_path = self._run_path(dest_run_name)  + "/" + self._remove_first_node(source_blob)

            # copy single blob within same storage service
            self.provider.copy_blob(source_workspace_name, source_blob, dest_workspace_name, dest_blob_path)

    def get_run_log(self, ws_name, run_name):
        blob_path = self._run_path(run_name) + "/" + constants.RUN_LOG
        
        if not self.provider.does_blob_exist(ws_name, blob_path):
            # limited support for old-style run logging 
            blob_path = run_name + "/" + constants.RUN_LOG

        #console.print("blob_path=", blob_path)
        if not self.provider.does_blob_exist(ws_name, blob_path):
            errors.store_error("unknown run: ws={}, run_name={}".format(ws_name, run_name))

        #console.print("get_run_log: ws_name=", ws_name, ", blob_path=", blob_path)

        # watch out for 0-length blobs (azure will throw retryable exception if you use "get_blob_to_text")
        blob = self.provider.get_blob_properties(ws_name, blob_path)
        #console.print("blob.properties.content_length=", blob.properties.content_length)
        lines = []

        if blob.properties.content_length:
            text = self.provider.get_blob_text(ws_name, blob_path)
            #console.print("get_run_log: text=", text)

            lines = text.split("\n")
            #console.print("lines=", lines)
            lines = [json.loads(line) for line in lines if line.strip()]

        return lines

    # def create_run_directory(self, ws_name, run_name):
    #     pass   # nothing to do for blobs here

    def get_legacy_next_run_id(self, ws_name):
         # get next run number
        fn_next = constants.WORKSPACE_DIR + "/" + constants.WORKSPACE_NEXT
        #console.print("reading next num, fn_next=", fn_next)

        next = None
        if self.provider.does_blob_exist(ws_name, fn_next):
            text = self._read_blob(ws_name, fn_next)
            next = int(text)

        return next

    def remove_legacy_run_control_file(self, ws_name):
        fn_next = constants.WORKSPACE_DIR + "/" + constants.WORKSPACE_NEXT
        #console.print("reading next num, fn_next=", fn_next)

        if self.provider.does_blob_exist(ws_name, fn_next):
            self.provider.delete_blob(ws_name, fn_next)


    def create_next_run_by_name(self, ws_name, run_name):
        '''
        NOTE: unique run_name has already been assigned thru MONGO atomic process.
        '''
        self._check_ws_name(ws_name)    
        fail_if_exists = False     # allow for restarted runs 

        run_dir = self._run_path(run_name) 

        fn_flag = run_dir + "/" + constants.HOLDER_FILE
        self._create_blob(ws_name, fn_flag, "1", fail_if_exists)   

        return run_name

    def copy_run_files_to_run(self, ws_name, from_run, run_wildcard, to_run, to_path):
        from_path = self._make_run_path_fn(from_run, run_wildcard)
        dest_path = self._make_run_path_fn(to_run, to_path)
        return self._copy_files(ws_name, from_path, run_wildcard, dest_path)

    def read_legacy_next_job_id(self):
        # read next job number from control file
        info_dir = constants.INFO_DIR
        fn_next = info_dir + "/" + constants.JOBS_NEXT
        next_id = None

        if self.provider.does_blob_exist(constants.INFO_CONTAINER, fn_next):
            text = self._read_blob(constants.INFO_CONTAINER, fn_next)
            next_id = int(text) if text else 1
        return next_id

    #---- JOBS ----

    def read_job_info_file(self, job_name):
        fn_job = self._get_job_path_fn(job_name, constants.JOB_INFO_FN)
        if self.provider.does_blob_exist(constants.INFO_CONTAINER, fn_job):
            text = self._read_blob(constants.INFO_CONTAINER, fn_job)
        else:
            text = ""

        return text

    def write_job_info_file(self, job_name, text):
        fn_job = self._get_job_path_fn(job_name, constants.JOB_INFO_FN)
        self._create_blob(constants.INFO_CONTAINER, fn_job, text)

    def create_job_dir(self, job_name):
        #self.create_info_container_if_needed()
        job_dir_path = self._get_job_path_fn(job_name, constants.HOLDER_FILE)

        # MULTIPROCESS: safe, because only 1 user will try to create the job dir (?)
        if not self.provider.does_blob_exist(constants.INFO_CONTAINER, job_dir_path):
            self._create_blob(constants.INFO_CONTAINER, job_dir_path, "1")

    def get_job_names(self):
        path = constants.JOBS_DIR 
        names = [ name[5:-1] for name in self.provider.list_blobs(constants.INFO_CONTAINER, path=constants.JOBS_DIR + "/job*", recursive=False) ]
        #console.print("names=", names)
         
        # sort by increasing job number
        names.sort(key=lambda name: int(name[3:]))
        return names

    def append_job_run_name(self, job_name, run_name):
        path = self._get_job_path_fn(job_name, constants.AGGREGATED_RUN_NAMES_FN)
        self._append_blob(constants.INFO_CONTAINER, path, run_name + "\n", append_with_rewrite=True)

    def get_job_run_names(self, job_name):
        #console.print("getting job run_names for", job_name)
        path = self._get_job_path_fn(job_name, constants.AGGREGATED_RUN_NAMES_FN)
        if self.provider.does_blob_exist(constants.INFO_CONTAINER, path):
            text = self._read_blob(constants.INFO_CONTAINER, path)
            text = text[:-1]    # remove last \n char
            run_names = text.split("\n")
        else:
            run_names = []
        return run_names

    # ---- DIRECT ACCESS ----

    def read_store_file(self, ws, path):
        if path:
            if not path.startswith("/"):
                path = ws + "/" + path
        else:
            path = ws

        # split wild_path into workspace and rest
        ws_name, base_path = self._get_first_dir(path)
        return self._read_blob(ws_name, base_path)

    # ---- FILES OBJECTS helper functions ----

    def run_files(self, ws_name, run_name, use_blobs=False):
        if use_blobs:
            return RunBlobs(self, ws_name, run_name)
        else:
            return store_azure_file.RunFiles(self, ws_name, run_name)

    def experiment_files(self, ws_name, exper_name, use_blobs=False):
        if use_blobs:
            return ExperimentBlobs(self, ws_name, exper_name)
        else:
            return store_azure_file.ExperimentFiles(self, ws_name, exper_name)

    def workspace_files(self, ws_name, use_blobs=False):
        if use_blobs:
            return WorkspaceBlobs(self, ws_name)
        else:
            return store_azure_file.WorkspaceFiles(self, ws_name)

    def job_files(self, job_name, use_blobs=False):
        if use_blobs:
            return JobBlobs(self, job_name)
        else:
            return store_azure_file.JobFiles(self, job_name)

    def root_files(self, root_name, use_blobs=False):
        if use_blobs:
            return RootBlobs(self, root_name)
        else:
            #return store_azure_file.RootFiles(self, ws_name)
            errors.store_error("Root files are not current supported (use RootBlobs)")


# ---- FILES OBJECTS ----

class BlobsObject():
    def __init__(self):
        self.store = False
        self.container = None
        self.base_path = False

    # need for FilesObject
    # def get_dir_fn(self, path):
    #     full_path = self.root_path + path
    #     dir_path = os.path.dirname(full_path)
    #     fn = os.path.basename(full_name)
    #     return dir, fn

    def _expand_path(self, path, for_dir=False):
        base_path = self.base_path

        if base_path:
            if path:
                path = base_path + "/" + path
            else:
                path = base_path
        return path

    def create_file(self, path, text, block_size=None):
        path = self._expand_path(path)
        return self.store._create_blob(self.container, path, text)

    def append_file(self, fn, text):
        path = self._expand_path(fn)
        return self.store._append_blob(self.container, path, text)

    def read_file(self, fn):
        path = self._expand_path(fn)
        return self.store._read_blob(self.container, path)

    def upload_file(self, fn, source_fn, progress_callback=None):
        #path = self._expand_path(fn)
        container, path, wc_target = self._get_container_path_target(fn)
        if wc_target:
            errors.syntax_error("wildcard characters not allowed in filename")

        return self.store.provider.create_blob_from_path(container, path, source_fn, progress_callback=progress_callback)

    def upload_files(self, folder, source_wildcard, recursive=False, exclude_dirs_and_files=[]):
        path = self._expand_path(folder)
        return self.store._upload_files(self.container, path, source_wildcard, recursive=recursive, 
            exclude_dirs_and_files=exclude_dirs_and_files)

    def _process_parent_path(self, container, base_path, path):
        if path.startswith("./"):
            path = path[2:]

        while path.startswith("../"):
            if base_path:
                base_path = os.path.dirname(base_path)
            else:
                container = None

            path = path[3:]

        return container, base_path, path

    def _get_container_path_target(self, path):
        '''
        This helper function is the first step in converting all of our _xxx (internal)
        methods to accept as parameters:
            - container  (optional - None or the Azure container name to use)
            - path       (optional - None, or the container-relative path to the target store object)
            - wc_target  (optional - the last node of the path containing the wildcard characters)

        The "container" should be None, or a simple container name.  When set to None, the set of all 
        container names is returned.

        The "path" should be None or a set of blob-folder-names separated by "/" chars.  When set to None,
        the outer path of the container is targeted.

        The "wc_target" can be None, or a string containing the characters: *, ?, or **.  
        '''

        container = self.container

        if path:
            #console.print("path=", path)
            # path specified
            if path.startswith("blob-store://"):
                path = "/" + path[13:]

            if path.startswith("/"):
                # extract new value for container from left dir node
                path = path[1:]
                parts = path.split("/")
                container = parts[0]
                path = "/".join(parts[1:])
                #console.print("container=", container, ", path=", path)
            elif self.base_path:
                # merge them
                container, base_path, path = self._process_parent_path(container, self.base_path, path)

                if base_path and path:
                    path = base_path + "/" + path
                elif base_path:
                    path = base_path
        else:
            # path not specified
            path = self.base_path

        #console.print("path=", path)
        if "*" in path or "?" in path:
            wc_target = os.path.basename(path)
            path = os.path.dirname(path)

            if "*" in path or "?" in path:
                errors.syntax_error("wildcard characters are not allowed in directory part of store paths")
        else:
            wc_target = None

        #console.print("container=", container, ", path=", path, ", wc_target=", wc_target)
        return container, path, wc_target

    def download_file(self, fn, dest_fn, progress_callback=None, use_snapshot=False):
        container, path, wc_target = self._get_container_path_target(fn)
        #console.print("container=", container, ", path=", path)

        # ensure blob exists ourselves so we can issue a friendly error
        if not self.store.provider.does_blob_exist(container, path):
            errors.store_error("Blob not found: container={}, path={}".format(container, path))

        # ensure the directory of the dest_fn exists
        file_utils.ensure_dir_exists(file=dest_fn)

        if use_snapshot:
            # create temp. snapshot
            if progress_callback:
                progress_callback(status="creating-snapshot")
            props = self.store.provider.snapshot_blob(container, path)
            snapshot_id = props.snapshot

            # download the snapshot
            if progress_callback:
                progress_callback(status="downloading-snapshot")
            text = self.store.provider.get_blob_to_path(container, path, dest_fn, snapshot=snapshot_id, progress_callback=progress_callback)

            # delete the snapshot
            if progress_callback:
                progress_callback(status="deleting-snapshot")
            self.store.provider.delete_blob(container, path, snapshot=snapshot_id)

            if progress_callback:
                progress_callback(status="deleted-snapshot")
        else:
            # normal download
            text = self.store.provider.get_blob_to_path(container, path, dest_fn, progress_callback=progress_callback)

        return text

    def download_files(self, wildcard, dest_folder):
        container, path, wc_target = self._get_container_path_target(wildcard)
        console.diag("container={}, path={}, wc_target={}, wildcard={}".format(container, path, wc_target, wildcard))

        return self.store._download_files(container, path, wc_target, dest_folder)

    def get_filenames(self, wildcard="*", full_paths=False):
        if not "*" in wildcard:
            wildcard += "/*"
        container, path, wc_target = self._get_container_path_target(wildcard)
        names = self.store._list_wild_blobs(container, path, wc_target, include_folder_names=True)

        if not full_paths and path != "/":
            # convert to relative paths (relative to the path for this job/run/experiment/workspace)
            path_len = 1 + len(path)
            #console.print("PRE names=", names)
            names = [ name[path_len:] for name in names ]
            #console.print("POST names=", names)

        files = [name for name in names if not name.endswith("/")]
        dirs = [name[0:-1] for name in names if name.endswith("/")]
        #console.print("get_filenames: wildcard=", wildcard, ", files=", files, ", dirs=", dirs)
        return dirs, files

    def delete_file(self, filename):
        container, path, wc_target = self._get_container_path_target(filename)
        if wc_target:
            errors.syntax_error("wildcard not supported here: " + filename)
        self.store.provider.delete_blob(container, path)
        return True

    def delete_files(self, wildcard):
        container, path, wc_target = self._get_container_path_target(wildcard)
        return self.store._delete_blobs(self.container, path, wc_target)

    def delete_directory(self, dir_name):
        # nothing to do for blobs (assuming blobs have already been deleted)
        pass

    def does_file_exist(self, fn):
        container, path, wc_target = self._get_container_path_target(fn)
        if wc_target:
            errors.internal_error("wildcard cannot be specified here")

        return self.store.provider.does_blob_exist(container, path)

    def list_directories(self, path, subdirs=0):
        container, path, wc_target = self._get_container_path_target(path)

        #console.print("container=", container, ", path=", path, ", wc_target=", wc_target, ", subdirs=", subdirs)
        return self.store._list_directories(container, path, wc_target, subdirs)

    def get_uri(self, path):
        ''' return a URI that describes this path '''
        container, path, wc_target = self._get_container_path_target(path)
        uri = "blob-store://" + container
        if path:
            uri += "/" + path
        # if wc_target:
        #     uri += "/" + wc_target
        return uri

class RootBlobs(BlobsObject):
    def __init__(self, store, root_name):
        self.store = store
        self.container = root_name
        self.base_path = ""

        # create if needed on first access
        if not store.provider.does_container_exist(root_name):
            store.provider.create_container(root_name)

class WorkspaceBlobs(BlobsObject):
    def __init__(self, store, ws_name):
        self.store = store
        self.container = ws_name
        self.base_path = constants.WORKSPACE_DIR

class RunBlobs(BlobsObject):
    def __init__(self, store, ws_name, run_name):
        self.store = store
        self.container = ws_name
        self.base_path = constants.RUNS_DIR + "/" + run_name

class ExperimentBlobs(BlobsObject):
    def __init__(self, store, ws_name, exper_name):
        self.store = store
        self.container = ws_name
        self.base_path = constants.EXPERIMENTS_DIR + "/" + exper_name

class JobBlobs(BlobsObject):
    def __init__(self, store, job_name):
        self.store = store
        self.container = constants.INFO_CONTAINER
        self.base_path = constants.JOBS_DIR + "/" + job_name
