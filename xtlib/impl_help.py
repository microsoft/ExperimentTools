#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# impl_help.py: implementation of XT help commands
import os
import sys
import copy
import time
import itertools

from .console import console
from .cmd_core import CmdCore
from .impl_base import ImplBase
from .qfe import command, argument, option, flag, root, example, command_help, kwgroup_help

from xtlib import qfe
from xtlib import utils
from xtlib import errors    
from xtlib import constants
from xtlib import file_utils
'''
This module implements the following commands:

     - xt                   # display XT about information
     - xt help [ <value> ]  # displays XT commands and options (value can be 'cmds', 'about', or 'api')
     - xt <command> --help
     - xt help <command> 
'''     

class ImplHelp(ImplBase):
    def __init__(self, config, store):
        super(ImplHelp, self).__init__()
        self.core = CmdCore(config, None, None)
        self.config = config
        self.mini_mode = False
        self.name = "xt"

    def set_mini_mode(self, value):
        self.mini_mode = value
        self.name = "xt"  

    def print_name_help_aligned(self, items, prefix="", separator=" ", name_field="name", help_prefix="", include_type=False, grouping_enabled=True):
        text = self.gen_name_help_aligned(items, prefix, separator, name_field, help_prefix, include_type, grouping_enabled=grouping_enabled)
        console.print(text)

    def gen_name_help_aligned(self, items, prefix="", separator=" ", name_field="name", help_prefix="", include_type=False, 
        spacer="  ", grouping_enabled=True):

        max_name_len = max(len(fi[name_field]) for fi in items if name_field in fi )

        text = ""
        kwgroups_seen = {}

        if include_type:
            max_type_len = max(len(fi["type"]) for fi in items)
        else:
            max_type_len = 0

        for fi in items:
            if not "hidden" in fi or not fi["hidden"]:
                name = fi[name_field]
                help_text = fi["help"]

                if separator:
                    name = name.replace("_", separator)

                if grouping_enabled and "kwgroup" in fi:
                    kwgroup = fi["kwgroup"]
                    if kwgroup:
                        if kwgroup in kwgroups_seen:
                            continue
                        kwgroups_seen[kwgroup] = 1
                        name = kwgroup
                        help_text = fi["kwhelp"]
                        if not help_text:
                            errors.internal_error("kwhelp must be defined for this first kwgroup member: " + fi[name_field])

                if include_type:
                    fmt = "  " + prefix + "{:<"  + str(max_name_len) + "}    {:<"  + str(max_type_len) + "}    {}"
                    text += fmt.format(name, fi["type"], help_prefix + fi["help"]) + "\n"
                else:
                    fmt = "  " + prefix + "{:<"  + str(max_name_len) + "}    {}"
                    text += fmt.format(name, help_prefix + help_text) + "\n"

                if "keywords" in fi:
                    text += fmt.format("", "--> choose one: " + ", ".join(fi["keywords"]) ) + "\n\n"

        return text

    #---- general HELP (dispatches to other functions) ----
    @argument(name="command", required=False, type="cmd", help="the command or topic to be described")
    @flag("about",  help="show information about the XT command line app")
    @flag("version",  help="display version and build information for XT")
    @flag("browse",  help="open a browser to the XT HTML doc pages")
    @flag("syntax",  help="only display the syntax of the cmd")
    @flag("args",  help="only display the syntax, arguments, and options of the cmd")
    @command(kwgroup="help", kwhelp="help commands show information about how to use XT", help="Shows information about how to run XT")
    def help(self, command, about, version, syntax, browse, args):
        '''
        The help command:
            xt help            (show list of all available commands)
            xt help topics     (show a list of help topics, or a specified topic)
            xt help internals  (show a list of XT internal help topics, or a specified topic)
            xt help <command>  (show help for a specific XT command)
        '''
        if about:
            self.help_about()
        elif version:
            self.help_version()
        elif browse:
            self.help_docs(True)
        elif command:
            if "kwgroup_name" in command:
                return self.kwgroup_help(command)
            else:
                return self.command_help(command, syntax, args)
        else:
            self.command_summary()

    #@command(kwgroup="help", help="Shows information about the XT command line program")
    def help_about(self):
        console.print()
        console.print("XT")
        console.print("  - Command line app for managing and scaling ML experiments")

        adv = "[advanced mode], " if not self.mini_mode else ""

        console.print("  - " + adv + constants.BUILD)
        console.print("  - Copyright (c) 2020, Microsoft Corporation")
        console.print("  - Developed by the AML Tools Team")
        console.print()

        console.print("XT Key Features")
        console.print("  - Scale ML experiments across multiple COMPUTE services:")
        console.print("      - local machine, VM's, Philly, Azure Batch, Azure AML")
        console.print("  - Provide a consistent STORAGE model:")
        console.print("      - workspaces, experiments, jobs, runs")
        console.print("      - blob shares")
        console.print("  - Provide related tooling:")
        console.print("      - live tensorboard, hyperparameter searching, reporting, utilities")
        console.print()

        console.print("XT Design")
        console.print("  - Backend COMPUTE service API")
        console.print("  - Azure Blob Storage (for before/after snapshots, logs, data, models)")
        console.print("  - Cosmos MongoDB database (for fast, scalable access to stats and metrics)")
        console.print("  - XT controller app running on all nodes")
        console.print()

        console.print("XT Behavior")
        console.print("  - controlled by hierarichal property settings:")
        console.print("    - master config file (readonly)")
        console.print("    - local directory config file")
        console.print("    - command line options")

    def help_docs(self, browse=False):
        url = "https://xtdocs.z22.web.core.windows.net/"

        if self.mini_mode:
            url = "https://xtdocs.z22.web.core.windows.net/"

        if browse:
            import webbrowser
            webbrowser.open(url)
        else:
            console.print("HTML docs for XT are available at: "+ url)

    @argument(name="topic", required=False, help="The help topic to display")
    @flag("browse",  help="open a browser to the specified help topic")
    @command(kwgroup="help", help="Displays the specificed help topic, or the available help topics")
    def help_topics(self, topic, browse, prefix="topics", title="help topics"):

        # build list of help topics from xtlib/help_topics directory
        topics_dir = os.path.join(file_utils.get_xtlib_dir(), "help_topics", prefix)
        if not os.path.isdir(topics_dir):
            errors.env_error("Missing help topics dir: {}".format(topics_dir))
        topic_files, _ = file_utils.get_local_filenames(topics_dir)

        # build a map from topic names to the files
        topic_map = {file_utils.root_name(fn):fn for fn in topic_files}

        if not topic:
            console.print("available {}:".format(title))
            keys = list(topic_map.keys())
            keys.sort()

            for topic_name in keys:
                console.print("  {}".format(topic_name))

            console.print()
            console.print("To display a help topic, use 'xt help topic <topic name>'")
        else:
            # print a specific topic
            topic_low = topic.lower()
            if not topic_low in topic_map:
                errors.general_error("help topic not found: {}".format(topic_low))

            text = file_utils.read_text_file(topic_map[topic_low])
            print(text)


    @argument(name="topic", required=False, help="The help topic to display")
    @flag("browse",  help="open a browser to the specified help topic")
    @command(kwgroup="help", help="Displays the specificed help topic, or the available help topics")
    def help_internals(self, topic, browse):
        self.help_topics(topic, browse, prefix="internals", title="internal help topics")

    def help_version(self):
        console.print(constants.BUILD)

    def command_summary(self):

        console.print()
        adv = "[advanced mode], " if not self.mini_mode else ""
        console.print("{} ({}{})".format(self.name.upper(), adv, constants.BUILD))
        
        console.print("Usage: {} [FLAGS] COMMAND [ARGS]...".format(self.name))
        console.print()
        
        if self.mini_mode:
            console.print("  XT is used to manage and scale ML experiments.   Most command ")
            console.print("  and option keywords can be abbreviated down to 4 letters.")
        else:
            console.print("  XT is used to manage and scale ML experiments.  Jobs can be run on:")
            console.print("  the local machine, VM's, Philly, Azure Batch, and Azure ML.")
            console.print()

            console.print("  Most command and option keywords can be abbreviated down to 4 letters.")
        #console.print()
        
        console.print("  To get help for a specific command, use '{} help <command>'".format(self.name))
        #console.print("    > xt <command> --help")
        #console.print("    > xt help <command>")
        console.print()
        #console.print()

        cmds = qfe.get_commands()

        self.assign_group_name(cmds)

        if self.mini_mode:
            cmds = list(cmds)
            console.print("Commands:")
            cmds.sort(key=lambda cmd: cmd["name"])
            self.print_name_help_aligned(cmds, grouping_enabled=False)
        else:
            # group by impl module (needs to be sorted first)
            group_key_func = lambda x: x["group"]
            cmds.sort(key=group_key_func)
            groups = itertools.groupby(cmds, group_key_func)

            for group_name, cmds in groups:
                cmds = list(cmds)
                console.print(group_name +  ":")
                cmds.sort(key=lambda cmd: cmd["name"])
                self.print_name_help_aligned(cmds)

    def gen_args(self, args, gen_docs=False):
        text = "\n"

        visible_args = [arg for arg in args if not utils.safe_value(arg, "hidden")]

        if visible_args:
            if gen_docs:
                text += "Arguments::\n\n"
            else:
                text += "Arguments:\n"
            text += self.gen_name_help_aligned(visible_args, separator="-")
            #text += "\n"
        return text

    def assign_group_name(self, cmds):
        for cmd in cmds:
            group_name = cmd["group"]

            if not group_name:
                key = cmd["func"].__module__

                if "utilities" in key:
                    group_name = "Utility commands"
                elif "help" in key:
                    # put help command in "utilities" group
                    group_name = "Utility commands"
                elif "compute" in key:
                    group_name = "Compute commands"
                elif "storage" in key:
                    group_name = "Storage commands"
                else:
                    # must be a user-defined command
                    group_name = "Utility commands"

            cmd["group"] = group_name

    def gen_options(self, orig_options, gen_docs=False):
        text = ""    
        if orig_options:       
            # make a copy since we will modify
            options = copy.deepcopy(orig_options)

            for option in options:
                if "values" in option:
                    values = option["values"]
                    if values:
                        help_text = option["help"]
                        help_text += " [one of: {}]".format(", ".join(values))
                        option["help"] = help_text

            options.sort(key=lambda option: option["name"])

            options_text = self.gen_name_help_aligned(options, prefix="--", separator="-", include_type=True)

            if options_text:
                # some non-hidden options were found
                text += "\n"
                if gen_docs:
                    text += "Options::\n\n"
                else:
                    text += "Options:\n"
                text += options_text

        return text

    def gen_inline_args(self, args):
        text = ""
        if args:
            for arg in args:
                if arg["required"]:
                    text += " <{}>".format(arg["name"])
                else:
                    text += " [{}]".format(arg["name"])        
        return text
        
    def get_formatted_doc_str(self, cmd_info):
        text = cmd_info["func"].__doc__

        if text:
            # remove 4 spaces from beginning of each line
            lines = text.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("    "):
                    line = line[4:]
                # trim end of each line
                line = line.rstrip()
                lines[i] = line

            text = "\n".join(lines)

            # remove blank lines at beginning/end
            while text.startswith("\n"):
                text = text[1:]

            while text.endswith("\n"):
                text = text[:-1]


        return text

    #---- command-specific HELP ----
    @command_help
    def command_help(self, cmd_info, syntax_only=False, args_only=False):

        show_all = not syntax_only and not args_only

        if cmd_info == "flags":
            print_flags()
            return

        '''Shows help for the specified xt command'''
        name = cmd_info["name"]

        args = cmd_info["arguments"]
        args = [arg for arg in args if not utils.safe_value(arg, "hidden")]

        options = cmd_info["options"]
        options = [opt for opt in options if not utils.safe_value(opt, "hidden")]
        
        examples = cmd_info["examples"]
        see_alsos = cmd_info["see_alsos"]
        faqs = cmd_info["faqs"]
        options_before_args = cmd_info["options_before_args"]

        words = name.replace("_", " ")
        if cmd_info["keyword_optional"]:
            words = "[ " + words + " ]"
        words = " " + words

        opts_text = ""
        if options:
            opts_text += " [OPTIONS]"

        args_text = self.gen_inline_args(args)

        if not syntax_only:
            console.print()

        if options_before_args:
            usage = "Usage: {}".format(self.name) + words + opts_text + args_text
        else:
            usage = "Usage: {}".format(self.name) + words + args_text + opts_text

        # print usage info
        console.print(usage)

        if show_all and not self.mini_mode:
            # print command help    
            doc_string = self.get_formatted_doc_str(cmd_info)

            help_text = doc_string if doc_string else "    " + cmd_info["help"]

            console.print()
            console.print(help_text)

        if syntax_only:        
            # show a quck list of options
            console.print("  OPTIONS: ", end="")
            for opt in options:
                console.print("--{} ".format(opt["name"]), end="")
            console.print()   # finish line

        else:
            # show each option on its own line with a short description
            text = ""
            if options_before_args:
                text += self.gen_options(options)
                text += self.gen_args(args)
            else:
                text += self.gen_args(args)
                text += self.gen_options(options)
            console.print(text)

        if show_all and examples:
            console.print("Examples:")
            for example in examples:
                console.print("  {}:".format(example["task"]))
                console.print("  > {}".format(example["text"]))
                console.print()

                if self.mini_mode:
                    # only show first example for mini mode
                    break

        if show_all and faqs:
            console.print("FAQs:")
            for faq in faqs:
                console.print("  {}?".format(faq["question"]))
                console.print("  => {}".format(faq["answer"]))
                console.print()

                if self.mini_mode:
                    # only show first FAQ for mini mode
                    break

        if show_all and see_alsos:
            console.print("See Also:")
            for also in see_alsos:
                text = also["text"]
                page_path = also["page_path"]

                console.print("  - {}".format(text))

    #---- kwgroup-specific HELP ----
    @kwgroup_help
    def kwgroup_help(self, cmd_dict):
        '''
        show help for a kwgroup of commands (like 'list' or 'view')
        '''
        group_name = cmd_dict["kwgroup_name"]
        
        console.print()
        console.print("{} commands:".format(group_name))

        cmds = list(cmd_dict.values())
        cmds = cmds[1:]   # skip bool entry at start
        cmds.sort(key=lambda cmd: cmd["name"])
        self.print_name_help_aligned(cmds, grouping_enabled=False)

    def generate_help_cmd(self, cmd_info):
        ''' EXAMPLE OF GENERATED TEXT:
                
            3. kill command
            ---------------

                syntax::

                    xt kill <name>

                example 1:
                    kill the run named "run23" running on the local machine::

                        > xt kill run23

                example 2: 
                    kill the run named "run28.23" running on the "vm100" box::

                        > xt kill run23 box=vm100
        '''

        name = cmd_info["name"]
        args = cmd_info["arguments"]
        options = cmd_info["options"]
        examples = cmd_info["examples"]
        see_alsos = cmd_info["see_alsos"]
        words = name.replace("_", " ")
        options_before_args = cmd_info["options_before_args"]

        if cmd_info["keyword_optional"]:
            words = "[ " + words + " ]"

        cmd_words = "xt " + words

        # begin generation
        text = ""

        # output the label (for other help pages to link to this one)
        under_name = name.replace(" ", "_")
        text += ".. _{}:  \n\n".format(under_name)


        text += "========================================\n"

        text += "{} command".format(name)
        count = len(text)

        text += "\n========================================\n\n"
        #text += "\n" + "-"*count + "\n\n"

        opts_text = ""
        if options:
            opts_text += " [OPTIONS]"

        args_text = self.gen_inline_args(args)

        # put it all TOGETHER 
        usage = "Usage::\n\n    " 

        if options_before_args:
            usage += cmd_words + opts_text + args_text
        else:
            usage += cmd_words + args_text + opts_text

        # output usage info
        text += usage + "\n\n"

        # output command help text
        text += "Description::\n\n    "

        doc_string = self.get_formatted_doc_str(cmd_info)
        help_text = doc_string if doc_string else "    " + cmd_info["help"]

        text += help_text + "\n"
        
        if options_before_args:
            text += self.gen_options(options, True)
            text += self.gen_args(args, True)
        else:
            text += self.gen_args(args, True)
            text += self.gen_options(options, True)

        if examples:
            text += "\nExamples:\n\n"
            for example in examples:
                example_text = "  {}:".format(example["task"]) + ":\n\n"
                
                # escape any backslashes
                example_text = example_text.replace("\\", "\\\\")

                # scp example uses "*", so escape it here so RST treats it literally
                example_text = example_text.replace("*", "\\*")

                example_text += "  > {}".format(example["text"]) + "\n\n"
                text += example_text

                if example["image"]:
                    img_path = example["image"]
                    text += ".. image:: {}\n".format(img_path)
                    text += "   :width: 600\n\n"

        if see_alsos:
            text += ".. seealso:: \n\n"

            for also in see_alsos:
                title = also["text"]
                page_path = also["page_path"]

                text += "    - :ref:`{} <{}>`\n".format(title, page_path) 

        return text

    @argument(name="dest-dir", help="the local directory where the files are written")
    @command(help="Shows generates RST-compatible help pages for all XT commands")
    def generate_help(self, dest_dir):
        file_utils.ensure_dir_exists(dest_dir)

        cmds = qfe.get_commands()
        count = 0

        for cmd in cmds:
            if cmd["hidden"]:
                continue

            cmd_name = cmd["name"].replace(" ", "_")

            fn = "{}/{}.rst".format(dest_dir, cmd_name)
            text = self.generate_help_cmd(cmd)

            # write text to .RST file
            with open(fn, "wt") as outfile:
                outfile.write(text)
            
            count += 1

        console.print("{} files generated to: {}".format(count, dest_dir))
