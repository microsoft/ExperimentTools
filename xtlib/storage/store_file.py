#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# store_file.py - an XT storage provider that uses for file-based storge (local directory or file share)

import os
import re
import shutil
import json
import time
import datetime
from interface import implements

from xtlib import utils
from xtlib import errors
from xtlib import constants
from xtlib import file_utils

from xtlib.console import console
from xtlib.storage.store_interface import StoreInterface

class FileStore(implements(StoreInterface)):
    def __init__(self, storage_creds):
        self.path = os.path.expanduser(storage_creds["path"])
        self.retry = None

        # create directory, if needed
        file_utils.ensure_dir_exists(self.path)

    # ---- HELPERS ----
    def _make_path(self, container=None, blob_path=None, snapshot=None):
        path = self.path
        if container:
            path = os.path.join(path, container)
            if blob_path:
                path = os.path.join(path, blob_path)
            if snapshot:
                path += snapshot

        return path

    # ---- MISC part of interface ----
    def get_service_name(self):
        ''' return the unique name of the storage service'''
        return "store_file://" + self.path

    def set_retries(self, count):
        ''' this provider doesn't currently retry errors.
        '''
        old_count = self.max_retries
        self.max_retries = count

        self.retry = utils.make_retry_func(count)
        return old_count

    def get_retry(self):
        return self.retry

    def set_retry(self, value):
        self.retry = value

    # ---- CONTAINER interface ----

    def does_container_exist(self, container):
        path = self._make_path(container)
        return os.path.exists(path)

    def create_container(self, container):
        path = self._make_path(container)
        os.makedirs(path)
        return True

    def list_containers(self):
        return os.listdir(self.path)

    def delete_container(self, container):
        path = self._make_path(container)
        return file_utils.zap_dir(path)
        
    def get_container_properties(self, container):
        path = self._make_path(container)
        props = os.stat(path)
        return props

    def get_container_metadata(self, container):
        # not supported by this provider
        return {}

    # ---- BLOB interface ----

    def does_blob_exist(self, container, blob_path):
        path = self._make_path(container, blob_path)
        return os.path.exists(path)

    def create_blob(self, container, blob_path, text, fail_if_exists=False):
        path = self._make_path(container, blob_path)
        file_utils.ensure_dir_exists(file=path)

        if fail_if_exists and os.path.exists(path):
            errors.service_error("blob already exists: " + blob_path)

        with open(path, "wt") as outfile:
            outfile.write(text)
        return True

    def create_blob_from_path(self, container, blob_path, source_fn, progress_callback=None):
        '''
        NOTE: the file could be binary (don't assume it is text)
        '''
        path = self._make_path(container, blob_path)
        file_utils.ensure_dir_exists(file=path)

        shutil.copyfile(source_fn, path)
        return True

    def append_blob(self, container, blob_path, text, append_with_rewrite=False):
        '''
        we ignore the *append_with_rewrite* request here, since it is an azure limitation workaround
        and not needed in a file-system provider.
        '''
        path = self._make_path(container, blob_path)
        file_utils.ensure_dir_exists(file=path)

        with open(path, "at") as outfile:
            outfile.write(text)
        return True

    def list_blobs(self, container, path=None, return_names=True, recursive=True):
        '''
        NOTE: the semantics here a bit tricky
        NOTE: file paths and dir paths are relative to the PARENT of the *path* parameter

        if recursive:
            - return a flat list of all file paths (no directory entries)
        else: 
            - return a flat list of all file paths and all dir paths (add "/" to end of dir paths)
        
        if return_names:
            - return list of names
        else:
            - return a list of objects with following properties:
                .name     (file or dir path)
                .properties   (for files only)
                    .content_length   (number)
                    .modified_ns      (time in ns)
        '''
        base_path = self._make_path(container)
        path_len = 1 + len(base_path)

        full_path = self._make_path(container, path)

        rel_paths = []
        for root, dirs, files in os.walk(full_path):
            for file in files:
                fpath = os.path.join(root, file)
                fpath = fpath[path_len:]
                rel_paths.append(fpath)

            if not recursive:
                for dir in dirs:
                    dpath = os.path.join(root, dir) + "/"
                    dpath = dpath[path_len:]
                    rel_paths.append(dpath)
                break

        # use forward slashes
        rel_paths = [rel_path.replace("\\", "/") for rel_path in rel_paths]
        if return_names:
            return rel_paths

        # create list of blob objects
        blob_objs = []
        for i, rel_path in enumerate(rel_paths):
            full_blob_path = os.path.join(base_path, rel_path)
            blob_obj = self._make_blob_object(full_blob_path, rel_path)
            blob_objs.append(blob_obj)

        return blob_objs

    def _make_rel_blob_path(self, container, full_blob_path):
        # remove the base_path
        base_path = self._make_path(container)
        base_len = len(base_path)

        rel_blob_path = full_blob_path[base_len:]
        return rel_blob_path

    def _make_blob_object(self, full_blob_path, rel_blob_path):
        stats = os.stat(full_blob_path)

        props = utils.PropertyBag()
        props.content_length = stats.st_size
        props.last_modified = datetime.datetime.fromtimestamp(stats.st_mtime)

        blob = utils.PropertyBag()
        blob.name = rel_blob_path
        blob.properties = props
        
        return blob

    def delete_blob(self, container, blob_path, snapshot=None):
        path = self._make_path(container, blob_path, snapshot)
        return os.remove(path)

    def get_blob_text(self, container, blob_path):
        path = self._make_path(container, blob_path)
        with open(path, "rt") as infile:
            text = infile.read()
        return text

    def get_blob_to_path(self, container, blob_path, dest_fn, snapshot=None, progress_callback=None):
        '''
        NOTE: the file could be binary (don't assume it is text)
        '''
        path = self._make_path(container, blob_path, snapshot)
        print("get_blob_to_path: full source path={}".format(path))

        with open(path, "rb") as infile:
            data = infile.read()
        with open(dest_fn, "wb") as outfile:
            outfile.write(data)
        return data

    def get_blob_properties(self, container, blob_path):
        path = self._make_path(container, blob_path)

        rel_blob_path = self._make_rel_blob_path(container, path)
        blob_obj = self._make_blob_object(path, blob_path)
        return blob_obj

    def get_blob_metadata(self, container, blob_path):
        path = self._make_path(container, blob_path)
        return {}

    def copy_blob(self, source_container, source_blob_path, dest_container, dest_blob_path):
        from_path = self._make_path(source_container, source_blob_path)
        dest_path = self._make_path(dest_container, dest_blob_path)
        shutil.copyfile(from_path, dest_path)
        return True

    def snapshot_blob(self, container, blob_path):
        path = self._make_path(container, blob_path)
        ss_suffix = None

        for i in range(1, 1000):
            ss = "__ss{}__".format(i)
            ss_path = path + ss
            if not os.path.exists(ss_path):
                # create the snapshot
                shutil.copyfile(path, ss_path)
                ss_suffix = ss
                break
        
        fake_blob = utils.PropertyBag()
        fake_blob.snapshot = ss_suffix

        return fake_blob

