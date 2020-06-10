#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# cache_server.py: caches creds on XT client machine
import os
import ssl
import sys
import time
import json
import socket
import logging

from xtlib import utils
from xtlib import console
from xtlib import constants
from xtlib import file_utils

logger = logging.getLogger(__name__)

HOST = '127.0.0.1'   # localhost
CACHE_SERVER_PORT = 65421   
#FN_CERT = os.path.expanduser(constants.FN_XT_CERT)

class CacheServer():
    def __init__(self):
        self.creds = {}
        self.terminate = False
        self.use_ssl = False

    def listen_for_commands(self):
        # if not os.path.exists(FN_CERT):
        #     errors.internal_error("cert file is missing: " + FN_CERT)

        # context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH, capath=FN_CERT)
        # context.set_ciphers('EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH')

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as normal_sock:

            if self.use_ssl:
                sock = context.wrap_socket(normal_sock, server_hostname=HOST, ca_certs="server.crt",
                    cert_reqs=ssl.CERT_REQUIRED)
            else:
                sock = normal_sock

            # Free up the port for reuse if the process is killed
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            sock.bind((HOST, CACHE_SERVER_PORT))
            sock.listen()
            console.print("waiting for client input...") 

            while not self.terminate:
                conn, addr = sock.accept()
                with conn:
                    try:
                        self.process_connection(conn)
                    except BaseException as ex:
                        logger.exception("Error during communication in xt_server, ex={}".format(ex))
                        console.print("exception: " + str(ex))    

    def process_connection(self, conn):

        console.print("new connection established")

        data = conn.recv(16000)
        #console.print("data=", data)

        if data:
            # decode command
            text = data.decode()
            cd = json.loads(text)
            team_name = cd["team_name"] if "team_name" in cd else None
            
            first_key = next(iter(cd))
            console.print("cmd: {}".format(first_key))

            if "get_creds" in cd:
                response = self.creds[team_name]
            elif "set_creds" in cd:
                self.creds[team_name] = cd["set_creds"]
                response = "OK"
            elif "terminate" in cd:
                self.terminate = True
                response = "OK"
            else:
                error.internal_error("unrecognized cmd received by xt_cache_server: {}".format(cd))

            byte_buff = response.encode()
            conn.send(byte_buff)
# MAIN
cache_server = CacheServer()
cache_server.listen_for_commands()

