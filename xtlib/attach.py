#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# attach.py: handles the monitor-loop and attach cmd
import sys
import json
import time
import datetime

from xtlib import errors
from xtlib import console
from xtlib import pc_utils
from xtlib import constants
from .helpers.bag import Bag

from .helpers.key_press_checker import KeyPressChecker

class Attach():
    def __init__(self, xtc):
        self.xtc = xtc

    def monitor_attach_run(self, ws, run_name, show_waiting_msg=True, escape=0):
        console.print("")    # separate the waiting loop output from previous output
        attach_attempts = 0

        def monitor_work():
            nonlocal attach_attempts

            connected = self.xtc.connect()
            #azure_task_state, connected, box_name, job_id = self.connect_to_box_for_run(ws, run_name)
            azure_task_state = None
            box_name = self.xtc.box_name
            job_id = "xxxxx"   # TODO

            attach_attempts += 1

            if azure_task_state:
                #console.print("azure_task_state=", azure_task_state)
                # its an azure-batch controlled run
                if azure_task_state == "active":
                    text = "Waiting for run to start: {} ({} in azure-batch)".format(run_name.upper(), job_id)
                elif azure_task_state == "running" and not connected:
                    text = "Waiting for run to initialize: {} ({} in azure-batch)".format(run_name.upper(), job_id)
                else:
                    # exit monitor loop
                    return azure_task_state, connected, box_name, job_id, attach_attempts
            else:
                # its a normal box-controller run
                if not connected:
                    errors.env_error("could not connect to box: " + box_name)
                # we are connected, but has run started yet?
                status_dict = self.xtc.get_status_of_runs(ws, [run_name])
                # controller may not have heard of run yet (if we were fast)
                status = status_dict[run_name] if run_name in status_dict else "created"
                if status in ["created", "queued"]:
                    text = "Waiting for run to start: {} (queued to run on {})".format(run_name.upper(), box_name)
                else:
                    # status is one of running, killed, completed, spawning, ...
                    # exit monitor loop
                    return azure_task_state, connected, box_name, job_id, attach_attempts
            return text

        # wait for run to be attachable in a MONITOR LOOP
        result = monitor_loop(True, monitor_work, "[hit ESCAPE to detach] ", escape)
        #console.print("")    # separate the waiting loop output from subsequent output  

        if result:
            state, connected, box_name, job_id, attach_attempts = result
            #console.print("state=", state, ", connected=", connected, ", box_name=", box_name, ", job_id=", job_id)

            if not connected:
                if False:  #   attach_attempts == 1:
                    errors.user_exit("Unable to attach to run (state={})".format(state))
                else:
                    # not an error in this case
                    console.print("Unable to attach to run (state={})".format(state))
                    return
                    
            console.print("<attaching to: {}/{}>\n".format(ws, run_name))
            self.attach_task_to_console(ws, run_name, show_waiting_msg=show_waiting_msg, escape=escape)
        else:
            # None returned; user cancelled with ESCAPE, so no further action needed
            pass    

    def status_to_desc(self, run_name, status):
        if status == "queued":
            desc = "{} has been queued".format(run_name)
        elif status == "spawning":
            desc = "{} is spawning repeat runs".format(run_name)
        elif status == "running":
            desc = "{} has started running".format(run_name)
        elif status == "completed":
            desc = "{} has completed".format(run_name)
        elif status == "error":
            desc = "{} has terminated with an error".format(run_name)
        elif status == "cancelled":
            desc = "{} has been killed".format(run_name)
        elif status == "aborted":
            desc = "{} has been unexpectedly aborted".format(run_name)
        else:
            desc = "{} has unknown status={}".format(run_name, status)

        return "<" + desc + ">"

    def attach_task_to_console(self, ws_name, run_name, show_waiting_msg=False, show_run_name=False, escape=0):
        full_run_name = ws_name + "/" + run_name

        # callback for each console msg from ATTACHED task
        def console_callback(run_name, msg):
            if msg.startswith(constants.APP_EXIT_MSG):
                #console.print(msg)
                status = msg.split(":")[1].strip()
                desc = self.status_to_desc(run_name, status)
                console.print(desc, flush=True)
                context.remote_app_is_running = False
            else:
                if show_run_name:
                    console.print(run_name + ": " + msg, end="", flush=True)
                else:   
                    console.print(msg, end="", flush=True)
            sys.stdout.flush()

        # RPYC bug workaround - callback cannot write to variable in its context
        # but it CAN write to an object's attribute
        context = Bag()
        context.remote_app_is_running = True

        show_detach_msg = False
        detach_requested = False

        attached, status = self.xtc.attach(ws_name, run_name, console_callback)
        #console.print("attached=", attached, ", status=", status)

        if attached:
            #if show_waiting_msg:
            #    console.print("\n<attached: {}>\n".format(full_run_name))

            started = time.time()
            timeout = escape
            if timeout:
                timeout = float(timeout)
    
            try:
                with KeyPressChecker() as checker:
        
                    # ATTACH LOOP
                    #console.print("entering ATTACH WHILE LOOP...")
                    while context.remote_app_is_running:
                        #console.print(".", end="")
                        #sys.stdout.flush()

                        if checker.getch_nowait() == 27:
                            detach_requested = True
                            break

                        time.sleep(.1)

                        if timeout:
                            elapsed = time.time() - started
                            if elapsed >= timeout:
                                break


            except KeyboardInterrupt:
                detach_requested = True
            finally:
                self.xtc.detach(ws_name, run_name, console_callback)

            if detach_requested or show_waiting_msg:
                console.print("\n<detached from run: {}>".format(full_run_name))
        else:
            desc = self.status_to_desc(run_name, status)
            console.print(desc)

# flat functions

def monitor_loop(monitor, func, action_msg="monitoring ", escape_secs=0):
    '''
    set up a loop to continually call 'func' and display its output, until the ESCAPE key is pressed
    '''
    # handle the easy case first
    if not monitor:
        text = func()
        console.print(text, end="")
        return

    pc_utils.enable_ansi_escape_chars_on_windows_10()

    if monitor == True:
        monitor = 5     # default wait time
    else:
        monitor = int(monitor)
    started = datetime.datetime.now()

    started2 = time.time()
    timeout = escape_secs
    if timeout:
        timeout = float(timeout)

    last_result = None

    # MONITOR LOOP
    with KeyPressChecker() as checker:
        while True:
            result = func()
            if not isinstance(result, str):
                # func has decided to stop the monitor loop itself
                if last_result:
                    console.print("\n")
                return result

            if last_result:
                # erase last result on screen
                console.print("\r", end="")
                line_count = len(last_result.split("\n")) - 1 

                # NOTE: on some systems, the number of lines needed to be erased seems to 
                # vary by 1.  when it is too many, it destroys prevous output/commands.  until
                # this is corrected, we pick the lower values that will cause some extra
                # output on some systems.

                #line_count += 1     # add 1 for the \n we will use to clearn the line
                
                pc_utils.move_cursor_up(line_count, True)

            elapsed = utils.elapsed_time(started)
            result += "\n" + action_msg + "(elapsed time: {})...".format(elapsed)

            console.print(result, end="")
            sys.stdout.flush()
            
            if timeout:
                elapsed = time.time() - started2
                if elapsed >= timeout:
                    console.print("\nmonitor timed out")
                    break

            # wait a few seconds during refresh
            if pc_utils.wait_for_escape(checker, monitor):
                console.print("\nmonitor cancelled")
                break

            last_result = result
    return None
