#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# impl_base.py: base class for impl_xxx modules
import sys

from xtlib import console

class ImplBase():
    '''
    one common function implemented here - the ability to redirect console.print() output to self.output, for
    API calls that want console.print output returned as text
    '''
    def __init__(self):
        self.capture_output = False
        self.output = []
        self.orig_std_out = sys.stdout

    def set_capture_output(self, value):
        if value:
            self.orig_level = console.level
            console.set_level(None)
            result = None
        else:
            result = console.consume_early_input(self.orig_level)
            console.set_level(self.orig_level)

        return result

