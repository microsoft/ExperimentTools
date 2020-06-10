#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# mirror_worker.py: handles mirroring of files from run box to grok server
import os
import sys
import time
import json
import logging
from fnmatch import fnmatch
import http.client
import requests
import logging

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from xtlib import utils
from xtlib import file_utils
from .console import console

logger = logging.getLogger(__name__)


class MirrorWorker():
    def __init__(self, store, run_dir, mirror_dest, wildcard_path, grok_url, ws_name, run_name):
        # path = '.'
        # wildcard = "*.tfevents.*"

        self.run_dir = run_dir

        wildcard_path = os.path.expanduser(wildcard_path)
        wildcard_path = wildcard_path.replace("\\", "/")

        if not wildcard_path.startswith("/"):
            wildcard_path = os.path.join(run_dir, wildcard_path)

        if "*" in wildcard_path:
            path = os.path.dirname(wildcard_path)
            wildcard = os.path.basename(wildcard_path)
        else:
            path = wildcard_path
            wildcard = None

        path = file_utils.fix_slashes(path)
        console.print("MirrorWorker: path={}, wildcard={}".format(path, wildcard))

        # in case program will create dir, but it hasn't yet been created
        file_utils.ensure_dir_exists(path)

        self.event_handler = MyHandler(store, mirror_dest, grok_url, ws_name, run_name, path, wildcard)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path, recursive=True)

    def get_status(self):
        status = self.event_handler.get_status()
        status["run_dir"] = self.run_dir
        return status

    def start(self):
        # start observer on his OWN THREAD
        self.observer.start()

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer = None

class MyHandler(FileSystemEventHandler):

    def __init__(self, store, mirror_dest, grok_url, ws_name, run_name, path, wildcard):
        super(MyHandler, self).__init__()

        self.store = store
        self.mirror_dest = mirror_dest
        self.grok_url = grok_url
        self.ws_name = ws_name
        self.run_name = run_name
        self.path = os.path.realpath(path)
        self.wildcard = wildcard
        self.last_modified = {}    # used to ignore duplicate msgs
        self.started = time.time()
        self.file_send_count = 0
        self.file_check_count = 0

        # don't console.print detail, fow now
        self.show_calls = False

    def get_status(self):
        elapsed = time.time() - self.started
        status = {"ws_name": self.ws_name, "run_name": self.run_name, "elapsed": elapsed, "check_count": self.file_check_count, 
            "send_count": self.file_send_count}
        return status

    def send_file_to_grok(self, fn):
        if self.show_calls:
            console.print("mirror: send_file_to_grok: fn=", fn)

        fin = open(fn, 'rb')
        files = {'file': fin}
        append = False

        # build relative path
        plen = 1 + len(self.path)
        rel_path = os.path.dirname(fn)[plen:]
        rel_path = rel_path.replace("\\", "/")

        payload = {"ws_name": self.ws_name, "run_name": self.run_name, "append": append, "rel_path": rel_path}
        console.print("mirror: payload=", payload)

        try:
            result = requests.post(url="http://" + self.grok_url + "/write_file", files=files, params=payload)
            if self.show_calls:
                console.print("mirror: POST result=", result)
            self.file_send_count += 1
        except BaseException as ex:
            logger.exception("Error in send_file_to_grok, ex={}".format(ex))
            console.print("send_file_to_grok EXCEPTION: " + str(ex))

    def send_file_to_storage(self, fn):
        append = False

        # build relative path
        plen = 1 + len(self.path)
        rel_path = fn[plen:]
        rel_path = rel_path.replace("\\", "/")

        blob_path = "mirrored/" + rel_path

        if self.show_calls:
            console.print("mirror: send_file_to_storage: fn={}, ws={}, run={}, blob_path={}".format(fn, 
                self.ws_name, self.run_name, blob_path))

        try:
            self.store.upload_file_to_run(self.ws_name, self.run_name, blob_path, fn)
            self.file_send_count += 1
        except BaseException as ex:
            logger.exception("Error in send_file_to_storage, ex={}".format(ex))
            console.print("send_file_to_grok EXCEPTION: " + str(ex))

    def on_any_event(self, event):
        fn = event.src_path
        et = event.event_type    # 'modified' | 'created' | 'moved' | 'deleted'
        is_dir = event.is_directory

        if not is_dir and et in ["modified", "created"]:
            basename = os.path.basename(fn)
            
            if not self.wildcard or fnmatch(basename, self.wildcard):

                self.file_check_count += 1

                # NOTE: watch out for multiple notifications for single change
                (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(fn)

                if (not fn in self.last_modified) or mtime != self.last_modified[fn]:
                    #console.print("last modified: %s" % time.ctime(mtime))
                    self.last_modified[fn] = mtime

                    # to make it simpler, can we check last modified time of file?
                    elapsed = time.time() - self.started
                    if self.show_calls:
                        console.print("fn={}, et={}, is_dir={}, elapsed={:.2f}".format(fn, et, is_dir, elapsed))

                    if self.mirror_dest == "grok":
                        # write file to grok server
                        self.send_file_to_grok(fn)
                    else:
                        self.send_file_to_storage(fn)
