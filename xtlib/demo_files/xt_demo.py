#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# xt_demo.py: runs a set of titled xt commands, with navigations: run/skip/back/quite
import os
import sys
import logging
import argparse

from xtlib.helpers.feedbackParts import feedback as fb
from xtlib.helpers.key_press_checker import KeyPressChecker

from xtlib import utils
from xtlib import errors
from xtlib import xt_cmds
from xtlib import pc_utils
from xtlib import file_utils
from xtlib import constants
from xtlib.helpers import xt_config

import xtlib.demo_files.commands_advanced as commands_advanced
import xtlib.demo_files.commands_basic as commands_basic

logger = logging.getLogger(__name__)

cmds = []
cmd_count = 0

ARCHIVES_DIR = "..\\xt_demo_archives"

def build_cmds(auto_mode, quick_test, nomonitor, nogui, philly=1, basic_mode=None):
    config = xt_config.get_merged_config()

    if basic_mode is None:
        mini_mode = not config.get("general", "advanced-mode")
    else:
        mini_mode = basic_mode

    is_windows = (os.name == "nt")
    has_gui = pc_utils.has_gui() and not nogui
    browse_flag = "--browse" if has_gui else ""
    browse_opt = "" if auto_mode or not has_gui else "--browse"
    timeout_opt = "--timeout=5" if auto_mode else ""
    monitor_opt = "--monitor=none " if nomonitor else ""
    templ = "{run}_{target}_lr={hparams.lr}_mo={hparams.momentum}_opt={hparams.optimizer}_tt={logdir}"

    # SET THESE before each demo (exper26 should be a multi-service set of simple runs)
    prev_exper = "exper18"
    curr_exper = "exper26"

    if mini_mode:
        command_dicts = commands_basic.get_command_dicts(
            prev_exper,
            curr_exper,
            browse_flag,
            browse_opt,
            timeout_opt,
            templ,
            ARCHIVES_DIR, 
            monitor_opt)
    else:
        command_dicts = commands_advanced.get_command_dicts(
            prev_exper,
            curr_exper,
            browse_flag,
            browse_opt,
            timeout_opt,
            templ,
            ARCHIVES_DIR,
            monitor_opt)

    if not has_gui:
        command_dicts = list(filter(
            lambda c_dict: not utils.safe_value(c_dict, "needs_gui", default=False),
            command_dicts))

    if philly == 0:
        command_dicts = [ cd for cd in command_dicts if not utils.safe_value(cd, "needs_philly", default=False) ]

    list(map(
        lambda cmd_dict: add_cmd(cmd_dict["title"], cmd_dict["xt_cmd"]),
        command_dicts
    ))


def add_cmd(title=None, xt_cmd=None, silent=False):

    title = file_utils.fix_slashes(title)
    xt_cmd = file_utils.fix_slashes(xt_cmd)

    cmd = {"title": title, "xt_cmd": xt_cmd, "silent": silent}
    cmds.append(cmd)

def wait_for_nav_key(cmd_text, auto_mode):
    print(" > " + cmd_text + " ", end="", flush=True)

    if auto_mode:
        response = "\r"
    else:
        # get KEYPRESS from user
        while True:
    
            with KeyPressChecker() as kpc:
                response = kpc.getch_wait()
                #print("getch: ord(response)={}".format(ord(response)))

                if not response or ord(response) == 0:
                    continue

            # treat control-c and ESCAPE as "q"
            if ord(response) in [3, 27]:
                response = "q"

            if response in ["\r", "\n", "s", "b", "q"]:
                break

            #print("? ", end="", flush=True)
            print("(press ENTER to run, 'q' to quit, 's' for skip, or 'b' for back)")
            print(" > " + cmd_text + " ", end="", flush=True)

    print()
    return response

def wait_for_any_key(auto_mode):
    if auto_mode:
        response = "\r"
    else:
        # get KEYPRESS from user
        while True:
            with KeyPressChecker() as kpc:
                response = kpc.getch_wait()
                break
    print()
    return response

