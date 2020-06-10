#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# cache_client.py: handles the caching of credehntials for the XT client
import os
import ssl
import sys
import time
import json
import socket
import logging

from xtlib import utils
from xtlib import console
from xtlib import pc_utils
from xtlib import constants
from xtlib import file_utils

logger = logging.getLogger(__name__)

HOST = '127.0.0.1'   # localhost
CACHE_SERVER_PORT = 65421  
#FN_CERT = os.path.expanduser(constants.FN_XT_CERT)

class CacheClient():
    def __init__(self):
        self.use_ssl = False

    def get_creds(self, team_name):
        cmd_dict = {"get_creds": True, "team_name": team_name}
        response = self._send_cmd_to_cache_server(cmd_dict, max_retries=1, can_start_server=False)
        return response

    def store_creds(self, team_name, creds):
        cmd_dict = {"set_creds": creds, "team_name": team_name}
        response =self._send_cmd_to_cache_server(cmd_dict, max_retries=5, can_start_server=True)
        return response

    def terminate_server(self):
        cmd_dict = {"terminate": True}
        response =self._send_cmd_to_cache_server(cmd_dict, max_retries=1, can_start_server=False)
        return response

    def _send_cmd_to_cache_server(self, cmd_dict, max_retries, can_start_server):
        # retry up to 5 secs (to handle case where XT cache server is being started)

        if True:  # os.path.exists(FN_CERT):
            # context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, capath=FN_CERT)
            # context.set_ciphers('EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH')

            for i in range(max_retries):
                try:
                    byte_buffer = json.dumps(cmd_dict).encode()

                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as normal_sock:

                        if self.use_ssl:
                            sock = context.wrap_socket(normal_sock, server_hostname=HOST, ca_certs="server.crt",
                                cert_reqs=ssl.CERT_REQUIRED)
                        else:
                            sock = normal_sock

                        sock.connect((HOST, CACHE_SERVER_PORT))

                        # send cmd_dict as bytes
                        sock.sendall(byte_buffer)

                        # read response
                        data = sock.recv(16000)
                        response = data.decode()

                        return response

                except BaseException as ex:
                    if i == 0 and can_start_server:
                        # first try failed; try starting the server
                        self._start_xt_cache_server()

                    if i > 0:
                        # we are retrying some error after trying to start the server
                        console.print(".", end="", flush=True)
                    #console.print(ex)
                    time.sleep(1)

                    # don't log this since it shows up to user as a confusing message
                    # if i == max_retries-1:
                    #     logger.exception("Error retry exceeded sending cmd to XT cache server.  Last ex={}".format(ex))

        return None

    def _start_xt_cache_server(self):

        import subprocess
        DETACHED_PROCESS = 0x00000008
        CREATE_NO_WINDOW = 0x08000000

        # launch in visible window for debugging
        MAKE_SERVER_VISIBLE = False

        xtlib_dir = os.path.dirname(__file__)
        fn_script = "{}/cache_server.py".format(xtlib_dir)
        fn_log = os.path.expanduser("~/.xt/tmp/cache_server.log")
        file_utils.ensure_dir_exists(file=fn_log)

        if MAKE_SERVER_VISIBLE:
            #subprocess.Popen(parts, cwd=".", creationflags=DETACHED_PROCESS)     
            cmd = "start python " + fn_script

            os.system(cmd) 
        elif pc_utils.is_windows():
            # run detached, hidden for WINDOWS
            parts = ["cmd", "/c", "python", fn_script]
            flags = CREATE_NO_WINDOW

            with open(fn_log, 'w') as output:
                subprocess.Popen(parts, cwd=".", creationflags=flags, stdout=output, stderr=subprocess.STDOUT) 
        else:
            # run detached, hidden for LINUX
            parts = ["python", fn_script]

            with open(fn_log, 'w') as output:
                subprocess.Popen(parts, cwd=".", stdout=output, stderr=subprocess.STDOUT) 

        # give it time to start-up and receive commands
        time.sleep(2)

