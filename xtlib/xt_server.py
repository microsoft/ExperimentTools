#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
#xt_server.py: support for QUICK-START mode in XT
import socket
import time
import sys
import json
import os
import psutil
import logging

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from xtlib.cmd_core import CmdCore
from xtlib.helpers.stream_capture import StreamCapture
from xtlib.helpers.feedbackParts import feedback as fb

from xtlib import utils
from xtlib import xt_cmds
from xtlib import console
from xtlib import file_utils

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65432        # Port to listen on (non-privileged ports are > 1023)

orig_stdout = sys.stdout
logger = logging.getLogger(__name__)

class WatchWorker():
    def __init__(self, wildcard_path):
        # path = '.'
        # wildcard = "*.tfevents.*"

        wildcard_path = os.path.expanduser(wildcard_path)
        wildcard_path = wildcard_path.replace("\\", "/")

        if "*" in wildcard_path:
            path = os.path.dirname(wildcard_path)
            wildcard = os.path.basename(wildcard_path)
        else:
            path = wildcard_path
            wildcard = None

        path = file_utils.fix_slashes(path)
        #console.print("WatchWorker: path={}, wildcard={}".format(path, wildcard))

        # in case program will create dir, but it hasn't yet been created
        file_utils.ensure_dir_exists(path)

        self.event_handler = MyHandler()
        self.observer = Observer()
        #console.print("WATCHING: " + path)
        self.observer.schedule(self.event_handler, path, recursive=True)

    def get_status(self):
        status = self.event_handler.get_status()
        status["watch_dir"] = self.watch_dir
        return status

    def start(self):
        # start observer on his OWN THREAD
        self.observer.start()

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer = None

class MyHandler(FileSystemEventHandler):

    def __init__(self):
        super(MyHandler, self).__init__()
        self.last_modified = {}    # used to ignore duplicate msgs
        self.started = time.time()
        self.file_send_count = 0
        self.file_check_count = 0
        self.change_detected = False

    def get_status(self):
        elapsed = time.time() - self.started
        status = {"ws_name": self.ws_name, "run_name": self.run_name, "elapsed": elapsed, "check_count": self.file_check_count, 
            "send_count": self.file_send_count}
        return status

    def restart_and_cancel_previous(self):
        # run a 2nd copy of xt_server and have it kill this instance
        # get the process id of this process
        pid = os.getpid() 
        #console.print("launching new server; my pid=", pid) 

        # passing "pid" means kill this process when you start 
        CmdCore.start_xt_server(pid)

    def on_any_event(self, event):
        fn = event.src_path
        et = event.event_type    # 'modified' | 'created' | 'moved' | 'deleted'
        is_dir = event.is_directory

        if not self.change_detected:
            self.change_detected = True
            #console.print("detected XTLIB change: event=", event)
            time.sleep(3)           # wait 3 secs
            self.restart_and_cancel_previous()  


class StdoutRedirectToConnection():

    def __init__(self, conn):
        self.conn = conn

    def write(self, text):
        #orig_stdout.write("stdout: " + text + "\n")
        # write to conn
        data = text.encode()
        conn.sendall(data)

    def flush(self):
        pass

    def close(self):
        self.conn = None

def process_connection(conn):
    #console.print('Connected by', addr)

    sys.stdout = StdoutRedirectToConnection(conn)
    cmd_started = time.time()
    # reset timing info for new cmd or client
    # utils.set_timing_data(time.time(), True)
    # console.diag("utils.init_timing() call")

    while True:
        data = conn.recv(16000)
        if not data:
            break

        # decode command
        text = data.decode()
        cmd = json.loads(text)
        cmd_text = cmd["text"]
        cwd = cmd["cwd"]

        if orig_stdout:
            orig_stdout.write("cwd: " + cwd + ", cmd: " + cmd_text + "\n")

        # RUN command
        os.chdir(cwd)
        fb.reset_feedback()
        
        xt_cmds.main(cmd_text, cmd_started) 
        break

# main code

pid = sys.argv[1] if len(sys.argv) > 1 else None
if pid:
    pid = int(pid) 

    # kill old process before we try to own resources 
    console.print("canceling old version of server: pid=", pid)
    p = psutil.Process(pid)
    p.terminate()

    time.sleep(2)       # wait for job to fully terminate so we can access its resources

xtlib_dir = os.path.realpath(os.path.dirname(__file__))
#console.print("xtlib_dir=", xtlib_dir)

worker = WatchWorker(xtlib_dir + "/**") 
worker.start()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    console.print("waiting for client input...") 

    while True:
        conn, addr = s.accept()
        with conn:
            try:
                process_connection(conn)
            except BaseException as ex:
                logger.exception("Error during communication in xt_server, ex={}".format(ex))
                console.print("exception: " + str(ex))