def navigate(cmds, auto_mode, steps):
    pc_utils.enable_ansi_escape_chars_on_windows_10()
    
    index = 0
    while True:

        if index < 0:
            # keep in range (in response to user 'back')
            index = 0

        if not (1+index) in steps:
            index += 1
            if index >= len(cmds):
                break
            continue

        # show title, cmd
        cmd = cmds[index]
        cmd_text = cmd["xt_cmd"]
        silent = cmd["silent"]

        if silent:
            # don't show cmd; just execute it
            error_code = os.system(cmd_text)
            if error_code:
                errors.general_error("error code {} returned from running cmd: {}".format(error_code, cmd_text))
            index += 1
            continue

        is_windows = (os.name == "nt")

        # clear screen
        if auto_mode:
            print("======================================")
        elif is_windows:
            # windows
            os.system("cls")
        else:
            # linux - screen is inconsistent (SSH screen drawing?)
            os.system('clear')
            
        if auto_mode:
            # adjust some commands for auto mode
            if cmd_text.startswith("xt rerun"):
                cmd_text += " --response=$cmd"
            elif cmd_text.startswith("xt extract"):
                cmd_text += " --response=y"
            elif cmd_text.startswith("xt explore"):
                cmd_text += " --timeout=5"
            # elif "--open" in cmd_text:
            #     cmd_text = cmd_text.replace("--open", "")

        print("xt demo {}/{}: {}".format(index+1, len(cmds), cmd["title"]))

        response = wait_for_nav_key(cmd_text, auto_mode)
        #print("response=", response, 'b"q"=', b"q", response == b"q")

        if response in ["\r", "\n"]:
            # ---- RUN COMMAND ---- 
            if cmd_text.startswith("xt "):
                # run XT cmd internally
                fb.reset_feedback()
                xt_cmds.main(cmd_text)
            elif cmd_text.startswith("!"):
                os_cmd = cmd_text[1:]
                # treat as OS cmd
                error_code = os.system(os_cmd)
                if error_code:
                    errors.general_error("error code {} returned from running cmd: {}".format(error_code, os_cmd))
            else:
                raise Exception("internal error: unexpected cmd=", cmd_text)
            
            global cmd_count
            cmd_count += 1
            index += 1
        elif response == "s":
            print("[skip]")
            index += 1
            continue
        elif response == "b":
            print("[back]")
            index -= 1
            continue
        elif response == "q":
            print("[quit]")
            break
        else:
            print("unrecognized choice: press ENTER to run, 'q' to quit, 's' for skip, or 'b' for back")

        if index >= len(cmds):
            break

        print()
        print("hit any key to continue: ", end="", flush=True)
        response = wait_for_any_key(auto_mode)
        if response == "q":
            break

def parse_args(arg_list=None):
    # Training settings
    parser = argparse.ArgumentParser(description='XT Demo')

    parser.add_argument('--auto', action='store_true', default=False, help='runs the demo unattended')
    parser.add_argument('--nomonitor', action='store_true', default=False, help='prevents monitoring of XT run commands')
    parser.add_argument('--nogui', action='store_true', default=False, help='prevents running of GUI commands')
    parser.add_argument('--philly', default=0, type=int, help='should Philly tests be run')
    parser.add_argument('--quick-test', action='store_true', default=False, help='specifies we are running as part of the quick-test')
    parser.add_argument('--basic-mode', default=None, type=int,  help='specifies if basic or advanced mode demo should be run')
    parser.add_argument("steps", nargs="*", help="the steps to be run")

    if not arg_list:
        arg_list = sys.argv[1:]
    args = parser.parse_args(arg_list)

    print("parsed xt_demo args:", args)
    return args

def parse_steps(step_list):
    count = len(cmds)
    #print("step_list=", step_list)

    if step_list:
        steps = []
        for step in step_list:
            if "-" in step:
                low, high = step.split("-")
                low = int(low) if low else 1
                high = int(high) if high else count

                low = max(1, low)
                high = min(count, high)

                for s in range(low, high+1):
                    steps.append(s)
            else:
                step = int(step)
                step = max(1, min(count, step))
                steps.append(step)
    else:
        steps = range(1, 1+count)

    steps = list(steps)
    return steps

def main(arg_list=None):
    utils.init_logging(constants.FN_XT_EVENTS, logger, "XT Demo")

    args = parse_args(arg_list)
    auto_mode = args.auto
    nomonitor = args.nomonitor
    nogui = args.nogui
    quick_test = args.quick_test
    philly = args.philly
    basic_mode = args.basic_mode

    build_cmds(auto_mode, quick_test, nomonitor, nogui, philly=philly, basic_mode=basic_mode)

    steps = parse_steps(args.steps)
    response = "x"

    if not auto_mode:
        print()
        print("This demonstrates how to run common XT commands")
        print("Press ENTER to execute each command (or s=SKIP, b=BACK, q=QUIT)")
        print()

        print("hit any key to continue: ", end="", flush=True)
        response = wait_for_any_key(auto_mode)

        if response and response != "q" and not ord(response) in [3, 27]:
            navigate(cmds, auto_mode, steps)
    else:
        navigate(cmds, auto_mode, steps)

    # clean-up
    file_utils.ensure_dir_deleted(ARCHIVES_DIR)

    print("end of xt_demo")

    return cmd_count

if __name__ == "__main__":
    main()
