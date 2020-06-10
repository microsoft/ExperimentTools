#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# aml_shim.py: AML wants to run a python script, so we use this to launch our shell script
import sys
import os
from xtlib import console

# MAIN code
args = sys.argv[1:]
console.print("aml_shim: args=", args)

cmd = args[0]    # all are passed as a logical string (but args[1] is "1", so don't use that)
console.print("aml_shim: about to run cmd=", cmd)
os.system(cmd)
