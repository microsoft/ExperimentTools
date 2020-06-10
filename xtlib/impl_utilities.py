#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# impl_utilities.py: implementation of XT utility commands
import os
import re
import sys
import copy
import time
import shutil
import logging
import yaml

from xtlib import qfe
from xtlib.console import console
from xtlib.cmd_core import CmdCore
from xtlib.helpers import xt_config
from xtlib.impl_base import ImplBase
from xtlib.helpers import file_helper
from xtlib.helpers.hexdump import hex_dump
from xtlib.helpers import yaml_dump
from xtlib.qfe import inner_dispatch, see_also
from xtlib.impl_storage_api import ImplStorageApi
from xtlib.helpers.xt_config import get_default_config_path
from xtlib.helpers.xt_config import get_default_config_template_path
from xtlib.qfe import command, argument, option, flag, root, example, command_help

from xtlib import utils
from xtlib import errors
from xtlib import pc_utils
from xtlib import constants
from xtlib import run_helper
from xtlib import file_utils
from .backends import backend_aml 
from xtlib import process_utils
from xtlib import box_information

logger = logging.getLogger(__name__)

'''
This module implements the following commands:

debugging options:
     --diagnostics <bool>                   # turn XT diagnostics msgs on/off
     --raise                                # if an exception is caught, raise it so we can see stack trace info
     --timing <bool>                        # turn XT timing msgs on/off

keypair generation and distribution:
     - xt keygen                            # generate a new keypair (calls ssh-keygen, dest = ~/.ssh/xt_id_rsa)`
     - xt keysend <box name>                # send public half of xt keypair files to specified box/pool

utility commands:
     - xt ssh <box> [ <cmd> ]               # opens a remote SSH session with specified box (or runs cmd if specified)
     - xt scp <from fn> <to fn>             # copies a file between local host and specified boxname:path
     --xt hex <file>                        # console.print contents of file in hex       
     - xt addr <box name or pool>           # display the address for the specified box(es)
     - xt config                            # view or edit the XT config file settings
     - xt config local                      # view or edit the XT local config file
     - xt version                           # display the version number and build date of XT
     - xt create demo <path>                # copy XT demo files to a specified directory
     - xt view mongo-db <run>               # show mongo-db info for a specified run
     - xt docker login                      # log docker into the Azure Container Registry from xt config file
     - xt docker logout                     # log docker out of the Azure Container Registry from xt config file
     - xt repl                              # turn on XT's REPL mode (use "repl" to toggle this off)
'''     

