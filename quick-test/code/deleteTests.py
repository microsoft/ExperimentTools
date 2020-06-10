#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# deleteTests.py: test out various options for XT delete cmd (subset for blobs and files)
'''
   - for now: files only
   - no name, filename, wildcard
   - --subdir=0, --subdir=1, --subdir=True
   - base path: --work, --run, --exper, --job
   - no path, relative path, global path, root-path, parent path
'''
import os
import time
import sys

import xtlib.xt_cmds as xt_cmds
from xtlib import utils
from xtlib.helpers.dir_change import DirChange

cmd_count = 0

def test_cmd(cmd, name):
    global cmd_count
    print("-------------------------------")
    print(name)
    print("deleteTests: testing ({}): ".format(1+cmd_count, cmd))
    xt_cmds.main(cmd)

    cmd_count += 1

#---- FILES ----
# def delete_by_filename():
#     # ensure we have files to delete
#     test_cmd("xt upload files **", "filename: populate files")

#     # single filename with IMPLICIT path
#     test_cmd("xt delete file xtTestApp.py", "filename:IMPLICIT path")

#     # single filename with RELATIVE path
#     test_cmd("xt delete file myapps/miniSweeps.yaml", "filename:RELATIVE path")

#     # single filename with PARENT path
#     test_cmd("xt delete file ../files/miniSweeps.yaml", "filename:PARENT path")

#     # single filename with GLOBAL path
#     test_cmd("xt delete file /workspaces/quick-test/files/listTests.py", "filename:GLOBAL path")

# def delete_by_wildcard():
#     # ensure we have files to delete
#     test_cmd("xt upload files **", "wildcard: populate files")

#     # single filename with IMPLICIT path
#     test_cmd("xt delete file xtTestApp.*", "wildcard: IMPLICIT path")

#     # single filename with RELATIVE path
#     test_cmd("xt delete file myapps/*", "wildcard: RELATIVE path")

#     # single filename with PARENT path
#     test_cmd("xt delete file ../files/*.txt", "wildcard: PARENT path")

#     # single filename with GLOBAL path
#     test_cmd("xt delete file /workspaces/quick-test/files/*.py", "wildcard: GLOBAL path")

# def delete_by_directory():
#     # ensure we have files to delete
#     test_cmd("xt upload files **", "directory: populate files")
#     test_cmd("xt upload files myApps foo", "directory: populate files")

#     # single filename with RELATIVE path
#     test_cmd("xt delete file myapps", "directory: RELATIVE path")

#     # single filename with PARENT path
#     test_cmd("xt delete file ../files/foo", "directory: PARENT path")

#     # single filename with GLOBAL path
#     test_cmd("xt delete file /workspaces/quick-test/files", "directory: GLOBAL path")

# MAIN CODE
def main():
    started = time.time()
    dir = "download_testing"

    with DirChange(dir):
        # delete_by_filename()
        # delete_by_wildcard()
        # delete_by_directory()
        pass

    elapsed = time.time() - started
    print("\nend of deleteTests, elapsed={:.0f} secs".format(elapsed))

    return cmd_count
    
if __name__ == "__main__":
    main()
