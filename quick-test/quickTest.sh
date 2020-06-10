#!/bin/sh
# ---- quick-test.bat: test out basic commands and options of XT from cmd line ----
# 
# ---- HOW TO RUN ----
# 1. run: 
#    > quicktest.bat
#
# 2. after test completes:
#    a. ensure command window shows that "NO ERROR CODES - PASSED" msg
#    b. ensure command window has no obvious errors (stack traces)
#    a. ensure controller windows shows no obvious errors (stack traces)
#    c. run "xt list runs work=quick-test" and ensure output looks correct and has NO ERRORS
# -------------------------------

python code/quickTest.py --reset-workspace=1  $@
