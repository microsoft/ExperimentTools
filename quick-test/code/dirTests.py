#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# dirTests.py: test out various options for XT dir cmd (subset for blobs and files)
'''
   - file vs. blob
   - no name, filename, wildcard
   - --subdir=0, --subdir=1, --subdir=True
   - base path: --work, --run, --exper, --job
   - no path, relative path, global path, root-path, parent path

   GOAL: keep this test to about 60 secs.
   MEASURED: 72 secs (12/5/2019, rfernand21)
'''
import os
import time
import xtlib.xt_cmds as xt_cmds

cmd_count = 0

def test_cmd(cmd):
    global cmd_count

    print("-----------------------")
    print("dirTests: testing ({}): ".format(1+cmd_count, cmd))
    xt_cmds.main(cmd)

    cmd_count += 1  

# ---- BLOBS ----
def dir_blobs():
    # PASS: blob, no name, subdir=0, --work, no path
    test_cmd("xt list blobs")

    # PASS: blob, name, subdir=0, --work, rel path
    test_cmd("xt list blobs myapps")

    # PASS: blob, wildcard, subdir=0, --work, rel-path
    test_cmd("xt list blobs myapps/test*.py")

    # PASS: blob, no name, subdir=0, --work, global-path
    test_cmd("xt list blobs /quick-test")

    # PASS blob, no name, subdir=0, --work, root-path
    test_cmd("xt list blobs /")

    # PASS: blob, no name, subdir=0, --work, parent-path
    test_cmd("xt list blobs ../")
    test_cmd("xt list blobs ../runs")
    test_cmd("xt list blobs ../../../../")

    # PASS: blob, no name, subdir=*, --work, no path
    test_cmd("xt list blobs /quick-test --subdir=0")
    test_cmd("xt list blobs /quick-test --subdir=1")
    test_cmd("xt list blobs /quick-test --subdir=-1")

    # PASS: blob, no name, subdir=*, --work/--run/--job/--exper, no path
    test_cmd("xt list blobs --work=quick-test")
    test_cmd("xt list blobs --exper=default-exper")
    test_cmd("xt list blobs --run=run2.1")
    test_cmd("xt list blobs --job=job1000")

#---- FILES ----
# def dir_files():
#     # PASS: file, no name, subdir=0, --work, no path
#     test_cmd("xt dir files")

#     # PASS: file, name, subdir=0, --work, rel path
#     test_cmd("xt dir files myapps")

#     # PASS: file, wildcard, subdir=0, --work, rel-path
#     test_cmd("xt dir files myapps/test*.py")

#     # file, no name, subdir=0, --work, global-path
#     test_cmd("xt dir files /workspaces/quick-test")

#     # file, no name, subdir=0, --work, root-path
#     test_cmd("xt dir files /")

#     # file, no name, subdir=0, --work, parent-path
#     test_cmd("xt dir files ../")
#     test_cmd("xt dir files ../files")
#     test_cmd("xt dir files ../../../../")

#     # file, no name, subdir=*, --work, no path
#     test_cmd("xt dir files ../ --subdir=0")
#     test_cmd("xt dir files ../ --subdir=1")
#     test_cmd("xt dir files ./ --subdir=-1")

#     # file, no name, subdir=*, --work/--run/--job/--exper, no path
#     test_cmd("xt dir files --work=quick-test")

#     test_cmd("xt upload files *.py --exper=default-exper")
#     test_cmd("xt dir files --exper=default-exper")

#     test_cmd("xt upload files *.py --run=run2.1")
#     test_cmd("xt dir files --run=run2.1")

#     test_cmd("xt upload files *.py --job=job1000")
#     test_cmd("xt dir files --job=job1000")

def main():
    started = time.time()

    dir_blobs()
    #dir_files()

    elapsed = time.time() - started
    print("\nend of dirTests, elapsed={:.0f} secs".format(elapsed))

    return cmd_count
    
if __name__ == "__main__":
    main()