class ImplUtilities(ImplBase):
    def __init__(self, config, store):
        super(ImplUtilities, self).__init__()
        self.core = CmdCore(config, store, None)
        self.config = config
        self.store = store

        #self.azure_ml = backend_aml.AzureML(self.core, True)

    def prep_machine_for_controller(self):
        # download the xt cert to the CWD directory
        pass

    #---- XT ROOT FLAGS/OPTIONS ----
    @flag("help", help="Shows an overview of XT command syntax")
    @option("console", type=int, values=["none", "normal", "diagnostics", "detail"], default="$internal.console", help="sets the level of console output")
    @flag("stack-trace", default="$internal.stack-trace", help="Show stack trace when an exception is raised")
    @flag("quick-start", default="$general.quick-start", help="When true, XT startup time is reduced (experimental)")
    @flag("new", help="specifies that the current XT command should be run in a new console window")
    @flag("echo", help="echo the XT command before running it (used with --new)")
    #@flag("prep", hidden=True, help="Prepares local machine for running the XT controller")
    @root(help="callback for processing root flag detection")
    def root(self, name, value):
        #console.print("setting root name={} to value={}".format(name, value))
        if name == "help":
            pass       # will be handled later

        elif name == "console":
            console.set_level(value)

        elif name == "stack-trace":
            utils.show_stack_trace = value

        elif name == "new":
            if value and process_utils.can_create_console_window():
                cmd = qfe.current_dispatcher.dispatch_cmd
                echo_cmd = "xt " + cmd.replace("--new", "--echo", 1)

                process_utils.run_cmd_in_new_console(echo_cmd)
                errors.early_exit_without_error()

        elif name == "echo":
            if value:
                cmd = qfe.current_dispatcher.dispatch_cmd
                console.print("xt " + cmd, flush=True)

        elif name == "quick-start":
            pass       # was already handled

        elif name == "prep":
            self.prep_machine_for_controller()
            
        else:
            errors.syntax_error("unrecognized root flag=" + name)

    #---- KEYGEN command ----
    @flag("overwrite", help="When specified, any previous XT generated key will be overwritten")
    @example(task="generate a keypair for the local machine", text="xt keygen")
    @command(help="Generates an XT keypair for use in communicating with remote computers without passwords")
    def keygen(self, overwrite):
        status = self.core.keygen(overwrite)
        if status:
            console.print("key pair successfully generated.")

    #---- KEYSEND command ----
    @argument("box", default="local", type=str, help="the name of the box to send the keypair to (specify as a remote box name or address, e.g., xt keysend johnsmith@104.211.38.123)")
    @example(task="establish a keypair relationship with box 'vm10'", text="xt keysend vm10")
    @command(help="Sends the public half of the local XT keypair to the specified box (remote computer)")
    def keysend(self, box):
        # syntax: xt keysend <box name> 
        box_name = box
        if not box_name:
            errors.syntax_error("must specify a box name/address")

        info = box_information.get_box_addr(self.config, box_name, self.store)
        box_addr = info["box_addr"]

        if pc_utils.is_localhost(box_name, box_addr) or box_name == "azure-batch":
            errors.syntax_error("must specify a remote box name or address (e.g., xt keysend johnsmith@104.211.38.123")

        console.print("this will require 2 connections to the remote host, so you will be prompted for a password twice")
        status = self.core.keysend(box_name)
        if status:
            console.print("public key successfully sent.")

    #---- ZIP command ----
    @argument(name="files", help="a directory or wildcard string identifying the files to be zipped")
    @argument(name="zipfile", help="name of the zip file to be created")
    @example(task="zip up all the files in the test directory to test.zip", text="xt zip test test.zip")
    @command(help="compresses the specified files and writes them to the zip file")
    def zip(self, files, zipfile):
        filenames = file_helper.get_filenames_from_include_lists([files], [".git", "__pycache__"], recursive=True)
        count = len(filenames)
        source_dir = os.path.dirname(files)
        remove_prefix_len = 1 + len(source_dir)

        file_helper.zip_up_filenames(zipfile, filenames, True, remove_prefix_len)
        console.print("{:,} files written to: {}".format(count, zipfile))

    #---- UNZIP command ----
    @argument(name="zipfile", help="name of the zip file to be read")
    @argument(name="destination", help="the directory where the files should be unzipped")
    @example(task="unzip all files from test.zip to the 'test' direcotry", text="xt unzip test.zip test")
    @command(help="uncompress all of the files in the specified zip file to the destination directory")
    def unzip(self, zipfile, destination):
        names = file_helper.unzip_files(zipfile, destination)
        console.print("{:,} files extacted to: {}".format(len(names), destination))

    #---- WGET command ----
    @argument(name="url", help="URL of the file to be downloaded")
    @argument(name="fn-output", help="name of the local file to be created")
    @example(task="display the text for http://google.com", text="xt wget http://google.com goggle.txt")
    @command(help="download the specified file from a web URL")
    def wget(self, url, fn_output):
        import urllib.request
        
        console.print("downloading file from: {} ...".format(url))
        urllib.request.urlretrieve(url, fn_output)
        console.print("downloaded to: {}".format(fn_output))

    #---- SSH command ----
    @argument(name="name", help="the box or run name to communicate with or connect to")
    @argument(name="cmd", help="the optional command to execute", required=False, type="text", default="")
    @option(name="workspace", default="$general.workspace", help="the workspace for the runs to be displayed")
    @option(name="output", help="the name of the file to write the cmd output to")
    @example(task="initiate a remote console session with box 'vm10'", text="xt ssh vm10")
    @example(task="get a directory listing of files on box 'vm23''", text="xt ssh vm10 ls -l")
    @command(options_before_args=True, help="executes the specified command, on begins a console session, with the specified box")
    def ssh(self, name, cmd, workspace, output):
        capture_output = True if cmd else False

        if name.startswith("run"):
            # assume it's a RUN name
            # from xtlib.backends.backend_philly import Philly
            # rr = run_helper.get_run_record(self.store, workspace, name)
            # if not "cluster" in rr:
            #     errors.store_error("only philly runs are currently supported for this cmd")

            # philly = Philly(core=self.core)
            # ssh_cmd = philly.get_ssh_for_run(workspace, name)
            # print("ssh_cmd: " + ssh_cmd)
            
            # exit_code, output = process_utils.sync_run(ssh_cmd, report_error=True, capture_output=capture_output)
            pass
        else:
            # assume it's a BOX name
            info = box_information.get_box_addr(self.config, name, self.store)
            ssh_ip = info["box_addr"]

            #console.print("ssh_cmd: ssh_ip=", ssh_ip, ", cmd=", cmd)
            capture_as_bytes = bool(output)

            exit_code, ssh_output = process_utils.sync_run_ssh(self, ssh_ip, cmd, capture_output=capture_output,
                capture_as_bytes=capture_as_bytes)

        if output:
            # write as bytes
            with open(output, "wb") as outfile:
                outfile.write(ssh_output)
        elif capture_output:
            console.print(ssh_output)

    #---- SCP command ----
    @argument(name="cmd", help="the scp command to execute", type="text")
    @example(task="copy the local file 'miniMnist.py' to the outer directory of box 'vm10'", text="xt scp miniMnist.py vm10:~/")
    @example(task="copy the all *.py files from the outer directory of box 'vm10' to the local directory /zip", text="xt scp vm10:~/*.py /zip")
    @command(help="copy file(s) between the local machine and a remote box")
    def scp(self, cmd):
        # fixup the boxname:xxx patterns
        parts = cmd.split(" ")
        for i, part in enumerate(parts):
            if ":" in part:
                # remove surrounding quotes
                if part.startswith('"') and part.endswith('"'):
                    part = part[1:-1]
                elif part.startswith("'") and part.endswith("'"):
                    part = part[1:-1]

                names = part.split(":")
                if len(names) == 2 and len(names[0]) > 1:
                    # it looks like a box name
                    box_name = names[0]
                    #console.print("box_name=", box_name)

                    info = box_information.get_box_addr(self.config, box_name, self.store)
                    box_addr = info["box_addr"]

                    #console.print("box_addr=", box_addr)
                    if box_addr:
                        new_part = box_addr + ":" + ":".join(names[1:])
                        #console.print("new part=", new_part)
                        parts[i] = new_part

        #cmd = " ".join(parts).replace(": ", ":")
        #console.print("new cmd=", cmd)

        # remove empty parts
        parts = [part for part in parts if part]

        exit_code, output = process_utils.run_scp_cmd(self, parts, report_error=True)
        if output:
            console.print(output)
        else:
            console.print("SCP command completed")

    #---- HEX command ----
    @argument(name="fn", help="the file to be displayed")
    @example(task="display file file 'train.sh' in hex", text="xt hex train.sh")
    @command(help="display the context of the file as hex bytes")
    def hex(self, fn):
        if not os.path.exists(fn):
            errors.env_error("cannot open file: " + fn)

        hex_dump(fn)        

    #---- GROK command ----
    # @option(name="team", default="$general.xt-team-name", help="the team to navigate to on the XT Grok website")
    # @flag(name="browse", default=False, help="open the XT Grok URL in the browser")
    # @example(task="open XT Grok in the browser, for the 'dilbert' team", text="xt browse --team=dilbert")
    # @command(help="display or browse the XT Grok website")
    # def grok(self, team, browse):

    #     url = "https://grok.azurewebsites.net"
    #     if team:
    #         url += "/#/teams/" + team

    #     browse = browse and pc_utils.has_gui()
        
    #     if browse:
    #         import webbrowser
    #         webbrowser.open(url)
    #     else:
    #         console.print("the XT Grok url: {}".format(url))

    #---- ADDR command ----
    @argument(name="box", help="the box name to show the address for")
    @example(task="display the IP address of box 'vm10", text="xt addr vm10")
    @command(help="Shows the username/IP address for the specified box")
    def addr(self, box):
        box_name = box

        info = box_information.get_box_addr(self.config, box_name, self.store)
        box_addr = info["box_addr"]
        controller_port= info["controller_port"]
        tb_port= info["tensorboard_port"]
        
        if controller_port:
            console.print("{} address: {}, controller port={}, tensorboard port".format(box_name, box_addr, controller_port, tb_port))
        else:
            console.print("{} address: {}".format(box_name, box_addr))

    def get_prop_lines(self, all_prop_lines, prop):
        prop_lines = []
        found = False

        for pl in all_prop_lines:
            if found and (not pl.strip() or pl.strip().startswith("#")):
                break

            is_prop_start = pl.startswith("    ") and re.match('^[a-zA-Z0-9\-]+:', pl.strip()) is not None

            if is_prop_start:
                if pl.strip().startswith(prop + ":"):
                    found = True
                elif found:
                    break

            if found:
                prop_lines.append(pl)

        assert not (not prop_lines)
        return prop_lines

    def copy_sections(self, default_sections, sections):
        config_lines = []

        for section in sections:
            if "." in section:
                section, prop = section.split(".")
                all_prop_lines = default_sections[section]
                prop_lines = self.get_prop_lines(all_prop_lines, prop)
                prop_lines.append("")
            else:
                prop_lines = default_sections[section]

            config_lines.append(section + ":")
            config_lines += prop_lines

        text = "\n".join(config_lines)
        return text

    def copy_and_merge_sections(self, default_sections, sections, update_keys=None):
        if update_keys is None:
            update_keys = dict()
        new_config = dict()
        for section in sections:
            section_components = section.split(".")
            current = new_config
            current_default = default_sections
            for section_component in section_components:
                if section_component not in current and section_component != section_components[-1]:
                    current[section_component] = dict()
                elif section_component not in current and section_component == section_components[-1]:
                    current[section_component] = current_default[section_component]
                current = current[section_component]
                current_default = current_default[section_component]

        for section in update_keys.keys():
            section_components = section.split(".")
            current = new_config
            for section_component in section_components:
                if section_component == section_components[-1]:
                    current[section_component] = update_keys[section]
                current = current[section_component]

        result = yaml_dump.pretty_yaml_dump(new_config, read_only_text=False)

        return result

    def build_sections(self, lines):
        sections = {}
        props = None

        for line in lines:
            if re.match('^[a-zA-Z]+', line) is not None:
                # line starts with a letter
                name, _ = line.split(":")
                props = []
                sections[name] = props
            elif props is not None:
                props.append(line)

        return sections

    def get_config_template(self, template):
        # load default config file as lines
        fn = get_default_config_template_path()
        default_text = file_utils.read_text_file(fn)
        default_lines = default_text.split("\n")

        # convert lines to sections dict
        sections = yaml.safe_load(default_text)

        if not template or template == "empty":

            # EMPTY
            hdr = \
                "# local xt_config.yaml\n" + \
                "# uncomment the below lines to start populating your config file\n\n" 

            text = \
                "#general:\n" + \
                "    #workspace: 'ws1'\n" + \
                "    #experiment: 'exper1'\n"

        elif template == "philly":

            # PHILLY
            hdr = "# local xt_config.yaml for Philly compute service\n\n"
            text = self.copy_and_merge_sections(sections, ["external-services.philly",
                "external-services.philly-registry", "external-services.phoenixkeyvault", 
                "external-services.phoenixmongodb", "external-services.phoenixregistry",
                "external-services.phoenixstorage", "xt-services",
                "compute-targets.philly", "setups.philly", "dockers.philly-pytorch", 
                "general"], update_keys={"xt-services.target": "philly"})

        elif template == "batch":

            # BATCH
            hdr = "# local xt_config.yaml (for Azure Batch compute services)\n\n"
            text = self.copy_and_merge_sections(sections, ["external-services.phoenixbatch",
                "external-services.phoenixkeyvault", 
                "external-services.phoenixmongodb", "external-services.phoenixregistry",
                "external-services.phoenixstorage",
                "xt-services", "compute-targets.batch", "azure-batch-images",
                "general"], update_keys={"xt-services.target": "batch"})

        elif template == "aml":

            # AML 
            hdr = "# local xt_config.yaml (for Azure ML compute service)\n\n"
            text = self.copy_and_merge_sections(sections, ["external-services.phoenixaml", 
                "external-services.phoenixkeyvault", 
                "external-services.phoenixmongodb", "external-services.phoenixregistry",
                "external-services.phoenixstorage", "xt-services",
                "compute-targets.aml", "aml-options",
                "general"], update_keys={"xt-services.target": "aml"})

        elif template == "pool":

            # POOL
            hdr = "# local xt_config.yaml (for local machine and Pool compute service)\n\n"
            text = self.copy_and_merge_sections(sections, ["external-services.phoenixkeyvault", 
                "external-services.phoenixmongodb", "external-services.phoenixregistry",
                "external-services.phoenixstorage",
                "xt-services", "compute-targets.local", "compute-targets.local-docker", "boxes", "setups.local",
                "dockers.pytorch-xtlib", "dockers.pytorch-xtlib-local", "general"])

        elif template == "all":

            # ALL
            hdr = "# local xt_config.yaml (for all compute services)\n\n"
            text = "\n".join(default_lines)

        else:
            errors.syntax_error("unrecognized --create value: {}".format(template))
        
        return hdr + text

    def create_local_config_file(self, fn, template):
        # create new LOCAL file
        text = self.get_config_template(template)

        with open(fn, "w") as newfile:
            newfile.write(text)

    #---- CONFIG command ----
    #@flag(name="local", help="edit the config file in the current directory")
    @option(name="response", help="the response to use if a new config file needs to be created")
    @flag(name="default", help="specifies that the XT DEFAULT config file should be viewed as a readonly file")
    @flag(name="reset", help="the XT default config file should be reset to its original setting")
    @option(name="create", values=["philly", "batch", "aml", "pool", "all", "empty"], help="specifies that a local XT config file should be created with the specified template")
    @example(task="edit the user's local config file", text="xt config")
    @see_also("XT Config File", "xt_config_file")
    @see_also("Preparing a new project for XT", "prepare_new_project")
    @command(name="config", help="opens an editor on the user's LOCAL XT config file")
    def config_cmd(self, response, default, create, reset):
        '''
        The --create option accepts a template name to create a new local XT config file.  
        
        The currently available templates are:
            - philly   (create config file for Philly users)
            - batch    (create config file for Azure Batch users)
            - aml      (create config file for Azure Machine Learning users)
            - pool     (create config file for users running ML apps on local machines)
            - all      (create config file for users who want to have access to all backend services)
            - empty    (create an empty config file)
        '''

        if default and reset:
            xt_config.overwrite_default_config()
        else:
            if default:
                fn = get_default_config_path()
                if not os.path.exists(fn):
                    errors.env_error("the XT default config file is missing: {}".format(fn))
            else:
                fn = constants.FN_CONFIG_FILE

            edit = True

            if create:
                if os.path.exists(fn):
                    console.print("the local config file already exists: {}".format(fn))

                    answer = pc_utils.input_response("OK to overwrite?  (y/n) [n]: ", response)
                    if answer == "y":
                        self.create_local_config_file(fn, create)
                    else:
                        edit = False
                else:
                    self.create_local_config_file(fn, create)

            elif not os.path.exists(fn):
                console.print("the config file doesn't exist: {}".format(fn))

                answer = pc_utils.input_response("OK to create?  (y/n) [y]: ", response)
                if answer in ["", "y"]:
                    self.create_local_config_file(fn, "empty")
                else:
                    edit = False

            if edit:
                console.print("invoking your default .yaml editor on: {}".format(fn))
                from xtlib import process_utils 
                process_utils.open_file_with_default_app(fn)

    #---- CREATE DEMO command ----
    @argument(name="destination", help="the path in which the demo files should be created")
    @option("response", default=None, help="the response to be used to confirm the directory deletion")
    @example(task="create a set of demo files in the subdirectory xtdemo", text="xt create demo ./xtdemo")
    @flag("overwrite", help="When specified, any existing xtd-prefixed job names that match xt-demo job names will be overwritten")
    @command(help="creates a set of demo files that can be used to quickly try out various XT features")
    def create_demo(self, destination, response, overwrite):
        '''
        This command will removed the specified destination directory if it exists (prompting the user for approval).
        Specifying the current directory as the destination will produce an error.
        '''

        # set up from_dir
        from_dir = file_utils.get_xtlib_dir() + "/demo_files"

        # set up dest_dir
        dest_dir = destination
        if not dest_dir:
            errors.syntax_error("An output directory must be specified")

        create = True
        console.print("creating demo files at: {}".format(os.path.abspath(dest_dir)))

        if os.path.exists(dest_dir):
            answer = pc_utils.input_response("'{}' already exists; OK to delete? (y/n): ".format(dest_dir), response)
            if answer != "y":
                create = False

        if create:
            file_utils.ensure_dir_deleted(dest_dir)

            shutil.copytree(from_dir, dest_dir)
            #file_utils.copy_tree(from_dir, dest_dir)

            if not self.store.does_workspace_exist("xt-demo"):
                # import xt-demo workspace from archive file
                console.print("importing xt-demo workspace (usually takes about 30 seconds)")
                impl_storage_api = ImplStorageApi(self.config, self.store)

                fn_archive = os.path.join(file_utils.get_xtlib_dir(), "demo_files", "xt-demo-archive.zip")
                impl_storage_api.import_workspace(fn_archive, "xt-demo", "xtd", overwrite=overwrite, show_output=False)

    def is_aml_ws(self, ws_name):
        return self.azure_ml.does_ws_exist(ws_name)
        
    def get_registry_creds(self, compute, env):
        registry_creds = None

        if not env:
            compute_def = self.config.get_compute_def(compute)
            env = utils.safe_value(compute_def, "environment")

        if env and env != "none":
            env_def = self.config.get("dockers", env, default_value=None)
            if not env_def:
                errors.config_error("docker '{}' not found in config file".format(env))

            registry_name = env_def["registry"]

            # get REGISTRY credentials
            registry_creds = self.config.get("external-services", registry_name, suppress_warning=True)
            if not registry_creds:
                config_error("'{}' must be specified in [external-services] section of XT config file".format(registry_name))

        return registry_creds

    #---- DOCKER LOGIN command ----
    @option("docker", help="the docker environment that defines the docker registry for login")
    @option("target", default="$xt-services.target", help="one of the user-defined compute targets on which to run")
    @example(task="log user into docker", text="xt docker login")
    @command(kwgroup="docker", kwhelp="runs the specified docker command", help="logs the user into docker using docker credentials from the XT config file")
    def docker_login(self, target, docker):
        reg_creds = self.get_registry_creds(target, docker)
        if not reg_creds:
            if docker:
                errors.env_error("no dockers entry defined for docker '{}'".format(docker))
            else:
                errors.env_error("no docker property defined for target '{}'".format(target))

        server = reg_creds["login-server"]
        username = reg_creds["username"]
        password = reg_creds["password"]

        text = self.core.docker_login(server, username, password)
        console.print(text)

    #---- DOCKER LOGOUT command ----
    @option("docker", help="the docker environment that defines the docker registry for login")
    @option("target", default="$xt-services.target", help="one of the user-defined compute targets on which to run")
    @example(task="log the user out of docker", text="xt docker logout")
    @command(kwgroup="docker", help="logs the user out of docker")
    def docker_logout(self, target, docker):
        reg_creds = self.get_registry_creds(target, docker)
        server = reg_creds["login-server"]

        text = self.core.docker_logout(server)
        console.print(text)

    #---- REPL command ----
    @example(task="initiate an XT repl session", text="xt repl")
    @command(help="starts an interactive session of XT command entering and evaluation")
    def repl(self):
        while True:
            cmd = input("xt> ")
            if not cmd:
                continue

            if cmd.startswith("xt "):
                cmd = cmd[3:].strip()

            if cmd in ["exit", "close", "bye"]:
                break
            elif cmd in ["cls", "clear"]:
                #pc_utils.enable_ansi_escape_chars_on_windows_10()
                #console.print(chr(27) + "[2J")
                os.system('cls' if os.name == 'nt' else 'clear')
            else:
                args = cmd.split(" ")
                try:
                    inner_dispatch(args)
                except BaseException as ex:
                    logger.exception("Error during displatcher.dispatch, args={}".format(args))
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    errors.process_exception(exc_type, exc_value, exc_traceback, exit_app=False)


