#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# run_info.py: information about a run (kept on the controller)
import os
import sys
import copy 
import rpyc
import time 
import json
import psutil
import logging
from threading import Thread, Lock

from xtlib import utils
from xtlib import errors
from xtlib import file_utils

from xtlib.console import console
from xtlib.storage.store import store_from_context

logger = logging.getLogger(__name__)

class RunInfo():
    def __init__(self, run_name, workspace, cmd_parts, run_script, repeat, context, status, show_output=True, parent_name=None, 
        parent_prep_needed=False, mirror_close_func=None, aml_run=None, node_id=None, run_index=None, mri=None, mri_entry=None):

        if isinstance(repeat, str):
            repeat = int(repeat)

        self.run_name = run_name
        self.parent_name = parent_name
        self.workspace = workspace
        self.cmd_parts = cmd_parts
        self.run_script = run_script
        self.repeat = repeat
        self.repeats_remaining = repeat if context.repeats_remaining is None else context.repeats_remaining 
        self.context = context
        self.status = status    
        self.is_wrapped_up = False     # this is set to True by controller when all wrapup processing has completed
        self.show_output = show_output
        self.callbacks = [] 
        self.acallbacks = []
        self.exit_code = None
        self.killing = False
        self.lock = Lock()   
        self.process = None     
        self.store = None    
        self.recent_output = []
        self.max_recent = 10
        self.rundir = None      # assigned at start time
        self.started = time.time()      # time started with current status
        self.elapsed = None
        self.parent_prep_needed = parent_prep_needed      # when True, must run parent prep script before running first child
        self.console_fn = None
        self.process_was_created = False
        self.mirror_worker = None
        self.mirror_close_func = mirror_close_func
        self.aml_run = aml_run
        self.is_aml = not(not aml_run)
        self.job_id = context.job_id
        self.exper_name = context.exper_name
        self.username = context.username
        self.run_as_parent = context.search_style != "single"
        self.node_id = node_id
        self.run_index = run_index
        self.mri = mri
        self.mri_entry = mri_entry
        self.killed_for_restart = False

        console.print("RunInfo: is_aml=", self.is_aml, ", aml_run=", self.aml_run)

        #console.print("mirror_close_func=", mirror_close_func)
        
        #console.print("run_info ctr: setting self.repeats_remaining=", self.repeats_remaining)
        
    def set_console_fn(self, console_fn):
        console_fn = os.path.expanduser(console_fn)
        self.console_fn = console_fn

        if os.path.exists(console_fn):
            os.remove(console_fn)

        file_utils.ensure_dir_exists(file=console_fn)


    def process_run_output(self, text_msg, run_info_is_locked=False):

        # if self.context.scrape:
        #     # scrape output line for XT log records
        #     if self.scrape_output(text_msg):
        #         # don't show scraped output to user
        #         return

        # let run_info keep recent output for new clients
        self.update_recent_output(text_msg)

        # append to output file
        with open(self.console_fn, "a") as tfile:
            tfile.write(text_msg)

        # send output to attached clients
        if self.show_output:
            # console.print output on CONTROLLER console
            sys.stdout.write(self.run_name + ": ")
            sys.stdout.write(text_msg)

            # if run_info_is_locked:
            #     list2 = list(self.acallbacks)
            # else:
            #     with self.lock:
            #         # make a copy of list for safe enumeration 
            #         list2 = list(self.acallbacks)

            # semi-thread safe (avoid creating list under a lock for every output line)
            for i in range(len(self.acallbacks)):
                try:
                    callback = self.acallbacks[i]
                    print("sending text to callback: " + text_msg)
                    callback(self.run_name, text_msg)
                except BaseException as ex:
                    # if stream is closed unexpectly, treat as non-fatal error and just log
                    logger.exception("Error in process_run_output, ex={}".format(ex))

    def get_core_properties(self):
        dd = {"run_name": self.run_name, "workspace": self.workspace, "cmd_parts": self.cmd_parts, "run_script": self.run_script, 
            "repeat": self.repeat,  "status": self.status, "show_output": self.show_output, "repeats_remaining": self.repeats_remaining,
            "parent_name": self.parent_name}

        context = copy.copy(self.context.__dict__)
        dd["context"] = context

        return dd

    def attach(self, callback):
        self.callbacks.append(callback)       
        acallback = rpyc.async_(callback)

        # first, send recent output 
        #lines = "\n<recent output>\n\n" + "".join(self.recent_output)
        lines = "".join(self.recent_output)
        acallback(self.run_name, lines)

        # now, hook to our list of callback for next output line
        with self.lock: 
            self.acallbacks.append(acallback)           

    def detach(self, callback):
        index = None

        with self.lock:
            index = self.callbacks.index(callback)
            if index > -1:
                del self.callbacks[index]
                del self.acallbacks[index]
            else:
                errors.internal_error("could not find callback to detach")

        return index

    def update_recent_output(self, msg):
        self.recent_output.append(msg)
        if len(self.recent_output) > self.max_recent:
            self.recent_output = self.recent_output[10:]        # drop oldest 10 lines

    def wrapup_parent_prep_run(self):
        context = self.context
        store = store_from_context(context)

        store.log_run_event(context.ws, self.run_name, "parent_script_completed", {"status": self.status})  # , is_aml=self.is_aml)

    def run_wrapup(self):
        '''wrap-up the run (logging, capture)'''
        #console.print("run_wrapup, self.killed_for_restart={}".format(self.killed_for_restart))
        
        if self.mirror_worker:
            self.mirror_close_func(self)

        context = self.context
        run_name = self.run_name
        store = store_from_context(context)

        self.check_for_completed(True)

        if not self.killed_for_restart:
            # for "xt restart controller", do not log "cancelled" for runs
            # in spirit of a box that has just been preempted

            #console.print("run_wrapup: self.is_aml=", self.is_aml)
            is_parent = not (not self.repeat)

            store.wrapup_run(context.ws, run_name, context.aggregate_dest, context.dest_name, 
                status=self.status, exit_code=self.exit_code, primary_metric=context.primary_metric, 
                maximize_metric=context.maximize_metric, report_rollup=context.report_rollup, rundir=self.rundir, 
                after_files_list=context.after_files_list, after_omit_list=context.after_omit_list, log_events=context.log, 
                capture_files=context.after_upload, job_id=self.job_id, is_parent = is_parent, node_id=self.node_id, 
                run_index=self.run_index)

            if self.mri_entry:
                self.mri.mark_child_run_completed(self.mri_entry)

    def set_status(self):
        if self.killing:
            self.status = "cancelled"
        elif self.exit_code:
            self.status = "error"
        else:
            self.status = "completed"

        self.elapsed = time.time() - self.started
        #console.print("set_status: status=", self.status)

    def check_for_completed(self, wait_if_needed=False):
        result = None
        if self.process:

            # wait for process to completely terminate
            if wait_if_needed:
                console.print("waiting for process to terminate...")
                self.process.wait()

            presult = self.process.poll()
            exited = (presult != None)
            console.print("process.poll() result=", presult, ", exited=", exited)

            if exited or wait_if_needed:
                self.exit_code = self.process.wait()
                self.process = None
                self.set_status()
                result = True  # "completed (exit code=" + str(self.exit_code) + ")"
            elif self.killing:
                self.status = "dying"   
        return result

    def get_summary_stats(self):
        self.check_for_completed()
        elapsed = self.elapsed if self.elapsed else time.time() - self.started
        return "{}^{}^{}^{}".format(self.workspace, self.run_name, self.status, elapsed)

    def set_process(self, process):
        self.process = process
        self.status = "running"
        self.process_was_created = True
        console.print("set_process for {}, pid={}".format(self.run_name, self.process.pid))

    def kill(self):

        result = False
        console.print("run_info: self.status=", self.status, ", self.process=", self.process)
        before_status = self.status

        if self.process:
            result = self.check_for_completed(False)

            if not result and self.process and self.process.pid:
                self.killing = True

                # convert popen object to real Process object
                console.print("processing kill request for {}, pid={}".format(self.run_name, self.process.pid))

                # allow for "no such process" exception due to timing errors
                try:
                    p = psutil.Process(self.process.pid)

                    # since we run job in a batch file, we need to enumerate all kill
                    # all child processes
                    kids = p.children(recursive=True)
                    for kid in kids:
                        console.print("  killing CHILD process, pid=", kid.pid)
                        kid.kill()
                except psutil.NoSuchProcess as ex:
                    console.print("run={}, exception while killing process: {}".format(self.run_name, ex))

                # it may have changed async since above check 
                if self.process and self.process.pid:
                    console.print("  killing MAIN process, pid=", self.process.pid)
                    self.process.kill()
                
                result = self.check_for_completed(False)
                #self.exit_code = self.process.returncode
                #self.process = None
                #self.status = "cancelled"
                result = True   # "cancelled! (exit code=" + str(self.exit_code) + ")"
        elif self.status in ["queued", "spawning", "running"]:
            self.status = "cancelled"
            self.elapsed = time.time() - self.started

            # must call manually since it doesn't have a process exit_handler()
            self.run_wrapup()          
            result = True   
        elif self.status in ["completed", "error", "cancelled", "aborted"]:
            result = False   # nothing for us to do
        else:
            console.print("run_info.kill: unexpected status=", self.status)

        return result, self.status, before_status

