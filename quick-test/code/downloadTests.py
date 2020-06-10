#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# downloadTests.py: test out various options for XT download cmd
'''
   - file vs. blob
   - single vs. multiple
   - optional dest
   - progress updates vs. disabled
   - local directory/file not found

   GOAL: keep this test to about 60 secs.
   MEASURED: 78 secs (12/5/2019, rfernand21)
'''
import os
import time
import shutil

from xtlib import utils
from xtlib import constants
from xtlib import file_utils
import xtlib.xt_cmds as xt_cmds
from xtlib.helpers.dir_change import DirChange

cmd_count = 0

def test_cmd(cmd):
    global cmd_count
    print("-------------------------------")
    print("downloadTests: testing ({}): ".format(1+cmd_count, cmd))
    xt_cmds.main(cmd)

    cmd_count += 1

# ---- SINGLE BLOB ----
def single_blob_tests():
    #test_cmd("xt list blobs")

    # blob, single, optional, enabled, found
    test_cmd("xt download test1.py")

    # blob, single, optional, enabled, not found
    #test_cmd("xt download test1.pyxx")

    # blob, single, optional, disabled, found
    test_cmd("xt download test1.py --feedback=false")

    # blob, single, specified, enabled, found
    test_cmd("xt download test1.py foo.py")

    # PASS: parent path into current dir
    test_cmd("xt download ../__ws__/test1.py foo2.py")
    
    # PASS: parent path into specified dir
    test_cmd("xt download ../__ws__/test1.py myfiles/foo2.py")

    # PASS: global path into current dir
    test_cmd("xt download /{}/__info__/next_job_number.control".format(constants.INFO_CONTAINER))
    

# ---- MULTIPLE BLOBS ----
def multiple_blob_tests():
    # blob, multi, not specifed, enabled, found
    test_cmd("xt download *.py")

    # blob, multi, specifed, enabled, found
    #test_cmd("xt download blobs *.py myapps")

    # PASS: reg path
    test_cmd("xt download myapps")

    # PASS: parent path into current dir
    test_cmd("xt download ../__ws__/maindir")
    
    # PASS: parent path into specified dir
    test_cmd("xt download ../__ws__/maindir myfiles")

    # PASS: global path into current dir
    test_cmd("xt download /{}/__info__/*".format(constants.INFO_CONTAINER))
    
    # PASS: recursive into local unnamed relative dir
    test_cmd("xt download maindir/**")
    
    # PASS: recursive into local named relative dir
    test_cmd("xt download myapps/** foo")
        
    # PASS: recursive into local absolute path
    test_cmd("xt download maindir/** ./xxx")
    file_utils.zap_dir("./xxx")

def init():
    shutil.copyfile("../xt_config.yaml", "xt_config.yaml")

def main():
    started = time.time()
    dir = "download_testing"
    file_utils.ensure_dir_clean(dir)

    with DirChange(dir):
        init()
        
        single_blob_tests()
        multiple_blob_tests()

        # restore initial working dir
        elapsed = time.time() - started
        print("\nend of downloadTests, elapsed={:.0f} secs".format(elapsed))

    return cmd_count
    
if __name__ == "__main__":
    main()

