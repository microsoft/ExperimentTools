#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# capture.py: support for uploading and download files to/from cloud storage
import os
import time

from xtlib import utils
from .console import console
from xtlib import constants
from .helpers import file_helper
from .helpers.feedbackParts import feedback as fb

def capture_before_files_zip(store, source_dir, ws_name=None, run_name=None, extra_files = [], rerun_name=None, 
        job_id=None,  omit_files=None, zip_before="none", store_dest="before", remove_prefix_len=None, upload_type=None):
    
    copied_files = []
    started = time.time()

    if rerun_name:
        if "/" in rerun_name:
            ws, rerun_name = rerun_name.split("/")
            
        copied_files = store.copy_run_files_to_run(ws_name, rerun_name, store_dest + "/", run_name, store_dest)
    else:
        # minimize confusion by deleting known files form previous run output
        #utils.zap_file("console.txt")

        # if not preserve_run_sh:
        #     utils.zap_file(constants.SH_NAME)

        # CAPTURE user-specified INPUT FILES

        before_files = [source_dir] + extra_files
        
        #console.print("before_files=", before_files)
        #console.print("omit_files=", omit_files)
        filenames = file_helper.get_filenames_from_include_lists(before_files, omit_files, recursive=True)
        count = len(filenames)
        where = "job" if job_id else "run"

        #console.print("zip-before=", zip_before)

        if zip_before in ["fast", "compress"]:
            fb.feedback("uploading {} {} files (zipped)".format(count, upload_type), add_seperator=False)

            zip_name = constants.CODE_ZIP_FN if upload_type == "code" else None
            fn_zip = os.path.expanduser(constants.CWD_DIR + "/" + zip_name)
            use_compress = (zip_before=="compress")
            file_helper.zip_up_filenames(fn_zip, filenames, use_compress, remove_prefix_len)

            before_files = [fn_zip]
            omit_files = []

            # look for wrapped cmds script; if found, copy it separately for bootstraping everything (backend=batch needs this)
            fn_wrapped = source_dir + "/" + constants.FN_WRAPPED_CMDS
            if os.path.exists(fn_wrapped):
                before_files.append(fn_wrapped)
        else:
            fb.feedback("uploading {} {} files".format(count, upload_type), add_seperator=False)

        console.diag("after zip of files")

        # TODO: modify store.upload_files_to_xxx to take a list of filenames
        for input_wildcard in before_files:
            if job_id:
                # "input_wildcard" is a wildcard string relative to the current working directory
                copied_files += store.upload_files_to_job(job_id, store_dest, input_wildcard, exclude_dirs_and_files=omit_files)
                dest_name = "job"
                elapsed = time.time() - started
                store.log_job_event(job_id, "capture_before", {"elapsed": elapsed, "count": len(copied_files)})
            else:
                # "input_wildcard" is a wildcard string relative to the current working directory
                copied_files += store.upload_files_to_run(ws_name, run_name, store_dest, input_wildcard, exclude_dirs_and_files=omit_files)
                dest_name = "run"
                elapsed = time.time() - started
                store.log_run_event(ws_name, run_name, "capture_before", {"elapsed": elapsed, "count": len(copied_files)})

    return copied_files

def download_before_files(store, job_id, ws_name, run_name, dest_dir, silent=False, log_events=True):
    files = []

    if job_id:
        # all files contained in JOB BEFORE
        files += store.download_files_from_job(job_id, "before/code/**", dest_dir)
        count = len(files)
        if not silent:
            console.print("  {} CODE files downloaded from store (JOB dir)".format(count))

        if log_events:
            store.log_run_event(ws_name, run_name, "download_before", {"source": "job", "count": count})
    else:
        if "." in run_name:
            # download from parent's RUN before files
            parent_name = run_name.split(".")[0]
            files += store.download_files_from_run(ws_name, parent_name, "before/**", dest_dir)
            count = len(files)
            if not silent:
                console.print("  {} files downloaded from store (PARENT'S RUN dir)".format(count))

            if log_events:
                store.log_run_event(ws_name, run_name, "download_before", {"source": "parent-run", "count": count})
        
        # download from normal/child RUN before files
        files += store.download_files_from_run(ws_name, run_name, "before/**", dest_dir)
        count = len(files)
        if not silent:
            console.print("  {} files downloaded from store (RUN dir)".format(count))

        if log_events:
            store.log_run_event(ws_name, run_name, "download_before", {"source": "run", "count": count})

    unzip_before_if_found(dest_dir, silent=silent)

    return files

def unzip_before_if_found(dest_dir, remove_after=True, silent=False):
    fn_zip = dest_dir + "/" + constants.CODE_ZIP_FN
    names = []

    if os.path.exists(fn_zip):
        found = True
        if not silent:
            console.print("unzipping fn_zip=", fn_zip)
        names = file_helper.unzip_files(fn_zip, dest_dir)

        if remove_after:
            os.remove(fn_zip)

    return names

def download_run(store, ws_name, run_name, dest_dir):
    '''
       - first, download entire RUN store
       - then, if BEFORE files are in job, download them
    '''
    files = []

    files += store.download_files_from_run(ws_name, run_name, "**", dest_dir)
    
    job_id = store.get_job_id_of_run(ws_name, run_name)

    # this will issue no errors if no files are found
    before_dir = dest_dir + "/before"
    before_files = store.download_files_from_job(job_id, "before/**", before_dir)

    zip_files = unzip_before_if_found(before_dir + "/code", silent=True)
    if zip_files:
        files += zip_files
    else:
        files += before_files

    return files
