#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
import os
import sys
import json
import time
import logging
import subprocess

from xtlib.storage.store import Store
from xtlib import utils
from xtlib import file_utils
from .console import console

logger = logging.getLogger(__name__)

class TensorboardReader():
    def __init__(self, port, cwd, store_props_dict, ws_name, run_records, browse, interval):
        self.port = port
        self.ws_name = ws_name
        self.run_records = run_records
        self.browse = browse
        self.poll_interval = interval
        self.cwd = cwd

        console.set_level("normal")

        os.chdir(cwd)

        self.store = Store.create_from_props_dict(store_props_dict)
        self.print_progress = False

    def create_local_fn_from_template(self, run_record, ws_name, run_name, blob_name):
        return path

    def poll_for_tensorboard_files(self, last_changed, blob_path, start_index, tb_path, run_name):
        # get all blobs in the run's output dir
        blobs = self.store.list_blobs(self.ws_name, blob_path, return_names=False)
        download_count = 0

        #console.print("blob_names=", blob_names)
        for blob in blobs:
            # is this a tensorboard file?
            basename = os.path.basename(blob.name)
            if not basename.startswith("events.out.tfevents"):
                continue

            # get interesting part of blob's path (after run_name/)
            bn = blob.name[start_index:]
            modified = blob.properties.last_modified

            if not bn in last_changed or last_changed[bn] != modified:
                last_changed[bn] = modified

                if "{logdir}" in tb_path:

                    # extract parent dir of blob
                    test_train_node = os.path.basename(os.path.dirname(blob.name))
                    console.print("tb_path=", tb_path, ", test_train_node=", test_train_node, ", basename=", basename)

                    # apply to remaining template
                    tb_path_full = tb_path.format( **{"logdir": test_train_node} )
                    #console.print("tb_path_full=", tb_path_full)
                    local_fn = file_utils.path_join(tb_path_full, basename)
                else:
                    local_fn = tb_path

                local_fn = os.path.join("logs", local_fn)
                console.print("our local_fn=", local_fn)

                # download the new/changed blob
                try:
                    console.print("downloading bn={}, local_fn={}".format(bn, local_fn))
                    file_utils.ensure_dir_exists(file=local_fn)
                    self.store.download_file_from_run(self.ws_name, run_name, bn, local_fn)
                    download_count += 1

                    if self.print_progress:
                        console.print("d", end="", flush=True)
                except BaseException as ex:
                    logger.exception("Error in download_file_from_run, from tensorboard_reader, ex={}".format(ex))

        return download_count

    def run(self):
        console.print("XT Tensorboard Reader process (port={})".format(self.port))
        names = [rr["run"] for rr in self.run_records]
        console.print("watching runs: {}".format(", ".join(names)))
        console.print()

        #console.print(self.cwd)

        # create a tensorboard process as a DEPENDENT child process
        parts = ["tensorboard", "--port", str(self.port), "--logdir=./logs"]

        console.print("running TB cmd, parts=", parts)
        tb_process = subprocess.Popen(parts, cwd=self.cwd)

        download_count = 0 
        last_changed = {}
        poll_count = 0

        console.print("pulling down initial log files...")

        if self.browse:
            self.launch_tensorboard_url()

        while True:
            # monitor storage files by polling them for changes every poll_interval seconds
            for rr in self.run_records:
                run_name = rr["run"]
                tb_path = rr["tb_path"]
                
                #console.print("run_name=", run_name)
                for root in ["output", "mirrored"]:
                    blob_path = "runs/" + run_name + "/" + root
                    start_index = 1 + len("runs/" + run_name)

                    count = self.poll_for_tensorboard_files(last_changed, blob_path, start_index, tb_path, run_name)
                    download_count += count

            poll_count += 1
            if poll_count == 1:
                console.print("finished initial pull, now monitoring for changes every {} secs...".format(self.poll_interval))
            else:                
                if self.print_progress:
                    console.print(".", end="", flush=True)

            time.sleep(self.poll_interval)
            print(".", end="", flush=True)

    def launch_tensorboard_url(self):
        if self.browse:
            self.browse = False

            # if we open the browser too quickly, it shows a misleading subset of the runs until it refreshes 30 secs later
            # to fix this issue, use a thread so we can delay the browser launch for a few secs

            from threading import Thread

            def set_timer(timeout):
                time.sleep(timeout)

                url = "http://localhost:{}/".format(self.port)
                console.print("launching browser to url=", url)
                
                import webbrowser
                webbrowser.open(url)

                self.browse = False

            timeout = 6
            thread = Thread(target=set_timer, args=[timeout])
            thread.daemon = True    # mark as background thread
            thread.start()

def main(port, fn_run_records):

    with open(fn_run_records, "rt") as infile:
        json_text = infile.read()

    json_text = json_text.replace("'", "\"")
    pd = json.loads(json_text)

    # pd is a dict of params to pass to TensorboardReader
    reader = TensorboardReader(port=port, **pd)
    reader.run()

if __name__ == "__main__":
    main()
