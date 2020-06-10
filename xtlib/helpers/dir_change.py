#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# dir_change.py: does a structured dir changed
import os

class DirChange:
    def __init__(self, new_dir):
        self.orig_dir = os.getcwd()
        self.new_dir = new_dir
        
    def __enter__(self):
        os.chdir(self.new_dir)

    def __exit__(self, type, value, traceback):        
        os.chdir(self.orig_dir)
