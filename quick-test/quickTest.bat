echo off

rem ---- quick-test.bat: test out basic commands and options of XT from cmd line ----
rem 
rem ---- HOW TO RUN ----
rem 1. run: 
rem    > quicktest.bat
rem
rem 2. after test completes:
rem    a. ensure command window shows that "NO ERROR CODES - PASSED" msg
rem    b. ensure command window has no obvious errors (stack traces)
rem    a. ensure controller windows shows no obvious errors (stack traces)
rem    c. run "xt list runs work=quick-test" and ensure output looks correct and has NO ERRORS
rem -------------------------------

python code\quickTest.py --reset-workspace=1  %*

