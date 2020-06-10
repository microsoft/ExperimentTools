#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# unzip.py: python program to unzip files (*.zip, *.gz)
import os
import sys
import gzip
import shutil
import zipfile

fn = sys.argv[1]

if fn.endswith(".gz") or fn.endswith(".tar"):
    # unzip all files in fn
    with zipfile.ZipFile(fn, 'r') as zip_ref:
        zip_ref.extractall(".")

elif fn.endswith(".zip"):
    # unzip all files in fn
    with zipfile.ZipFile(fn, 'r') as zip_ref:
        zip_ref.extractall(".")


