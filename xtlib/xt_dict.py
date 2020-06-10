#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# xt_dict.py: implementation of small persisted dictionary to managed $lastrun, $lastjob values by workspace
import os
import json

FN_XT_DICT = "~/.xt/xt_dict.json"   # xt persistent info (lastrun, etc)

def read_raw_xt_dict():
    xt_dict_by_dir = {}
    fn = os.path.expanduser(FN_XT_DICT)
    cwd = os.path.realpath(".")

    if os.path.exists(fn):
        with open(fn, "rt") as infile:
            text = infile.read()

        xt_dict_by_dir = json.loads(text)

    return xt_dict_by_dir

def read_xt_dict():
    cwd = os.path.realpath(".").lower()
    xt_dict_by_dir = read_raw_xt_dict()

    xt_dict = xt_dict_by_dir[cwd] if cwd in xt_dict_by_dir else {}
    return xt_dict

def write_xt_dict(xt_dict):
    fn = os.path.expanduser(FN_XT_DICT)
    cwd = os.path.realpath(".").lower()

    xt_dict_by_dir = read_raw_xt_dict()
    xt_dict_by_dir[cwd] = xt_dict

    with open(fn, "wt") as outfile:
        text = json.dumps(xt_dict_by_dir)
        outfile.write(text)

def get_xt_dict_value(key, default_value=None):
    xt_dict = read_xt_dict()
    value = xt_dict[key] if key in xt_dict else default_value
    return value
