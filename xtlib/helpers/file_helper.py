#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# file_helper.py: helps collect a list of local files, given lists of files to include and omit
import os
import zipfile
from fnmatch import fnmatch

from xtlib import utils
from xtlib import file_utils
from ..console import console

def _wildcard_match_in_list(source, name_list):
    matches = []

    if name_list:
        matches = [name for name in name_list if fnmatch(source, name)]
        
    return len(matches) > 0

def _director_match_in_list(dir_name, name_list):
    matches = []

    # only compare the last part of the directory name (since we are walking down it one node at a time and 
    # testing each node here)
    dir_name = os.path.basename(dir_name)
    dir_name = dir_name.lower()

    if name_list:
        matches = [name for name in name_list if name.lower() == dir_name]
        
    return len(matches) > 0

def get_filenames_from_wildcard(source_wildcard, exclude_dirs_and_files=[], recursive=False):
    filenames = []

    if source_wildcard.endswith("**"):
        # handle special "**" for recursive copy
        recursive = True
        source_wildcard = source_wildcard[:-1]   # drop last "*"
    elif os.path.isdir(source_wildcard):
        # simple dir name; make it glob-compatible
        # if source_wildcard != ".":
        #     ws_path += "/" + source_wildcard
        source_wildcard += "/*"

    console.detail("source_wildcard={}, recursive={}".format(source_wildcard, recursive))
    console.detail("exclude_dirs_and_files={}".format(exclude_dirs_and_files))
    
    for source_fn in file_utils.glob(source_wildcard):
        #console.print("source_fn=", source_fn)

        # check if basename is wildcard match
        source_name = os.path.basename(source_fn)
        if _wildcard_match_in_list(source_name, exclude_dirs_and_files):
            # omit processing this file or directory
            console.detail("skipping EXCLUDED file/dir: {}".format(source_name))
            continue

        if os.path.isfile(source_fn):
            console.detail("adding FILE: " + source_fn)
            filenames.append(source_fn)
        elif os.path.isdir(source_fn) and recursive:
            # check if directory is contains match
            if _director_match_in_list(source_fn, exclude_dirs_and_files):
                continue

            # copy subdir
            console.detail("processing DIR: " + source_fn)
            filenames += get_filenames_from_wildcard(source_fn + "/*", exclude_dirs_and_files=exclude_dirs_and_files, recursive=recursive)

    return filenames

def get_filenames_from_include_lists(include_lists, exclude_dirs_and_files=[], recursive=False, from_dir=None):
    filenames = []

    if include_lists:
        for source_wildcard in include_lists:
            if from_dir:
                source_wildcard = from_dir + "/" + source_wildcard

            filenames += get_filenames_from_wildcard(source_wildcard, exclude_dirs_and_files, recursive=recursive)
    else:
        if from_dir.endswith("**"):
            from_dir = from_dir [:-1]   # drop last "*"
            recursive = True
            
        filenames += get_filenames_from_wildcard(from_dir, exclude_dirs_and_files, recursive=recursive)

    return filenames

def zip_up_filenames(fn_zip, filenames, compress=True, remove_prefix_len=None):
    fn_zip = os.path.expanduser(fn_zip)
    file_utils.ensure_dir_exists(file=fn_zip)

    compression = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    #console.print("compression=", compression)

    with zipfile.ZipFile(fn_zip, "w", compression=compression) as zip: 
        # writing each file one by one 
        for fn in filenames: 
            #console.print("zipping fn: " + fn)
            fn_dest = fn[remove_prefix_len:] if remove_prefix_len else fn
            zip.write(fn, arcname=fn_dest) 

def unzip_files(fn_zip, dest_dir):

    with zipfile.ZipFile(fn_zip, "r") as zip: 
        names = zip.namelist() 
        zip.extractall(dest_dir)

    return names
    