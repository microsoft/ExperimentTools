#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# console.py: control level of output during XT command processing 
'''
0 = no output
1 = normal output
2 = high level diagnostics ("capturing code files from dir=xxx")
3 = low level diagnostics ("capturing file: xxx")
'''
import sys
import time

class Console():
    '''
    Console class:
        - support 4 levels of output control: none, normal, diagnostics, and detail (low level diagnostics).

        - only complication is when we are geneating console output before we have processed the XT "console" option, 
          so we don't know which output, if any, we should send to stdout.

        - so, for "early processing", we capture all output and it's target level.  Then, when our set_level() method 
          is first called, we process the captured output and decide which results to print.
    '''
    def __init__(self, level="normal"):
        self.level = level      

        # we set these now for XTLib clients, but XT calls init_timing() to override these settings
        self.xt_started = time.time()
        self.xt_last_time = time.time()

        # for early processing
        self.early_output = []

        # for capture mode
        self.capturing_output = False
        self.captured_output = []

    def set_capture(self, value: bool):
        self.capturing_output = True
        if value:
            self.captured_output = []

        return self.captured_output

    def print_to_string(self, *objects, sep=' ', end='\n'):
        text = sep.join([str(obj) for obj in objects]) + end
        return text

    def early_print(self, target_level, *objects, sep=' ', end='', file=sys.stdout, flush=False):
        text = self.print_to_string(*objects, sep=sep, end=end)
        self.early_output.append( (target_level, text) )

    def print(self, *objects, sep=' ', end='\n', file=sys.stdout, flush=False):
        if self.level == None:
            self.early_print("normal", *objects, sep=sep, end=end, file=file, flush=flush)
        elif self.level != "none":
            print(*objects, sep=sep, end=end, file=file, flush=flush)

        if self.capturing_output:
            text = sep.join([str(obj) for obj in objects]) + end
            self.captured_output.append(text)

    def warning(self, msg):
        msg = "warning: " + msg
        self.print(msg)

    def diag(self, *objects, sep=' ', end='\n', exit_time=0, target="diagnostics"):
        if self.level in [None, "diagnostics", "detail"]:
            # JIT import to prevent import cycles here
            from .helpers.feedbackParts import feedback

            if self.level:
                feedback.stop_feedback()

            elapsed = time.time() - self.xt_started + exit_time
            delta = time.time() - self.xt_last_time + exit_time
            self.xt_last_time = time.time()

            text = self.print_to_string(*objects, sep=sep, end=end)

            if self.level is None:
                self.early_print(target, "[{:.2f}, +{:.2f}]: {}".format(elapsed, delta, text), flush=True)
            else:
                print("[{:.2f}, +{:.2f}]: {}".format(elapsed, delta, text), flush=True, end="")

    def detail(self, *objects, sep=' ', end='\n'):
        if self.level in [None, "detail"]:
            text = self.print_to_string(*objects, sep=sep, end=end)
            return self.diag(text, target="detail")

    def set_level(self, level):
        '''
        args:
            level: one of these strings: none, normal, diagnostics, and detail 
        '''
        self.level = level

        text = self.consume_early_input(level)
        print(text, end="")

    def consume_early_input(self, level):
        all_text = ""

        if level and self.early_output:
            # process early output now
            for target, text in self.early_output:
                if level == "normal" and target == "normal":
                    all_text += text
                elif level == "diagnostics" and target in ["normal", "diagnostics"]:
                    all_text += text
                elif level == "detail" and target in ["normal", "diagnostics", "detail"]:
                    all_text += text
        
            self.early_output = []

        return all_text

    def init_timing(self, argv, timing_name, xt_start_time, invoke_time):
        self.xt_started = xt_start_time
        self.xt_last_time = xt_start_time

        self.diag("console.init_timing() call (includes invoke time={:.2f})".format(invoke_time))

console = Console()

'''
example of how to use from a client module:
    from .console import console

    console.diag("starting to process")
    for fn in files:
        console.diag_detail("processing file {}".format(fn))

    console.print("{} files processed".format(count))

'''