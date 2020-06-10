#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# store-azure-blob21: Azure Blob Storage API (based on azure-storage-blob==2.1.0)
import logging
from interface import implements
from azure.storage.blob import AppendBlobService, BlockBlobService, PublicAccess
from azure.storage.blob.models import DeleteSnapshot

from xtlib import utils
from xtlib.storage.store_interface import StoreInterface

logger = logging.getLogger(__name__)

class AzureBlobStore21(implements(StoreInterface)):
    def __init__(self, storage_creds, max_retries=10):
        self.storage_id = storage_creds["name"]
        self.storage_key = storage_creds["key"]

        self.bs = BlockBlobService(account_name=self.storage_id, account_key=self.storage_key) 
        self.append_bs = AppendBlobService(account_name=self.storage_id, account_key=self.storage_key) 

        self.max_retries = max_retries    
        self.set_retries(max_retries)

    # ---- HELPER functions ----

    def set_retries(self, count):

        old_count = self.max_retries
        self.max_retries = count

        # bug workaround: standard Retry classes don't retry status=409 (container is being deleted)
        #import azure.storage.common.retry as retry
        #self.bs.retry = retry.LinearRetry(backoff=5, max_attempts=count).retry
        #self.append_bs.retry = retry.LinearRetry(backoff=5, max_attempts=count).retry

        self.bs.retry = utils.make_retry_func(count)
        self.append_bs.retry = utils.make_retry_func(count)

        return old_count

    # ---- MISC part of interface ----

    def get_service_name(self):
        ''' return the unique name of the storage service'''
        return self.storage_id
    
    def get_retry(self):
        return self.bs.retry

    def set_retry(self, value):
        self.bs.retry = value

    # ---- CONTAINER interface ----

    def does_container_exist(self, container):
        return self.bs.exists(container)

    def create_container(self, container):
        return self.bs.create_container(container)

    def list_containers(self):
        containers = self.bs.list_containers()
        name_list = [contain.name for contain in containers]
        return name_list

    def delete_container(self, container):
        return self.bs.delete_container(container)

    def get_container_properties(self, container):
        props = self.bs.get_container_properties(container)
        return props

    def get_container_metadata(self, container):
        md = self.bs.get_container_metadata(container)
        return md

    # def set_container_metadata(self, container, md_dict):
    #     return self.bs.set_container_metadata(container, md_dict)

    # ---- BLOB interface ----

    def does_blob_exist(self, container, blob_path):
        return self.bs.exists(container, blob_path)

    def create_blob(self, container, blob_path, text, fail_if_exists=False):
        ifn = "*" if fail_if_exists else None

        return self.bs.create_blob_from_text(container, blob_path, text, if_none_match=ifn)

    def create_blob_from_path(self, container, blob_path, source_fn, progress_callback=None):
        result = self.bs.create_blob_from_path(container, blob_path, source_fn, progress_callback=progress_callback)
        return result

    def append_blob(self, container, blob_path, text, append_with_rewrite=False):
        # create blob if it doesn't exist

        if not append_with_rewrite:
            # normal handling
            if not self.append_bs.exists(container, blob_path):
                self.append_bs.create_blob(container, blob_path)

            return self.append_bs.append_blob_from_text(container, blob_path, text)

        ''' 
        Appends text to a normal blob blob by reading and then rewriting the entire blob.
        Correctly handles concurrency/race conditions.
        Recommended for lots of small items (like 10,000 run names).

        Note: we turn off retries on azure CALL-level so that we can retry on 
        OUR CALL-level.
        '''
        # experimental local retry loop
        old_retry = self.bs.get_retry()
        self.bs.set_retry(utils.make_retry_func(0))
        succeeded = False

        for i in range(20):
            
            try:
                if self.bs.does_blob_exist(container, blob_path):
                    # read prev contents
                    blob_text = self.bs.get_blob_text(container, blob_path)
                    # append our text
                    new_text = blob_text + text
                    # write blob, ensuring etag matches (no one updated since above read)
                    self.bs.create_blob(container, blob_path, new_text, if_match=blob.properties.etag)
                else:
                    # if no previous blob, just try to create it
                    self.bs.create_blob(container, blob_path, text)
            except BaseException as ex:
                logger.exception("Error in _append_blob_with_retries, ex={}".format(ex))
                sleep_time = np.random.random()*4
                console.diag("XT store received an expected azure exception; will backoff for {:.4f} secs [retry #{}]".format(sleep_time, i+1))
                time.sleep(sleep_time)
            else:
                succeeded = True
                break

        # restore retry
        self.bs.set_retry(old_retry)

        if not succeeded:
            errors.service_error("_append_blob_with_rewrite failed (too many retries)")


    def list_blobs(self, container, path=None, return_names=True, recursive=True):
        '''
        NOTE: the semantics here a tricky

        if recursive:
            - return a flat list of all full path names of all files (no directory entries)
        else: 
            - return a flat list of all files and all directory names (add "/" to end of directory names)

        if return_names:
            - return list of names
        else:
            - return a list of objects with following properties:
                .name     (file pathname)
                .properties
                    .content_length   (number)
                    .modified_ns      (time in ns)

        The delimiter trick: this is when we set the delimiter arg = "/" to tell azure to return only the blobs 
        in the specified directory - that is, don't return blobs from child directories.  In this case, azure 
        returns the effective child directory name, followed by a "/", but not its contents (which we hope is faster).
        '''
        delimiter = None if recursive else "/"

        # specific Azure path rules for good results
        if path:
            if path.startswith("/"):
                path = path[1:]     # blob API wants this part of path relative to container

            # we should only add a "/" if path is a folder path
            if path.endswith("*"):
                # we just need to block the addition of "/"
                path = path[0:-1]
            elif not path.endswith("/"):
                path += "/"         # best if path ends with "/"

        blobs = self.bs.list_blobs(container, prefix=path, delimiter=delimiter)

        if return_names:
            blobs = [blob.name for blob in blobs]
        else:
            blobs = list(blobs)
        return blobs

    def delete_blob(self, container, blob_path, snapshot=None):
        dss = DeleteSnapshot()
        return self.bs.delete_blob(container, blob_path, delete_snapshots=dss.Include)

    def get_blob_text(self, container, blob_path):
        # watch out for 0-length blobs - they trigger an Azure RETRY error
        text = ""
        # azure storage bug workaround: avoid RETRY errors for 0-length blob 
        blob = self.bs.get_blob_properties(container, blob_path)
        if blob.properties.content_length:
            blob = self.bs.get_blob_to_text(container, blob_path)
            text = blob.content
        return text

    def get_blob_to_path(self, container, blob_path, dest_fn, snapshot=None, progress_callback=None):
        # azure storage bug workaround: avoid RETRY errors for 0-length blob 
        blob = self.bs.get_blob_properties(container, blob_path)
        if blob.properties.content_length:
            result = self.bs.get_blob_to_path(container, blob_path, dest_fn, snapshot=snapshot, progress_callback=progress_callback)
            text = result.content
        else:
            md = blob.metadata
            if "hdi_isfolder" in md and md["hdi_isfolder"]:
                # its a directory marker; do NOT create a local file for it
                text = ""
            else:
                # 0-length text file; just write the file outselves
                text = ""
                with open(dest_fn, "wt") as outfile:
                    outfile.write(text)
           
        return text

    def get_blob_properties(self, container, blob_path):
        props = self.bs.get_blob_properties(container, blob_path)
        return props

    def get_blob_metadata(self, container, blob_path):
        return self.bs.get_blob_metadata(container, blob_path)

    # def set_blob_metadata(self, container, blob_path, md_dict):
    #     return self.bs.set_blob_metadata(container, blob_path, md_dict)

    def copy_blob(self, source_container, source_blob_path, dest_container, dest_blob_path):
        source_blob_url = self.bs.make_blob_url(source_container, source_blob_path)
        self.bs.copy_blob(dest_container, dest_blob_path, source_blob_url)

    def snapshot_blob(self, container, blob_path):
        blob = self.bs.snapshot_blob(container, blob_path)
        #pd = utils.obj_to_dict(blob)
        return blob

