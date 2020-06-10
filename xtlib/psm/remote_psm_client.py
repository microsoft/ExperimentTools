#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# remote_psm_client.py: talk to Pool State Mgr running on local machine
import os
import time
import uuid
import psutil
import shutil
import paramiko 

from xtlib import utils
from xtlib import errors
from xtlib import console
from xtlib import pc_utils
from xtlib import constants
from xtlib import file_utils
from xtlib import process_utils
from xtlib.helpers.xt_config import get_merged_config

class RemotePsmClient():
    def __init__(self, box_user_addr, box_is_windows):
        parts = box_user_addr.split("@")

        self.box_user = parts[0]
        self.box_addr = parts[1]
        self.box_is_windows = box_is_windows
        self.ssh_client = None
        self.ftp_client = None

        self.start_ssh_session()

        # expand paths on remote box
        self.home = self.run_cmd("echo $HOME").strip()
        self.psm_queue_path = self.expand_remote_path(constants.PSM_QUEUE)
        self.xt_path = self.expand_remote_path(constants.XT_HOME)
        self.cwd_path = self.expand_remote_path(constants.CWD)
        self.psm_logdir = self.expand_remote_path(constants.PSM_LOGDIR)
        self.controller_cwd = self.expand_remote_path(utils.get_controller_cwd(self.box_is_windows, is_local=False))

    def remote_file_exists(self, fn):
        exists = False
        try:
            result = self.ftp_client.stat(fn)
            exists = True
        except IOError:
            exists = False

        return exists

    def expand_remote_path(self, fn):
        fn_expand = fn.replace("~/", self.home + "/")
        return fn_expand

    def start_ssh_session(self):
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # connect
        keyfile = os.path.expanduser(constants.LOCAL_KEYPAIR_PRIVATE)

        self.ssh_client.connect(hostname=self.box_addr, username=self.box_user, 
            key_filename=keyfile, look_for_keys=True)

        self.ftp_client = self.ssh_client.open_sftp()

    def enqueue(self, team, job, run, node, fn_zip):
        # copy file to box (with unique name)
        guid = str(uuid.uuid4())
        ticks = time.time()

        # copy with ".tmp" extension so PSM doesn't see partial file
        fn_tmp_entry = "{}.{}.{}.{}.{}.tmp".format(team, job, run, node, int(10*ticks))
        fn_tmp_dest = file_utils.path_join(self.psm_queue_path, fn_tmp_entry, for_windows=False)

        fn_entry = os.path.splitext(fn_tmp_entry)[0] + ".zip"
        fn_dest = file_utils.path_join(self.psm_queue_path, fn_entry, for_windows=False)

        # don't do a confirm since PSM can remove it from queue instantly
        self.ftp_client.put(fn_zip, fn_tmp_dest)

        # now, rename the file so that PSM can see it
        self.ftp_client.rename(fn_tmp_dest, fn_dest)

        return fn_entry

    def dequeue(self, fn_entry):
        # delete entry file
        fn_dest = os.path.join(self.psm_queue_path, fn_entry)

        # if self.box_is_windows:
        #     box_cmd = "del {}".format(fn_dest)
        # else:
        #     box_cmd = "rm {}".format(fn_dest)

        #process_utils.sync_run_ssh(self, self.box_addr, box_cmd)
        self.ftp_client.remove(fn_dest)

    def enum_queue(self):
        # list contents of queue
        if self.box_is_windows:
            box_cmd = "dir {}".format(self.psm_queue_path)
        else:
            box_cmd = "ls {}".format(self.psm_queue_path)

        #exit_code, output = process_utils.sync_run_ssh(self, self.box_addr, box_cmd)
        entries = self.ftp_client.listdir(self.psm_queue_path)

        # get current entry being processed by controller
        current = self.get_running_entry_name()
        if not self._get_controller_process_id():
            current = None
        
        return entries, current

    def run_cmd(self, cmd):
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        text = stdout.read().decode()
        return text

    def _get_psm_process_id(self):
        # current code only supports linux as remote
        assert not self.box_is_windows

        # run PS on box to determine if PSM is running
        box_cmd = "ps aux | grep psm.py"
        #exit_code, output = process_utils.sync_run_ssh(self, self.box_addr, box_cmd)
        output = self.run_cmd(box_cmd)
        
        #console.print("result=\n", output)
        targets = [text for text in output.split("\n") if "python" in text]
        #console.print("targets=", targets)
        process_id = None

        if targets:
            process_id = targets[0].split("  ")[1]
        return process_id

    def _get_controller_process_id(self):
        # current code only supports linux as remote
        assert not self.box_is_windows

        # run PS on box to determine if PSM is running
        box_cmd = "ps aux | grep python"
        #exit_code, output = process_utils.sync_run_ssh(self, self.box_addr, box_cmd)
        output = self.run_cmd(box_cmd)

        #console.print("result=\n", output)
        targets = [text for text in output.split("\n") if "__run_controller__.py" in text]
        #console.print("targets=", targets)
        process_id = None

        if targets:
            process_id = targets[0].split("  ")[1]
        return process_id

    def _get_runner_script_process_id(self):
        # current code only supports linux as remote
        assert not self.box_is_windows

        # run PS on box to determine if PSM is running
        box_cmd = "ps aux | grep bash"
        #exit_code, output = process_utils.sync_run_ssh(self, self.box_addr, box_cmd)
        output = self.run_cmd(box_cmd)

        #console.print("result=\n", output)
        targets = [text for text in output.split("\n") if ".xt/cwd/wrapped.sh" in text]
        #console.print("targets=", targets)
        process_id = None

        if targets:
            process_id = targets[0].split("  ")[1]
        return process_id

    def _make_dir(self, path):
        # use SSH to list contents of queue
        if self.box_is_windows:
            box_cmd = "mkdir {}".format(path)
        else:
            box_cmd = "mkdir -p {}".format(path)

        #process_utils.sync_run_ssh(self, self.box_addr, box_cmd)
        output = self.run_cmd(box_cmd)

    def restart_psm_if_needed(self):
        '''
        processing:
            - if PSM is running on old psm.py, kill the process and restart it.  
            - if PMS is not running, start it.
        '''
        kill_needed = False
        start_needed = False

        fn_src = os.path.join(file_utils.get_my_file_dir(__file__), constants.PSM)
        fn_dest = file_utils.path_join(self.xt_path, constants.PSM, for_windows=self.box_is_windows)

        running = bool(self._get_psm_process_id())
        #print("PSM running=", running)

        if running:
            # do file contents match?
            text_src = file_utils.read_text_file(fn_src)
            text_dest = ""

            if self.remote_file_exists(fn_dest):
                # read text of fn_dest on remote box
                with self.ftp_client.open(fn_dest, "rb") as infile:
                    bytes_dest = infile.read()
                    text_dest = bytes_dest.decode()

                # normalize NEWLINE chars before comparison 
                # (ftp_client seems to add CR when called frm windows)
                text_src = text_src.replace("\r\n", "\n")
                text_dest = text_dest.replace("\r\n", "\n")

            if text_src != text_dest:
                kill_needed = True
        else:
            start_needed = True

        if kill_needed:
            p = self._get_psm_process_id()
            ssh_cmd = "kill -kill {}".format(p)
            self.run_cmd(ssh_cmd)
            start_needed = True

        if start_needed:
            # create required dirs
            self._make_dir(self.psm_queue_path)
            self._make_dir(self.cwd_path)

            # copy psm.py
            # caution: node slashes in fn_dest must all match box's OS style
            fn_dest = file_utils.fix_slashes(fn_dest, is_linux=True)
            status = self.ftp_client.put(fn_src, fn_dest)

            # run psm
            fn_log = os.path.join(self.xt_path, constants.PSMLOG)

            if self.box_is_windows:
                cmd_parts = ["cmd", "/c", "python -u {} > {}".format(fn_dest, fn_log)]
                cmd = " ".join(cmd_parts)
            else:
                fn_log = file_utils.fix_slashes(fn_log, is_linux=True)
                cmd = 'nohup bash --login -c "python -u {}" </dev/null > {} 2>&1 &'.format(fn_dest, fn_log) 
                #print("cmd=", cmd)

            #process_utils.sync_run_ssh(self, self.box_addr, cmd)
            self.run_cmd(cmd)

            for i in range(20):
                # don't return until PSM is running
                running = bool(self._get_psm_process_id())
                if running:
                    break

                time.sleep(.5)

            if not running:
                errors.general_error("Could not start remote PSM on box={}".format(self.box_addr))

    def read_file(self, fn, start_offset, end_offset):

        fn = file_utils.fix_slashes(fn, is_linux=True)

        # # leverage the read_file() function in psm.py
        # ssh_cmd = "cd ~/.xt/cwd; python -c 'import psm; psm.read_file(\"{}\", {}, {})'" \
        #     .format(fn, start_offset, end_offset)

        # error_code, read_bytes = process_utils.sync_run_ssh(None, self.box_addr, ssh_cmd, capture_as_bytes=True, report_error=False)
        new_bytes = b""

        try:
            with self.ftp_client.file(fn) as infile:
                infile.seek(start_offset)

                if end_offset:
                    new_bytes = infile.read(end_offset - start_offset) 
                else:
                    new_bytes = infile.read() 
        except BaseException as ex:
            console.diag("exception: ex={}".format(ex))

        #new_bytes = read_bytes if not error_code else b""
        return new_bytes

    def get_running_entry_name(self):
        text = None

        fn_current = file_utils.path_join(self.controller_cwd, constants.CURRENT_RUNNING_ENTRY, for_windows=False)

        new_bytes = self.read_file(fn_current, 0, None)
        text = new_bytes.decode()
        text = text.strip()         # remove newline, spaces
        return text

    def get_status(self, fn_entry):
        status = "completed"      # unless below finds different

        fn_queue_entry = file_utils.path_join(self.psm_queue_path, fn_entry, for_windows=False)
        ssh_cmd = "ls -lt " + fn_queue_entry
        result = None

        #error_code, result = process_utils.sync_run_ssh(None, self.box_addr, ssh_cmd, report_error=False)
        result = self.run_cmd(ssh_cmd)

        if result and fn_entry in result:
            status = "queued"
        else:
            text = self.get_running_entry_name()
            if text == fn_entry:
                # entry might be running; is the runner script OR controller active?
                if self._get_runner_script_process_id():
                    status = "running"
                elif self._get_controller_process_id():
                    status = "running"
                else:
                    console.print("--> runner script and controller processes not running")
            else:
                console.print("PSM current job:", text)

        return status

    def cancel(self, fn_entry):
        cancelled = False
        status = "completed"

        # don't call get_entry_status - check details JIT to minimize race conditons
        fn_queue_entry = os.path.join(self.psm_queue_path, fn_entry)

        if os.path.exists(fn_queue_entry):
            self.ftp_client.remove(fn_queue_entry)
            cancelled = True
        else:
            text = self.get_running_entry_name()
            if text == fn_entry:
                # entry might be running; is the controller active?
                process_id = self._get_controller_process_id()
                if process_id:
                    ssh_cmd = "kill -kill {}".format(process_id)
                    self.run_cmd(ssh_cmd)
                    cancelled = True

        return cancelled, status

    def read_log_file(self, fn_entry, start_offset, end_offset):
        '''
        Description:
            Each SSH call to read a file takes about 1.5 secs (too long), so
            we instead leverage   
        '''
        fn_entry_base = os.path.splitext(fn_entry)[0]
        fn_log = os.path.join(self.psm_logdir, fn_entry_base + ".log")

        new_bytes = self.read_file(fn_log, start_offset, end_offset)
        return new_bytes
