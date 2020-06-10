#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# xt_client.py: implements client side of the controller API

import os
import json
import rpyc

from xtlib import errors
from xtlib import console
from xtlib import constants
from xtlib import file_utils

class XTClient():
    def __init__(self, config, cs, box_secret):
        self.config = config
        self.ip = cs["ip"]
        self.port = cs["port"]
        self.box_name = cs["box_name"]   
        self.box_secret = box_secret
        self.conn = None
        self.bgsrv = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        #Exception handling here
        self.close()
        
    def connect(self):
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

            self.conn = rpyc.ssl_connect(self.ip, port=self.port, keyfile=None, certfile=fn_server_public) 

            if self.conn:
                # magic step: allows our callback to work correctly!
                # this must always be executed (even if self.conn is already true)
                self.bgsrv = rpyc.BgServingThread(self.conn)
                console.diag("  now running BgServingThread")
        finally:
            # delete the CERT file
            #os.remove(fn_server_public)
            pass

        connected = not(not self.conn)
        return connected

    def ensure_connected(self):
        if not self.conn:
            errors.internal_error("XTClient is not connected")

    def restart_controller(self, delay):
        self.ensure_connected()
        result = self.conn.root.restart_controller(self.box_secret, delay)
        return result

    def get_runs(self, stage_flags=None, ws=None, run_name=None):
        status_list = self.conn.root.get_runs(self.box_secret, stage_flags, ws_name=ws, run_name=run_name)
        return status_list

    def cancel_runs(self, run_names):
        self.ensure_connected()

        # send results as json text so that we are not tied to controller (which may be killed immediately after this call)
        results_json_text = self.conn.root.cancel_run(self.box_secret, run_names)
        results = json.loads(results_json_text)
        return results

    def cancel_runs_by_property(self, prop_name, prop_value):
        self.ensure_connected()
        # send results as json text so that we are not tied to controller (which may be killed immediately after this call)
        #                             cancel_runs_by_property
        results_json_text = self.conn.root.cancel_runs_by_property(self.box_secret, prop_name, prop_value)
        results = json.loads(results_json_text)
        return results

    def get_controller_elapsed(self):
        self.ensure_connected()
        return self.conn.root.elapsed_time(self.box_secret)

    def get_controller_xt_version(self):
        self.ensure_connected()
        return self.conn.root.xt_version(self.box_secret)

    def get_controller_log(self):
        self.ensure_connected()
        return self.conn.root.controller_log(self.box_secret)

    def get_controller_ip_addr(self):
        self.ensure_connected()
        return self.conn.root.get_ip_addr(self.box_secret)

    def get_controller_concurrent(self):
        self.ensure_connected()
        return self.conn.root.get_concurrent(self.box_secret)

    def set_controller_concurrent(self, value):
        self.ensure_connected()
        self.conn.root.set_concurrent(self.box_secret, value)

    def get_status_of_runs(self, ws, run_names):
        self.ensure_connected()
        # use strings to communicate (faster than proxy objects)
        run_names_str = "^".join(run_names)
        #console.print("run_names_str=", run_names_str)
        json_status_dict = self.conn.root.get_status_of_runs(self.box_secret, ws, run_names_str)
        #console.print("json_status_dict=", json_status_dict)

        box_status_dict = json.loads(json_status_dict)

        return box_status_dict

    def get_status_of_workers(self, worker_name):
        self.ensure_connected()
        status_text = self.conn.root.get_status_of_workers(self.box_secret, worker_name)
        status_list = json.loads(status_text)

        return status_list

    def attach(self, ws_name, run_name, console_callback):
        self.ensure_connected()
        attached, status = self.conn.root.attach(self.box_secret, ws_name, run_name, console_callback)
        return attached, status

    def detach(self, ws_name, run_name, console_callback):
        self.ensure_connected()
        return self.conn.root.detach(self.box_secret, ws_name, run_name, console_callback)

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.conn_box = None

        if self.bgsrv:
            # important to stop (otherwise END OF STREAM error on exit)
            self.bgsrv.stop()
            self.bgsrv = None

