#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# client.py - cmds related to talking with the XT controller on the compute node.

'''
NOTE: the code in this module is being refactored and moved into:
    - xt_client.py
    - attach.py
    - impl_compute.py
    - cmd_core.py
'''

import os
import sys
import json
import rpyc
import time
import uuid
import arrow
import socket 
import socket 
import signal   
import psutil    
import datetime
import numpy as np
import subprocess   
from time import sleep

from .helpers.bag import Bag
from .helpers.key_press_checker import KeyPressChecker
from .helpers.feedbackParts import feedback as fb

from xtlib import utils
from xtlib import errors
from xtlib import capture 
from xtlib import scriptor
from xtlib import pc_utils
from xtlib import constants
from xtlib import file_utils
from xtlib import box_secrets
from xtlib import process_utils
from xtlib import box_information

from xtlib.storage.store import Store
from xtlib.console import console
from xtlib.backends.backend_batch import AzureBatch
from xtlib.report_builder import ReportBuilder   

# constants
SH_NAME ="xtc_run.sh"

CONTROLLER_NAME_PATTERN = "xtlib.controller"
DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000000

class Client():
    '''
    This class is responsible for talking to the XT controller (on local machine, VM's, or backend services)
    '''
    def __init__(self, config=None, store=None, core=None):
        self.config = config
        self.store = store
        self.blob_client = None     # will allocate on demand
        self.visible_for_debugging = False
        self.port = constants.CONTROLLER_PORT
        self.conn = None
        self.conn_box = None
        self.core = core
        self.token = None

    def ensure_token_is_set(self):
        # this approach no longer makes sense (we must get token from the job/node index, not the box name)
        #assert self.token
        pass

    def create_new_client(self, config):
        return Client(config, self.store, self.core)

    def get_config(self):
        return self.config

    def cancel_runs(self, run_names):
        self.ensure_token_is_set()

        # send results as json text so that we are not tied to controller (which may be killed immediately after this call)
        results_json_text = self.conn.root.cancel_run(self.token, run_names)
        results = json.loads(results_json_text)
        return results

    def cancel_runs_by_property(self, prop_name, prop_value):
        self.ensure_token_is_set()
        # send results as json text so that we are not tied to controller (which may be killed immediately after this call)
        #                             cancel_runs_by_property
        results_json_text = self.conn.root.cancel_runs_by_property(self.token, prop_name, prop_value)
        results = json.loads(results_json_text)
        return results

    def connect(self, box_name, ip_addr, port):
        self.ensure_token_is_set()

        self.conn = None
        self.conn_box = None
        
        fn_server_public= os.path.expanduser(constants.FN_SERVER_CERT_PUBLIC)
        xt_server_cert = self.config.get_vault_key("xt_server_cert")

        use_public_half = False    # cannot get the public half approach to work

        try:
            # write CERT file JIT
            if use_public_half:
                _, public_half = xt_server_cert.split("END PRIVATE KEY-----\n")
                file_utils.write_text_file(fn_server_public, public_half)
            else:
                file_utils.write_text_file(fn_server_public, xt_server_cert)

            self.conn = rpyc.ssl_connect(ip_addr, port=port, keyfile=None, certfile=fn_server_public) 
            self.conn_box = box_name
        finally:
            # delete the CERT file
            #os.remove(fn_server_public)
            pass

    def is_controller_running(self, box_name, box_addr, port=constants.CONTROLLER_PORT):
        if not port:
            port = constants.CONTROLLER_PORT
            
        # KISS: just try to connect
        is_running = False

        try:
            ip_addr = self.core.get_ip_addr_from_box_addr(box_addr)
            console.diag("  trying to connect with: ip_addr={}, port={}".format(ip_addr, port))

            self.connect(box_name, ip_addr, port=port)
            is_running = True
        except BaseException as ex:
            console.diag("  received exception: " + str(ex))
            is_running = False
            #raise ex   # uncomment to see the stack trace

        console.diag("  is_controller_running: " + str(is_running))
        return is_running

    def cancel_controller(self, box_name, os_call_only=False):
        shutdown = False

        if not os_call_only:
            try:
                # first try to cancel it thru a SHUTDOWN REQUEST
                self.ensure_token_is_set()

                info = box_information.get_box_addr(self.config, box_name, self.store)
                box_addr = info["box_addr"]

                is_running = self.is_controller_running(box_name, box_addr)
                if is_running:
                    self.conn.root.shutdown(self.token)
                    shutdown = True
            except BaseException as ex:
                console.print("shutdown request result: ex={}".format(ex))
                raise ex    

        if not shutdown:
            # if above fails, kill the process if local or PEER
            self.cancel_thru_os(box_name)

    def cancel_thru_os(self, box_name, show_progress=True):
        progress = console.print if show_progress else console.diag

        progress("  checking running processes on: " + box_name)

        is_local = pc_utils.is_localhost(box_name)
        #console.print("box_name=", box_name, ", is_local=", is_local)

        ''' kill the controller process on the specified local/remote box'''
        if is_local:  # pc_utils.is_localhost(box_name, box_addr):
            result = self.cancel_local_controller(progress)
        else:
            result = self.cancel_remote_controller(box_name, progress)

        return result

    def cancel_local_controller(self, progress):
        # LOCALHOST: check if controller is running 
        python_name = "python"  # "python.exe" if pc_utils.is_windows() else "python"

        processes = psutil.process_iter()
        cancel_count = 0

        for p in processes:
            try:
                if p.name().lower().startswith("python"):
                    console.detail("process name: {}".format(p.name()))
                    cmd_line = " ".join(p.cmdline())

                    if CONTROLLER_NAME_PATTERN in cmd_line or constants.PY_RUN_CONTROLLER in cmd_line:
                        process = p
                        process.kill()
                        progress("  controller process={} killed".format(process.pid))
                        cancel_count += 1

            except BaseException as ex:
                pass
        
        result = cancel_count > 0
        if not result:
            progress("  local XT controller not running")

        return result

    def cancel_remote_controller(self, box_name, progress):
        # REMOTE BOX: check if controller is running 
        box_addr = self.config.get("boxes", box_name, dict_key="address")
        if not box_addr:
            errors.config_error("missing address property for box: {}".format(box_name))
    
        # run PS on box to determine if controller is running
        box_cmd = "ps aux | grep controller"
        exit_code, output = process_utils.sync_run_ssh(self, box_addr, box_cmd)
        
        #console.print("result=\n", output)
        targets = [text for text in output.split("\n") if "python" in text]
        #console.print("targets=", targets)

        cancel_count = 0

        if len(targets):
            for target in targets:
                parts = target.split(" ")

                # remove empty strings
                parts = list(filter(None, parts))

                #console.print("parts=", parts)
                if len(parts) > 1:
                    pid = parts[1].strip()

                    # send "cancel" command to remote linux box
                    box_cmd = 'kill -kill {}'.format(pid)
                    progress("  killing remote process: {}".format(pid))
                    process_utils.sync_run_ssh(self, box_addr, box_cmd, report_error=True)

                    cancel_count += 1

        result = cancel_count > 0
        if not result:
            progress("  remote XT controller not running")

        return result

    def connect_to_controller(self, box_name=None, ip_addr=None, port=None):
        '''
        establish communication with the XT controller process on the specified box.
        return True if connection established, False otherwise.
        '''
        connected = False
        console.diag("init_controler: box_name={}".format(box_name))

        if self.conn == box_name:
            connected = True
        else:
            if ip_addr:
                box_addr = ip_addr
            else:
                info = box_information.get_box_addr(self.config, box_name, self.store)
                box_addr = info["box_addr"]
                controller_port = info["controller_port"]
                self.token = info["box_secret"]   
                
                ip_addr = self.core.get_ip_addr_from_box_addr(box_addr)
                port = controller_port if controller_port else constants.CONTROLLER_PORT

            # the controller should now be running - try to connect
            try:
                console.diag("  connecting to controller")
                self.connect(box_name, ip_addr, port=port)
                console.diag("  connection successful!")

                # magic step: allows our callback to work correctly!
                # this must always be executed (even if self.conn is already true)
                bgsrv = rpyc.BgServingThread(self.conn)
                console.diag("  now running BgServingThread")
                connected = True
            except BaseException as ex:
                #self.report_controller_init_failure(box_name, box_addr, self.port, ex)
                # most common reasons for failure: not yet running (backend service) or finished running
                pass

        return connected 

    def close_controller(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.conn_box = None

        
    def cancel_controller_by_boxes(self, box_list):
        for box_name in box_list:
            # connect to specified box
            self.change_box(box_name)
            self.cancel_controller(box_name)
       

    def get_tensorboard_status(self, ws_name, run_name, box_name):
        if ws_name and run_name:
            self.connect_to_box_for_run(run_name)
        else:
            self.change_box(box_name)

        # get running status from controller
        status = self.conn.root.get_tensorboard_status(self.token)            

        # add other info to status
        if not box_name:
            box_name, job_id, node_index = self.get_run_info(ws_name, run_name)

        info = box_information.get_box_addr(self.config, box_name, self.store)
        tensorboard_port = info["tensorboard_port"]
        
        status["box_name"] = box_name
        status["ip_addr"] = ip_addr
        status["tensorboard_port"] = tensorboard_port if tensorboard_port else constants.TENSORBOARD_PORT

        return status


    def set_token_from_box_secret(self, box_name):
        self.token = box_secrets.get_secret(box_name)
        assert self.token

    def change_box(self, box_name, port=None): 
        self.set_token_from_box_secret(box_name)
        self.connect_to_controller(box_name, port=port)

    def get_connection_info(self, ws, run_name):
        '''
        - get IP_ADDR, PORT, and TASK_STATE from backend service for specified:
            - run
            - job_id, node_index

            1. look up service_id for job/node in job store
            2. ci = backend.get_connect_info(service_id)
            3. use ci["port"] and ci["ip_addr"] to connect in client
        '''
        pass

    def get_run_info(self, ws_name, run_name):
        # get job_id from first log record
        box_name = None
        job_id = None
        node_index = None

        records = self.store.get_run_log(ws_name, run_name)
        dd = records[0]["data"]
        box_name = dd["box_name"]

        if utils.is_azure_batch_box(dd["box_name"]):
            # get extra info for azure-batch nodes
            job_id = dd["job_id"]
            node_index = dd["node_index"]

        return box_name, job_id, node_index

    def connect_to_box_for_run(self, ws_name, run_name):
        state = None
        box_name, job_id, node_index = self.get_run_info(ws_name, run_name)
        info = box_information.get_box_addr(self.config, box_name, self.store)
        ip_addr = info["box_addr"]
        controller_port = info["controller_port"]

        if not controller_port:
            controller_port = self.port

        if state == "deallocated":
            connected = False
        elif controller_port:
            connected = self.connect_to_controller(ip_addr=ip_addr, port=controller_port)
        else:
            connected = self.connect_to_controller(box_name=box_name)

        if controller_port:
            box_name = ip_addr + ":" + str(controller_port)
            
        return state, connected, box_name, job_id


