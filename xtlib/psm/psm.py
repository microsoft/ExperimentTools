#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# psm.py: pool service manager
'''
    - this file should not reference xtlib or other non-standard libraries.
    - this is to keep deployment simple: copy & run on dest machine

    - NOTE: we currently use psutil library (non-standard) that may need 
      to be installed on some systems.  is there an alternative to this?  

    - XT docs should include psutil as a prerequisite for each pool box
'''
import os
import time
import shutil
import zipfile
import datetime
import subprocess

is_windows = (os.name == "nt")
#log_print("is_windows:", is_windows)

PSM_QUEUE = os.path.expanduser("~/.xt/psm_queue")
PSM_LOGDIR = os.path.expanduser("~/.xt/psm_logs")

if is_windows:
    sys_drive = os.getenv("SystemDrive")
    CWD = os.path.join(sys_drive + "/xt", "cwd")
else:
    CWD = os.path.expanduser("~/.xt/cwd")

PSM = "psm.py"
CURRENT_RUNNING_ENTRY = "_current_running_entry_.txt"
FN_WRAPPER = os.path.join(CWD, "wrapped.bat" if is_windows else "wrapped.sh")
CONTROLLER_NAME_PATTERN = "xtlib.controller"
PY_RUN_CONTROLLER ="__run_controller__.py"

def log_print(*objects, sep=' '):
    # print to console (which is redirected to psm.log)
    text = sep.join([str(obj) for obj in objects])

    if text and not text.startswith("  "):
        # if outer level msg, add timestamp
        now = datetime.datetime.now()
        now_str = str(now).split(".")[0]
        text = "{}: {}".format(now_str, text)

    print(text, flush=True)

def get_controller_wrapped_counts():
    import psutil

    processes = psutil.process_iter()
    controller_count = 0
    wrapped_count = 0

    if is_windows:
        WRAPPED_PARTIAL = "xt\\cwd\\wrapped.bat"
    else:
        WRAPPED_PARTIAL = "xt/cwd/wrapped.sh"

    #log_print("  WRAPPED_PARTIAL: " + WRAPPED_PARTIAL)

    for p in processes:
        try:
            process_name = p.name().lower()
            #log_print("process_name=", process_name)

            if process_name.startswith("python") or "bash" in process_name:
                #log_print("process name: {}".format(p.name()))
                cmd_line = " ".join(p.cmdline())
                #log_print("  cmd_line: " + cmd_line)

                if CONTROLLER_NAME_PATTERN in cmd_line or PY_RUN_CONTROLLER in cmd_line:
                    controller_count += 1
                elif WRAPPED_PARTIAL in cmd_line:
                    wrapped_count += 1

        except BaseException as ex:
            pass
        
    return controller_count, wrapped_count

def start_async_run_detached(cmd, working_dir, fn_stdout):
    DETACHED_PROCESS = 0x00000008    # if visible else 0
    CREATE_NO_WINDOW = 0x08000000
    
    with open(fn_stdout, 'w') as output:

        if is_windows:
            cflags = CREATE_NO_WINDOW  # | DETACHED_PROCESS
            p = subprocess.Popen(cmd, cwd=working_dir, stdout=output, stderr=subprocess.STDOUT, creationflags=cflags)

        else:
            # linux
            p = subprocess.Popen(cmd, cwd=working_dir, stdout=output, stderr=subprocess.STDOUT)
    return p

def start_entry(fn_entry):
    '''
    Args:
        fn_entry: name of .zip file (w/o dir):  team.job.node.ticks.zip
    Returns:
        None
    '''

    log_print("PROCESSING: {}".format(fn_entry))
    fn_entry_path = os.path.join(PSM_QUEUE, fn_entry)

    log_print("  zapping CWD")
    shutil.rmtree(CWD)
    os.makedirs(CWD)

    # copy/remove entry from queue
    log_print("  copying entry to CWD")
    fn_current = os.path.join(CWD, "__current_entry__.zip")
    shutil.copyfile(fn_entry_path, fn_current)

    log_print("  removing entry from queue")
    os.remove(fn_entry_path)

    try:
        # UNZIP code from fn_current to CWD
        exists = os.path.exists(fn_current)
        log_print("  unzipping entry from={}, to={}, exists={}".format(fn_current, CWD, exists))

        # NOTE: this used to fail with "File is not a zip file" error (operating on partially copied file)
        with zipfile.ZipFile(fn_current, 'r') as zip:
            zip.extractall(CWD)

        # write "current job running" file
        log_print("  writing CURRENT_RUNNING_ENTRY")
        fn_current = os.path.join(CWD, CURRENT_RUNNING_ENTRY)
        with open(fn_current, "wt") as outfile:
            outfile.write(fn_entry)

        fn_wrapper = FN_WRAPPER
        if is_windows:
            # fix slashes
            fn_wrapper = fn_wrapper.replace("/", "\\")

        # extract script ARGS: node_id, run_name
        # parts: team, job, run, node, ticks, "zip"
        parts = fn_entry.split(".")
        run_name = parts[2]
        node_id = parts[3]

        if fn_wrapper.endswith(".bat"):
            cmd_parts = [fn_wrapper, node_id, run_name]
        else:
            script_part = "{} {} {}".format(fn_wrapper, node_id, run_name)
            #cmd_parts = ["bash", "--login", script_part]
            cmd_parts = ["bash", "--login", fn_wrapper, node_id, run_name]

        fn_base_entry = os.path.splitext(fn_entry)[0]
        fn_log = os.path.join(PSM_LOGDIR, fn_base_entry + ".log")

        # run PSM on remote box
        log_print("  starting ENTRY, cmd_parts={}".format(cmd_parts))
        log_print()

        start_async_run_detached(cmd_parts, ".", fn_log)

    except BaseException as ex:
        # log and move on to next entry
        log_print("  EXCEPTION processing entry: ex={}".format(ex))

def main():
    log_print("PSM starting")
    log_print()

    # ensure PSM_QUEUE exist
    if not os.path.exists(PSM_QUEUE):
        os.makedirs(PSM_QUEUE)

    # ensure PSM_LOGDIR exist
    if not os.path.exists(PSM_LOGDIR):
        os.makedirs(PSM_LOGDIR)

    last_entry_count = 0

    while True:
        time.sleep(1)

        # list queue
        files = os.listdir(PSM_QUEUE)

        # only look at .zip files (fully copied)
        files = [fn for fn in files if fn.endswith(".zip")]
        entry_count = len(files)

        # anything in queue?
        if entry_count:

            controller_count, wrapped_count = get_controller_wrapped_counts()
            
            if last_entry_count != entry_count:
                log_print("QUEUE changed (queue count={}, controller_count={}, wrapped_count={}):" \
                    .format(len(files), controller_count, wrapped_count))

                last_entry_count = entry_count

                # print queue
                for entry in files:
                    log_print("  {}".format(entry))
                log_print()

            if (controller_count + wrapped_count) == 0:
                # sort job entries by TICKS part of fn   (team.job.run.node.ticks.zip)
                files.sort( key=lambda fn: int(fn.split(".")[-2]) )

                # use oldest file (smallest tick value) to XT cwd
                fn_entry = files[0]

                # start processing oldest entry
                start_entry(fn_entry)


if __name__ == "__main__":
    main()
