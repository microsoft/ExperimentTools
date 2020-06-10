#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# xt_run.py: switch between NORMAL and QUICK-START modes

# average times to invoke XT and to exit XT
INVOKE_TIME = .25
EXIT_TIME = .25

# for timing stats, capture our start_time ASAP
#console.print("starting...", flush=True)
import time
xt_start_time = time.time()
xt_start_time -= INVOKE_TIME    # adjust for average delay from xt invocation to here

import sys

import socket
import sys
import os
import json
import shlex
import logging

from xtlib import utils
from xtlib import constants
from xtlib import file_utils

from xtlib.console import console

# turn off console output until we parse our root options
console.set_level(None)
console.init_timing(sys.argv, "--timi", xt_start_time, INVOKE_TIME)

HOST = '127.0.0.1'   # localhost
PORT = 65432         # port used by the server

logger = logging.getLogger(__name__)

def run_cmd_on_server(cmd_dict, retry_count):
    byte_buffer = json.dumps(cmd_dict).encode()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))

        # send cmd_dict as bytes
        s.sendall(byte_buffer)
        first_msg = True

        # read response
        while True:
            data = s.recv(16000)
            msg = data.decode()

            if not msg:
                break

            if retry_count:
                retry_count = 0
                console.print(flush=True)

            console.print(msg, end="", flush=True)    

def main(cmd=None, disable_quickstart = False, capture_output=False, mini=False):

    utils.init_logging(constants.FN_XT_EVENTS, logger, "XT session")

    # fix artifact if no args passed, we end up with python's first arg
    if cmd:
        # treat as if it came from the shell (for consistent debugging/support)
        console.diag("orig cmd={}".format(cmd))

        # shlex and linux loses single quotes around strings, but windows does not
        orig_args = shlex.split(cmd)
        console.diag("shlex args={}".format(orig_args))
    else:
        orig_args = sys.argv[1:]
        console.diag("orig_args={}".format(orig_args))

    cmd = " ".join(orig_args)
    cmd = cmd.strip()

    use_server = "--quic" in cmd
    if not use_server:
        from .helpers.xt_config import XTConfig
        config = XTConfig(create_if_needed=True)
        use_server = config.get("general", "quick-start")

    mid_elapsed = time.time() - xt_start_time
    #console.print("mid_elapsed={:.2f}".format(mid_elapsed))
    
    if not use_server or disable_quickstart:
        # NORMAL start-up mode
        from xtlib import xt_cmds
        output = xt_cmds.main(cmd, capture_output=capture_output, mini=mini, raise_syntax_exception=False)
    else:
        # QUICK-START mode
        output = None
        log.info("using xt_server")

        import psutil

        need_start = True

        for proc in psutil.process_iter():
            try:
                # Check if process name contains the given name string.
                ptext = str(proc.cmdline())

                # if "python" in ptext:
                #     console.print(ptext)

                if "python" in ptext and "xt_server.py" in ptext:
                    need_start = False
                    break
            except BaseException as ex:
                logger.exception("Error while enumerating processes looking for xt_server, ex={}".format(ex))
                pass

        if need_start:
            from .cmd_core import CmdCore
            CmdCore.start_xt_server()

        # for now, always turn on stack traces for server-run cmd
        cmd = "--stack-trace " + cmd

        cmd_dict = {"text": cmd, "cwd": os.getcwd()}

        # retry up to 5 secs (to handle case where xt_server is being restarted)
        retry_count = 0

        for i in range(5):
            try:
                run_cmd_on_server(cmd_dict, retry_count)
                break
            except BaseException as ex:
                logger.exception("Error retry exceeded sending cmd to xt_server.  Last ex={}".format(ex))
                console.print(".", end="", flush=True)
                #console.print(ex)
                time.sleep(1)
                retry_count += 1

            
    elapsed = time.time() - xt_start_time
    #console.print("(elapsed: {:.2f} secs)".format(elapsed))

    # add adjustment for average exit time
    console.diag("end of xt_run (includes exit time={:.2f})".format(EXIT_TIME), exit_time=EXIT_TIME)

    # don't return output if we were called from xt.exe (it will console.print a confusing "[]" to output)
    return output if capture_output else None

def mini():
    main(mini=True)

if __name__ == "__main__":
    main()

