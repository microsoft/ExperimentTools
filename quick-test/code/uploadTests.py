#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# uploadTest.py: test out various options for XT upload cmd
'''
   - file vs. blob
   - single vs. multiple
   - optional dest
   - progress updates vs. disabled
   - local directory/file not found

   GOAL: keep this test to about 60 secs.
   MEASURED: 53 secs (12/5/2019, rfernand21)
'''
import os
import time
import shutil

from xtlib import utils
from xtlib import constants
from xtlib import file_utils
import xtlib.xt_cmds as xt_cmds
from xtlib.helpers.dir_change import DirChange

mydir = os.getcwd()
cmd_count = 0

def test_cmd(cmd):
    global cmd_count
    print("uploadtests: testing ({}): ".format(1+cmd_count, cmd))
    xt_cmds.main(cmd)

    cmd_count += 1

# ---- SINGLE BLOB ----
def single_blob_tests():

    # blob, single, optional, enabled, found
    test_cmd("xt upload test1.py --share=sharetest")

    # blob, single, optional, enabled, not found
    #test_cmd("xt upload test1.pyxx")

    # blob, single, optional, disabled, found
    test_cmd("xt upload test1.py --share=sharetest --feedback=false")

    # blob, single, specified, enabled, found
    test_cmd("xt upload test1.py foo.py --share=sharetest")

    # PASS: dest=DOUBLE path
    test_cmd("xt upload test1.py maindir/subdir/test1.py --share=sharetest")

    # PASS: dest=PARENT path
    test_cmd("xt upload test1.py ../__ws__/parent.txt --share=sharetest")
    
    # PASS: dest=GLOBAL
    test_cmd("xt upload test1.py /{}/jobs/job1000/global_single.txt --share=sharetest".format(constants.INFO_CONTAINER))
    

# ---- MULTIPLE BLOBS ----
def multiple_blob_tests():
    # blob, multi, not specifed, enabled, found
    test_cmd("xt upload *.py --share=sharetest")

    # blob, multi, specifed, enabled, found
    test_cmd("xt upload *.py mypy --share=sharetest")

    # PASS: dest=DOUBLE path
    test_cmd("xt upload myapps maindir/subdir --share=sharetest")

    # PASS: dest=PARENT path
    test_cmd("xt upload *.py ../__ws__ --share=sharetest")
    
    # PASS: source=named, dest=PARENT 
    test_cmd("xt upload myapps ../__ws__ --share=sharetest")

    # PASS: dest=GLOBAL
    test_cmd("xt upload *.txt /{}/jobs/job1000 --share=sharetest".format(constants.INFO_CONTAINER))
    
    # PASS: source=RECURSIVE, dest=named
    test_cmd("xt upload myapps/** foo --share=sharetest")

#---- SINGLE FILE ----
#def single_file_tests():

    # # file, single, optional, enabled, found
    # test_cmd("xt upload file test1.py")

    # # file, single, optional, enabled, found
    # test_cmd("xt upload file test1.py foobar.py")

    # # file, single, optional, enabled, not found
    # #test_cmd("xt upload file test1.pyxx")

    # # file, single, optional, disabled, found
    # test_cmd("xt upload file test1.py --feedback=false")

    # # PASS: dest=DOUBLE path
    # test_cmd("xt upload file test1.py maindir/subdir/bar.txt")

    # # PASS: dest=PARENT path
    # test_cmd("xt upload file test1.py ../files/parent.py")
    
    # # PASS: dest=GLOBAL
    # test_cmd("xt upload file test1.txt /jobs/job1001/global.txt")
    

#---- MULTIPLE FILES ----
#def multiple_file_tests():
    # file, multi, not specifed, enabled, found
    # test_cmd("xt upload files *.py")

    # # file, multi, specifed, enabled, found, WILDCARD
    # test_cmd("xt upload files test*.py myapps")

    # # PASS: dest=DOUBLE path
    # test_cmd("xt upload files myapps maindir/subdir")

    # # PASS: dest=PARENT path
    # test_cmd("xt upload files *.py ../files")
    
    # # PASS: source=named, dest=PARENT 
    # test_cmd("xt upload files myapps ../files")

    # # PASS: dest=GLOBAL
    # test_cmd("xt upload files *.txt /jobs/job1000")
    
    # # PASS: source=RECURSIVE, dest=named
    # test_cmd("xt upload files myapps/** foo")

def generate(count, ext, subdir):
    texts = ["", "this is a test", "how about that?\nthis is a 2nd line\nthis is 3rd", "huh"]

    for i in range(count):
        fn = subdir + "test" + str(i) + ext
        file_utils.ensure_dir_exists(file=fn)

        with open(fn, "wt") as outfile:
            text = texts[i % 4]
            outfile.write(text)

def init():

    # bring over *.yaml file to put everything relative to quick-test
    shutil.copyfile("../xt_config.yaml", "./xt_config.yaml")

    # generate some files
    generate(3, ".py", "./")
    generate(2, ".txt", "./")
    generate(3, ".py", "./myapps/")
    generate(2, ".txt", "./myapps/")
    xt_cmds.main("xt create share sharetest")

def main():
    started = time.time()
    dir = "upload_testing"
    file_utils.ensure_dir_clean(dir)

    # move to a directory with a the set of files to upload

    with DirChange(dir):
        init()

        single_blob_tests()
        multiple_blob_tests()
        
        # single_file_tests()
        # multiple_file_tests()

    elapsed = time.time() - started
    print("\nend of uploadTests, elapsed={:.0f} secs".format(elapsed))
    xt_cmds.main("xt delete share sharetest --response sharetest")

    return cmd_count

if __name__ == "__main__":
    main()

