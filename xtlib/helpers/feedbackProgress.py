#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# feedbackProgress.py: simple cmdline task progress display
from xtlib import utils
from xtlib import pc_utils
from ..console import console

CLEAR_TO_EOL = "\033[K"

class FeedbackProgress():
    def __init__(self, progress_enabled=True, output_enabled = True):
        self.progress_enabled = progress_enabled
        self.output_enabled = output_enabled
        self.last_len = 0
        self.status = ""
        pc_utils.enable_ansi_escape_chars_on_windows_10()

    def start(self):
        if self.progress_enabled:
            self.last_len = 0
            self.current = 0
            self.total = 0

            self.progress(starting=True)

    def erase_last_msg(self):
        if self.last_len:
            # erase prev msg
            console.print("\b"*self.last_len, CLEAR_TO_EOL, end="", flush=True, sep="")

        self.last_len = 0

    def progress(self, current=0, total=0, status=None, starting=False):
        #console.print("current={}, total={}, status={}, started={}".format(current, total, status, starting))

        if self.progress_enabled:

            if status:
                self.status = status.replace("-", " ")
                current = self.current
                total = self.total

            msg = ""

            if self.status:
                msg = self.status 

            if total or starting:
                if total:
                    msg2 = "{:d} % ({:,d} of {:,d} bytes)".format(round(100*current/total), current, total)
                else:
                    msg2 = "starting..."

                msg = msg + ", " + msg2 if msg else msg2

                self.total = total
                self.current = current

            if msg:
                self.erase_last_msg()

                console.print(msg, end="", flush=True, sep="")
                self.last_len = len(msg)

    def end(self):
        if self.output_enabled:
            if self.progress_enabled:
                console.print(flush=True)
            else:
                console.print("done", flush=True)

        self.last_len = 0
