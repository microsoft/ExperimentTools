#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# process_utils.py: helper functions for starting, running processes
import os
import subprocess

from xtlib import console
from xtlib import pc_utils
from xtlib import constants
from xtlib import process_utils
from xtlib import file_utils

def sync_run(cmd_parts, capture_output=True, shell=False, report_error=False, env_vars=None, 
        capture_as_bytes=False):
    ''' this does a synchronous run of the specified cmd/app and returns the app's exitcode. It runs
    in the current working directory, but target app MUST be a fully qualified path. '''
    universal_newlines = False

    #cmd = " ".join(cmd_parts) if isinstance(cmd_parts, list) else cmd_parts
    console.diag("sync_run: {}".format(cmd_parts))
    
    # linux won't accept a command, only cmd parts
    #assert isinstance(cmd_parts, (list, tuple))
    if isinstance(cmd_parts, str):
        cmd_parts = cmd_parts.split(" ")

    if capture_output:
        process = subprocess.run(cmd_parts, cwd=".", env=env_vars, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
            universal_newlines=universal_newlines, shell=shell)

        output = process.stdout

        if not capture_as_bytes:
            if not universal_newlines:
                # since universal_newlines=False, we need to map bytes to str
                output = output.decode("utf-8", errors='backslashreplace').replace('\r', '')

            output = filter_out_verbose_lines(output)
    else:
        process = subprocess.run(cmd_parts, cwd=".", env=env_vars, shell=shell)
        output = None

    exit_code = process.returncode

    if report_error and exit_code:
        console.print(output)
        raise Exception("sync run failed, exit code={}, error={}".format(exit_code, output))

    return exit_code, output

def make_ssh_cmd_parts(box_addr, box_cmd, capture_output=True, capture_as_bytes=False):
    # "ssh -v -i ~/.ssh/xt_id_rsa {} {}".format(box_addr, box_cmd)
    ssh_parts = ["ssh"]
    if capture_output and not capture_as_bytes:
        ssh_parts.append("-v")
    ssh_parts.append("-i")
    ssh_parts.append("~/.ssh/xt_id_rsa")
    ssh_parts.append(box_addr)
    ssh_parts.append(box_cmd)
    
    return ssh_parts

def sync_run_ssh(caller, box_addr, box_cmd, report_error=True, capture_output=True, 
    capture_as_bytes=False):
    '''
    This can be used to execute a cmd on the remote box, provided that an XT key
    has previously been sent to the box with the 'xt keysend' command.

    Note:
        - we use the "-i <file>" option to send public half of keypair (avoid entering password)
        - we use the "-v" (verbose) option to avoid a "quick edit" mode non-responsive issue (avoid ENTER key pressing)
    '''

    ssh_parts = make_ssh_cmd_parts(box_addr, box_cmd, capture_output, capture_as_bytes)
    console.diag("  running SSH: " + " ".join(ssh_parts))

    exit_code, output = sync_run(ssh_parts, report_error=report_error, capture_output=capture_output, 
        capture_as_bytes=capture_as_bytes)

    console.diag("  <script completed OK>")
    return exit_code, output

'''
The following 2 functions start an asynch console app using 1 of the available "console_type" values:
    - hidden, visible, integrated (on a WINDOWS machine)
    - hidden, integrated (on a LINUX machine)
    
The "hidden" and "visible" values imply a detached console whose process life is not affected by 
the parent process dying.

Tested on WINDOWS and LINUX, 4/15/2019, rfernand2.  Machines used: "agent1" home machine (Windows 10)
and Azure VM "vm15" (Ubuntu 16.04.5 LTS).

LESSONS LEARNED in developing this code:
    - the target app name MUST be a FULLY QUALIFIED path name.
    - the target app name MUST have the "~/..." part of the path expanded into true path
    - sometimes the error "No such file or directory..." means it is try to interpret the entire cmd line as a filename
    - if using creationflags=DETACHED, you must redirect STDOUT, STDERR
    - when capturing stdout, we don't have to hold the file open (cool!)
    - if running a batch file or shell script, the stdout will NOT include the child processes.
    - the "startupinfo" information seeemed to be ignored by popen.
    - lack of good error messages/mechanisms/documentation made this process somewhat challenging
'''

