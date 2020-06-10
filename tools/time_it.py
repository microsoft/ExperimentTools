#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# time_it.py: time execution of a command
import os
import sys
import time

cmd = " ".join(sys.argv[1:])
print("TIMEIT running cmd: " + cmd)

started = time.time()
os.system(cmd)
elapsed = time.time() - started
print("TIMEIT time elapsed: {:.4f}".format(elapsed))