def start_async_run_detached(cmd, working_dir, fn_stdout, visible=False, env_vars=None):
    DETACHED_PROCESS = 0x00000008    # if visible else 0
    CREATE_NO_WINDOW = 0x08000000
    shell = False
    is_windows = pc_utils.is_windows()
    
    if not visible and is_windows:
        # do NOT specify DETACHED_PROCESS when CREATE_WINDOW 
        cflags = CREATE_NO_WINDOW  
    elif visible and not is_windows:
        # If we are in a Linux environment then attempt to spawn
        # a gnome terminal and display output there.

        # note: this should only be called if process_utils.can_create_console_window() returns True
        shell = True
        cmd =\
            ("bash -c 'if xset q &>/dev/null; then "
             "gnome-terminal -- bash -c \"{};bash\"; "
             "else bash -c \"{}\"; fi'").format(cmd, cmd)
    else:
        cflags = DETACHED_PROCESS

    with open(fn_stdout, 'w') as output:
        if is_windows:
            p = subprocess.Popen(cmd, cwd=working_dir, env=env_vars, stdout=output, stderr=subprocess.STDOUT, creationflags=cflags)
        else:
            p = subprocess.Popen(cmd, cwd=working_dir, env=env_vars, stdout=output, stderr=subprocess.STDOUT, shell=shell)
    return p

def can_create_console_window():
    cc = False

    if pc_utils.has_gui():
    
        if pc_utils.is_windows():
            # windows 
            cc = True
        else:
            # linux
            # TODO: how do we know if this linux can create a console window?
            cc = True

    return cc

def run_cmd_in_new_console(cmd):
    if pc_utils.is_windows():
        # windows
        os.system("start cmd /K " + cmd)
    else:
        # linux
        dest_dir = os.getcwd()
        fn_log = file_utils.make_tmp_dir("console_run") + "/new_console.log"

        start_async_run_detached(cmd, os.path.expanduser(dest_dir), fn_log, visible=True)

def start_async_run_integrated(cmd, working_dir):
    subprocess.Popen(cmd, cwd=working_dir)

def open_file_with_default_app(fn):
    import os
    import shutil
    if pc_utils.is_windows():
        cmd = 'start'
    else:
        # priority order:
        # VISUAL (if VISUAL and DISPLAY are set)
        # EDITOR (if EDITOR is set)
        # vim or nano (if found in PATH)
        default = shutil.which('vim') or shutil.which('nano')
        cmd = os.environ.get('EDITOR', default)
        if 'DISPLAY' in os.environ:
            cmd = shutil.which(os.environ.get('VISUAL', cmd))
    if cmd is None:
        console.warning('no editor found')
        return
    os.system(cmd + " " + fn)

def filter_out_verbose_lines(output):
    # filter out the "debug1:" messages produced by the verbose option
    lines = output.split("\n")
    filtered_lines = []

    for line in lines:
        if line.startswith("debug1:"):
            continue
        if line.startswith("OpenSSH_for"):
            continue
        if line.startswith("Authenticated to"):
            continue
        if line.startswith("Transferred:"):
            continue
        if line.startswith("Bytes per second:"):
            continue
        filtered_lines.append(line)

    output = "\n".join(filtered_lines)
    return output

def run_scp_cmd(caller, scp_parts, report_error=True):
    # cmd = 'scp -i {} {}'.format(constants.LOCAL_KEYPAIR_PRIVATE, cmd)
    cmd_parts = ["scp", "-i", constants.LOCAL_KEYPAIR_PRIVATE] + scp_parts
    console.print("  running SCP cmd: {}".format(" ".join(cmd_parts)))

    exit_code, output = sync_run(cmd_parts)
    if report_error and exit_code:
        console.print(output)
        raise Exception("scp copy command failed")

    return exit_code, output

def scp_copy_file_to_box(caller, box_addr, fn_local, box_fn, report_error=True):
    #cmd = 'scp -i {} "{}" {}:{}'.format(constants.LOCAL_KEYPAIR_PRIVATE, fn_local, box_addr, box_fn)
    cmd_parts = ["scp", "-i", os.path.expanduser(constants.LOCAL_KEYPAIR_PRIVATE), fn_local, "{}:{}".format(box_addr, box_fn)]
    console.diag("  copying script to box; cmd={}".format(cmd_parts))

    exit_code, output = sync_run(cmd_parts)
    if report_error and exit_code:
        console.print(output)
        raise Exception("scp copy command failed: {}".format(output))

    return exit_code, output

def make_launch_parts(prefix, parts):
    if prefix:
        parts = prefix.split(" ") + parts

    return parts

def make_launch_cmd(prefix, cmd, is_script=True):
    if prefix:
        if is_script:
            cmd = prefix + " " + cmd
        else:
            cmd = prefix + "-c '" + cmd + "'"

    return cmd
