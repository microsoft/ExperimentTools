#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# qfe: a quick-front-end builder for XT 
import os
import sys
import functools

from xtlib.console import console
from xtlib.helpers.scanner import Scanner

from xtlib import utils
from xtlib import errors

'''
Definitions:
    argument - a postional, unnamed parameter; can be optional iif it last argument
    option   - a non-positional, named parameter; can be optional or required
    flag     - a non-positional, named parameter without a value, or with a 1, 0 value

Root:
    options can be added to the main() function with a "root=True" parameter.  This
    will be they can be accepted for any command.
'''

# structure that is used for storing all cmd_info's and
# for locating a cmd_info one word at a time
commands = {}               # nested dictionary, each level index by next command keyword
commands_by_name = {}       # key = function name
current_dispatcher = None

# special cmd_info's and funcs
root_cmd_info = None
current_cmd_info = None         # for command function being defined as function decorators are processed
parser_cmd_info = None          # the command being parsed or dispatched
command_help_func = None
kwgroup_help_func = None
explict_options = {}

# debugging flags
debug_decorators = False
first_command = True

def is_xt_object(name):
   if name.startswith("run") and name[3:].replace('.','',1).isdigit():
      match = True
#    elif name.startswith("job") and name[3:].isdigit():
#       match = True
   else:
      match = False

   return match

def get_xt_objects_from_cmd_piping():
    objects = []

    if not os.isatty(0):
        # command line piping
        for line in sys.stdin:
            tokens = line.split()
            tokens = [tok for tok in tokens if is_xt_object(tok)]
            if tokens:
                objects.append(tokens[0])

    return objects

pipe_object_list = None   

# testing
#pipe_object_list= ['run2122', 'run2123', 'run2124']

def inner_dispatch(args, is_rerun=False):
    current_dispatcher.dispatch(args, is_rerun)

def get_dispatch_cmd():
    return current_dispatcher.get_dispatch_cmd() if current_dispatcher else None

def get_command_by_words(words):
    dd = commands
    for word in words:
        dd = dd[word]

    if not "" in dd:
        errors.general_error("command not found: " + " ".join(words))

    cmd_info = dd[""]
    return cmd_info

def get_root_command():
    return root_cmd_info

def build_commands():
    '''
    we return as a dict with key=func because:
        - it automatically eliminate the duplicate caused by keyword_optional 
        - enables caller to quickly access command by name
    '''
    func_dict = {}
    get_commands_from(commands, func_dict)

    return func_dict

def remove_hidden_commands():
    # remove hidden commands from commnds_by_name
    global commands_by_name
    commands_by_name = {name:cmd for name,cmd in commands_by_name.items() if not cmd["hidden"]}

    # rebuild commands from commands_by_name
    ddx = {}
    for _, cmd in commands_by_name.items():
        cmd_name = cmd["name"]

        # add cmd keywords to dd
        dd = ddx
        for name_part in cmd_name.split(" "):
            if name_part not in dd:
                dd[name_part] = {}
            dd = dd[name_part]

        dd[""] = cmd

    global commands
    commands = ddx

def get_commands_from(dd, func_dict):
    for key, value in dd.items():
        if key:
            get_commands_from(value, func_dict)
        else:
            func_name = value["func"].__name__
            func_dict[func_name] = value

def update_or_insert_argument(cmd_info, list_name, new_arg):
    new_name = new_arg["name"]
    args = cmd_info[list_name]
    names = [arg["name"] for arg in args]

    if new_name in names:
        # replace existing entry
        cmd_info[list_name] = [(new_arg if arg["name"] == new_name else arg) for arg in args ]
    else:
        # insert new entry at beginning
        args.insert(0, new_arg)

# COMMAND_HELP decorator processor
def command_help(func):
    global command_help_func
    command_help_func = func
    return func

# KWGROUP_HELP decorator processor
def kwgroup_help(func):
    global kwgroup_help_func
    kwgroup_help_func = func
    return func

# ROOT decorator processor
def root(help=""):
    '''
    builds the root_cmd_info entry, mostly to track root options.
    '''
    def decorator_root(func):
        @functools.wraps(func)
        def wrapper_root(*args, **kwargs):
            return func(*args, **kwargs)

        # begin actual decorater processing
        if debug_decorators:
            console.print("root decorator called, func=", func.__name__)

        global root_cmd_info, current_cmd_info
        root_cmd_info =  {"name": func.__name__, "func": func, "arguments": [], "options": [], "help": help}
        current_cmd_info = root_cmd_info
        # end actual decorater processing

        return wrapper_root
    return decorator_root

# COMMAND decorator processor
def command(name=None, group=None, kwgroup=None, kwhelp=None, options_before_args=False, keyword_optional=False, pass_by_args=False, help=""):
    '''
    builds a nested dictionary of name parts for multi-word commands 
    and their associated functions.
    '''

    def decorator_command(func):
        @functools.wraps(func)
        def wrapper_command(*args, **kwargs):
            return func(*args, **kwargs)

        # begin actual decorater processing
        global first_command
        if first_command:
            first_command = False
            #   console.diag("processing first cmd decorator")
            #console.print("first command...")

        if name:
            cmd_name = name
        else:
            cmd_name = func.__name__.replace("_", " ")

        if debug_decorators:
            console.print("command decorator called, func=", func.__name__)
        dd = commands

        for name_part in cmd_name.split(" "):
            if name_part not in dd:
                dd[name_part] = {}
            dd = dd[name_part]

        cmd_info =  {"name": cmd_name, "options_before_args": options_before_args, "keyword_optional": keyword_optional, "pass_by_args": pass_by_args, 
            "group": group, "func": func, "arguments": [], "options": [], "examples": [], "faqs": [], "hidden": False, "see_alsos": [],
            "kwgroup": kwgroup, "kwhelp": kwhelp, "help": help}

        dd[""] = cmd_info

        if keyword_optional:
            # only 1 command can use this
            if "" in commands:
                errors.internal_error("processing command decoration for '{}'; only 1 command can use 'keyword_optional'".format(func.__name__))
            commands[""] = cmd_info

        global current_cmd_info
        current_cmd_info = cmd_info
        # end actual decorater processing

        return wrapper_command
    return decorator_command

    #console.print("command decorator called, func=", func.__name__)
    #return func

# ARGUMENT decorator processor
def argument(name, required=True, type=str, help="", default=None):
    def decorator_argument(func):
        @functools.wraps(func)
        def wrapper_argument(*args, **kwargs):
            return func(*args, **kwargs)

        if debug_decorators:
            console.print("argument decorator called, name=", name, ", func=", func.__name__)

        global current_cmd_info
        if not current_cmd_info:
            errors.internal_error("@argument decorators must be followed by a single @command decorator")

        type_name = type if isinstance(type, str) else type.__name__
        arg_info = {"name": name, "required": required, "type": type_name, "help": help, "default": default}

        #current_cmd_info["arguments"].insert(0, arg_info)
        update_or_insert_argument(current_cmd_info, "arguments", arg_info)

        return wrapper_argument

    return decorator_argument

# ARGUMENT decorator processor
def keyword_arg(name, keywords, required=True, type=str, help="", default=None):
    def decorator_keyword_arg(func):
        @functools.wraps(func)
        def wrapper_keyword_arg(*args, **kwargs):
            return func(*args, **kwargs)

        if debug_decorators:
            console.print("keyword_arg decorator called, name=", name, ", func=", func.__name__)

        global current_cmd_info
        if not current_cmd_info:
            errors.internal_error("@keyword_arg decorators must be followed by a single @command decorator")

        type_name = type if isinstance(type, str) else type.__name__
        arg_info = {"name": name, "keywords": keywords, "required": required, "type": type_name, "help": help, "default": default}

        #current_cmd_info["keyword_args"].insert(0, arg_info)
        update_or_insert_argument(current_cmd_info, "arguments", arg_info)

        return wrapper_keyword_arg

    return decorator_keyword_arg

# OPTION decorator processor
def option(name, default=None, required=None, multiple=False, type=str, values=None, help=""):
    '''
    params:
        multiple: when True, user can specify this option multiple times and values will accumulate (list of strings)
        values: if values are specified, the value of this option must be set to one of these keyword values
    '''
    def decorator_option(func):
        @functools.wraps(func)
        def wrapper_option(*args, **kwargs):
            return func(*args, **kwargs)

        if debug_decorators:
            console.print("option decorator called, name=", name, ", func=", func.__name__)

        global current_cmd_info
        if not current_cmd_info:
            errors.internal_error("@option decorators must be followed by a single @command decorator")

        type_name = type if isinstance(type, str) else type.__name__
        option_info = {"name": name, "hidden": False, "required": required, "type": type_name, "multiple": multiple, 
            "default": default, "values": values, "help": help}
        
        #current_cmd_info["options"].append(option_info)
        update_or_insert_argument(current_cmd_info, "options", option_info)

        return wrapper_option

    return decorator_option
 
def hidden(name, default=None, type=str, help=""):
    def decorator_hidden(func):
        @functools.wraps(func)
        def wrapper_hidden(*args, **kwargs):
            return func(*args, **kwargs)

        if debug_decorators:
            console.print("hidden decorator called, name=", name, ", func=", func.__name__)

        global current_cmd_info
        if not current_cmd_info:
            errors.internal_error("@hidden decorators must be followed by a single @command decorator")

        # a hidden is really just a hidden option
        type_name = type if isinstance(type, str) else type.__name__
        option_info = {"name": name, "hidden": True, "type": type_name, "default": default, "help": help}
        
        #current_cmd_info["hiddens"].append(hidden_info)
        update_or_insert_argument(current_cmd_info, "options", option_info)

        return wrapper_hidden

    return decorator_hidden

# FLAG decorator processor  
def flag(name, default=None, help=""):
    def decorator_flag(func):
        @functools.wraps(func)
        def wrapper_flag(*args, **kwargs):
            return func(*args, **kwargs)

        if debug_decorators:
            console.print("flag decorator called, name=", name, ", func=", func.__name__)

        global current_cmd_info, root_cmd_info

        # a flag is really just a type=flag option
        option_info = {"name": name, "hidden": False, "type": "flag", "multiple": False, "default": default, "help": help}
        if not current_cmd_info:
            errors.internal_error("@flag decorators must be followed by a single @command or @root decorator")

        update_or_insert_argument(current_cmd_info, "options", option_info)

        return wrapper_flag

    return decorator_flag

# EXAMPLE decorator processor  
def example(text, task="", image=None):
    def decorator_example(func):
        @functools.wraps(func)
        def wrapper_example(*args, **kwargs):
            return func(*args, **kwargs)

        if debug_decorators:
            console.print("example decorator called, name=", name, ", func=", func.__name__)

        global current_cmd_info, root_cmd_info

        example_info = {"text": text, "task": task, "image": image}
        if not current_cmd_info:
            errors.internal_error("@example decorators must be followed by a single @command or @root decorator")

        #console.print("setting example name=", name)
         
        current_cmd_info["examples"].insert(0, example_info)
        return wrapper_example

    return decorator_example

# SEE ALSO decorator processor  
def see_also(text, page_path=""):
    def decorator_see_also(func):
        @functools.wraps(func)
        def wrapper_see_also(*args, **kwargs):
            return func(*args, **kwargs)

        if debug_decorators:
            console.print("see_also decorator called, name=", name, ", func=", func.__name__)

        global current_cmd_info, root_cmd_info

        see_also_info = {"text": text, "page_path": page_path}
        if not current_cmd_info:
            errors.internal_error("@see_also decorators must be followed by a single @command or @root decorator")

        #console.print("setting see_also name=", name)
         
        current_cmd_info["see_alsos"].insert(0, see_also_info)
        return wrapper_see_also

    return decorator_see_also

# FAW decorator processor  
def faq(question, answer):
    def decorator_faq(func):
        @functools.wraps(func)
        def wrapper_faq(*args, **kwargs):
            return func(*args, **kwargs)

        if debug_decorators:
            console.print("faq decorator called, name=", name, ", func=", func.__name__)

        global current_cmd_info, root_cmd_info

        faq_info = {"question": question, "answer": answer}
        if not current_cmd_info:
            errors.internal_error("@faq decorators must be followed by a single @command or @root decorator")

        #console.print("setting faq name=", name)
         
        current_cmd_info["faqs"].insert(0, faq_info)
        return wrapper_faq

    return decorator_faq

# CLONE decorator processor  
def clone(source, arguments=True, options=True):
    def decorator_clone(func):
        @functools.wraps(func)
        def wrapper_clone(*args, **kwargs):
            return func(*args, **kwargs)

        if debug_decorators:
            console.print("clone decorator called, source=", source, ", func=", func.__name__)

        global current_cmd_info, root_cmd_info

        if not current_cmd_info:
            errors.internal_error("@clone decorators must be followed by a single @command or @root decorator")

        source_cmd_info = get_command_by_words(source.split("_"))

        if arguments:
            current_cmd_info["arguments"] += source_cmd_info["arguments"]

        if options:
            current_cmd_info["options"] += source_cmd_info["options"]

        return wrapper_clone

    return decorator_clone

def get_commands():
    cmd_list = list(commands_by_name.values())
    return cmd_list

def get_command(name):
    return commands_by_name[name]

def get_explicit_options():
    '''
    return dict of options explicitly set for this command (dash-style names)
    '''
    return explict_options

class Dispatcher():
    def __init__(self, impl_dict, config, preprocessor=None):
        self.impl_dict = impl_dict
        self.config = config
        self.preprocessor = preprocessor
        self.cmd_words = None
        self.dispatch_cmd = None
        self.cmd_info = None
        global commands_by_name, current_dispatcher
        commands_by_name = build_commands()
        current_dispatcher = self

    def validate_and_add_defaults_for_cmd(self, cmd, arg_dict):
        cmd_info = get_command("run")
        options = cmd_info["options"]
        arguments = cmd_info["arguments"]

        return self.validate_and_add_defaults(arguments, options, arg_dict)

    def show_current_command_syntax(self):
        console.print()
        help_impl = self.impl_dict["xtlib.impl_help"]
        help_impl.command_help(self.cmd_info, True, False)

    def hide_commands(self, cmds_to_hide):
        for cmd in cmds_to_hide:
            if cmd in commands_by_name:
                cmd_info = commands_by_name[cmd]
                cmd_info["hidden"] = True

    def show_commands(self, show_dict):
        # start by hiding all commands
        for name, cmd_info in commands_by_name.items():
            cmd_info["hidden"] = True

        # show specified commands
        for cmd, args_to_show in show_dict.items():
            if cmd in commands_by_name:
                cmd_info = commands_by_name[cmd]
                cmd_info["hidden"] = False
                self.show_cmd_options(cmd_info, args_to_show)

    def show_cmd_options(self, cmd_info, args_to_show):
        for arg in cmd_info["arguments"]:
            arg["hidden"] = not (arg["name"] in args_to_show)

        for opt in cmd_info["options"]:
            opt["hidden"] = not (opt["name"] in args_to_show)

    def match(self, text, cmd):
        '''
        implements the min. 4-char abbreviaton matching.
        '''
        return cmd == text or (len(text) >= 4 and cmd.startswith(text))

    def match_keyword(self, value, keywords):
        found = None

        for kw in keywords:
            if self.match(value, kw):
                found = kw
                break
        
        return found

    def get_cmd_info(self, tok, scanner, for_help=False):
        '''
        given a command line (without the program name), parses it and calls the associated
        cmd_info.
        '''
        dd = commands 
        words_seen = ""

        if not tok:
            # no input defaults to help command
            tok = "help"

        while tok:
            if tok.startswith("-"):
                break

            name = tok
            key = self.list_item_by_value(name, dd.keys())
            if not key:
                #error("command part={} not found in dd={}".format(arg, dd))
                break

            dd = dd[key]    
            tok = scanner.scan()        # skip over name
            if words_seen:
                words_seen += " " + key
            else:
                words_seen = key

        # process OUTER LEVEL match (some special cases)
        if dd == command:
            if not words_seen:
                self.syntax_error("unrecognized start of command: " + tok)

        # if not "" in dd and not for_help:
        #     errors.user_error("incomplete command: " + words_seen)

        if "" in dd:
            cmd_info = dd[""]
        else:
            # return a dict of commands (for "list", "view", etc.)
            cmds = {"kwgroup_name": words_seen}   # mark as kwgroup of cmds
            get_commands_from(dd, cmds)
            cmd_info = cmds

        return cmd_info, tok

    def parse_string_list(self, tok, scanner, pipe_objects_enabled=True):
        global pipe_object_list
        #print("parse_string_list, tok=", tok)
    
        if not tok:
            # empty string specified
            value = []
            tok = scanner.scan()   # skip over the empty string
        elif tok == "$":
            if pipe_objects_enabled:
                global pipe_object_list
                pipe_object_list =  get_xt_objects_from_cmd_piping()
                console.diag("pipe_object_list: {}".format(pipe_object_list))

            if pipe_objects_enabled and pipe_object_list:
                #print("found '*', pipe_object_list=", pipe_object_list)
                value =  pipe_object_list
                console.print("replacing '$' with: ", value)
            else:
                errors.combo_error("'$' can only be used for piping the output of a previous XT command into this run")

            # mark pipe objects as having been consumed by this parsing
            pipe_object_list = None

            tok = scanner.scan()   # skip over the $
        else:
            # scan a comma separated list of tokens (some of which can be single quoted strings)
            value = []
    
            while tok != None:
                if tok.startswith("--"):
                    break
                    
                ev = self.expand_system_values(tok)
                value.append(ev)

                tok = scanner.scan()
                if tok != ",":
                    break

                tok = scanner.scan()   # skip over the comma

        return value, tok

    def expand_system_values(self, value):
        if value in ["$null", "$none"]:
            value = None
        elif value == "$empty":
            value = ""

        return value

    def parse_num_list(self, tok, scanner, pipe_objects_enabled=True):
        global pipe_object_list
    
        if "," in tok and not tok.startswith("--"):
            # str_list in an option string
            values = tok.split(",")
            value = [float(v) for v in values]

            tok = scanner.scan()        # skip over the whole string
        else:
            # normal list of comma-separated tokens
            value = []
    
            while tok != None:
                if tok.startswith("--"):
                    break
                    
                value.append(float(tok))

                tok = scanner.scan()
                if tok != ",":
                    break

                tok = scanner.scan()   # skip over the comma

        return value, tok

    def parse_prop_op_value_list(self, tok, scanner):
        # normal list of comma-separated tokens
        values = []

        while tok != None:
            if tok.startswith("--"):
                break
                
            value = self.process_prop_op_value(tok)
            values.append(value)

            tok = scanner.scan()
            if tok != ",":
                break

            tok = scanner.scan()   # skip over the comma

        return values, tok

    def parse_int_list(self, tok, scanner, pipe_objects_enabled=True):
        global pipe_object_list
    
        if "," in tok and not tok.startswith("--"):
            # str_list in an option string
            values = tok.split(",")
            value = [int(v) for v in values]

            tok = scanner.scan()        # skip over the whole string
        else:
            # normal list of comma-separated tokens
            value = []
    
            while tok != None:
                if tok.startswith("--"):
                    break
                    
                value.append(int(tok))

                tok = scanner.scan()
                if tok != ",":
                    break

                tok = scanner.scan()   # skip over the comma

        return value, tok

    def parse_tag_list(self, tok, scanner):
        tag_list = []

        while tok != None:
            if tok.startswith("--"):
                break

            # tagname
            tag = tok
            tok = scanner.scan()    # skip over tagname

            if tok == "=":
                # optional assignment
                tok = scanner.scan()    # skip over =
                tag += "=" + tok
                tok = scanner.scan()    # skip over value

            tag_list.append(tag)
            
            if tok != ",":
                break
            tok = scanner.scan()   # skip over the comma

        return tag_list, tok

    def list_item_by_name(self, name, values):
        matches = [value for value in values if self.match(name, value["name"])]
        found = matches[0] if matches else None
        return found

    def list_item_by_value(self, value, values):
        matches = [val for val in values if self.match(value, val)]
        found = matches[0] if matches else None
        return found

    def get_default_from_config(self, value):
        if value and isinstance(value, str) and value.startswith("$"):
            group, prop = value[1:].split(".")
            value = self.config.get(group, prop)

        return value

    # def process_value(self, value, type):
    #     if type == "flag":
    #         if value is not None:
    #             value = int(value)

    #     return value

    def process_root_options(self, scanner, tok):
        options_processed = {}

        root_options = root_cmd_info["options"]
        root_func = root_cmd_info["func"]
        #console.print("root_options=", root_options)

        while tok and tok.startswith("--"):
            name = tok[2:]    # remove dashes
            match = self.list_item_by_name(name, root_options)
            if not match:
                break

            name = match["name"]        # full name
            tok = scanner.scan()        # skip over name
            value = True

            if tok == "=":
                tok = scanner.scan()        # skip over equals
                value = tok
                tok = scanner.scan()        # skip over value

            values = match["values"] if "values" in match else None
            value = self.process_option_value(name, match["type"], value, values)

            arg_dict =  {"name": name, "value": value}
            caller = self.impl_dict[root_func.__module__]

            # call func for root flag procesing
            if self.preprocessor:
                self.preprocessor("root_flag", caller, arg_dict)

            root_func(caller, **arg_dict)
            options_processed[name] = 1

        # ensure all root options have been processed
        for info in root_cmd_info["options"]:
            name = info["name"]
            required = info["required"] if "required" in info else None

            if not name in options_processed:
                #console.print("opt_info=", opt_info)
                if required:
                    self.syntax_error("value for required option={} not found".format(name))

                default_prop_name = info["default"] if "default" in info else None
                default_value = self.get_default_from_config(default_prop_name)
                arg_dict =  {"name": name, "value": default_value}
                caller = self.impl_dict[root_func.__module__]
        
                if self.preprocessor:
                    self.preprocessor("root flag", caller, arg_dict)

                # call func for root flag procesing
                root_func(caller, **arg_dict)
        return tok

    def process_arguments(self, scanner, tok, arguments, arg_dict):
        for arg_info in arguments:
            if utils.safe_value(arg_info, "hidden"):
                continue

            arg_name = arg_info["name"]
            arg_type = arg_info["type"]
            required = arg_info["required"]
            keywords = arg_info["keywords"] if "keywords" in arg_info else None
            current_arg = None

            #print("processing arg=", arg_name, arg_type, tok)

            if arg_type == "cmd" and tok and not tok.startswith("-"):
                # convert remaining tokens to a cmd_info
                if tok:
                    # if self.match(tok, "topics"):
                    #     cmd_info = {"name": "topics"}
                    #     tok = scanner.scan()
                    # else:
                    cmd_info, tok = self.get_cmd_info(tok, scanner, for_help=True)
                    current_arg = cmd_info
            elif arg_type == "text":
                # convert remaining tokens to a string
                if tok:
                    text = scanner.get_rest_of_text(include_current_token=True)
                    tok = None
                else:
                    text = ""
                current_arg = text
            else:
                if tok and not tok.startswith("-"):
                    current_arg = tok

            if required and not current_arg:
                self.syntax_error("cmd '{}' missing required argument: {}".format(self.cmd_words, arg_name))

            if current_arg:
                if arg_type == "str_list":
                    value, tok = self.parse_string_list(tok, scanner)
                    if len(value)==0 and required:
                        self.syntax_error("missing value for required argument: " + arg_name)
                elif arg_type == "num_list":
                    value, tok = self.parse_num_list(tok, scanner)
                    if len(value)==0 and required:
                        self.syntax_error("missing value for required argument: " + arg_name)
                elif arg_type == "int_list":
                    value, tok = self.parse_int_list(tok, scanner)
                    if len(value)==0 and required:
                        self.syntax_error("missing value for required argument: " + arg_name)
                elif arg_type == "tag_list":
                    value, tok = self.parse_tag_list(tok, scanner)
                    if len(value)==0 and required:
                        self.syntax_error("missing value for required argument: " + arg_name)
                else:
                    value = current_arg
                    if keywords:
                        found = self.match_keyword(value, keywords)
                        if not found:
                            self.syntax_error("Keyword argument {} has unrecognized value: {}".format(arg_name, value))
                        value = found
                    tok = scanner.scan()

                # store value to be passed 
                arg_dict[arg_name] = value

        if tok and not tok.startswith("--"):
            errors.argument_error("unrecognized argument", tok)
        return tok

    def scan_raw_value(self, scanner, tok):
        # assume it is a str list
        value, tok = self.parse_string_list(tok, scanner)
        if len(value)==0:
            value = None
        elif len(value)==1:
            value = value[0]
        return value, tok

    def parse_flag_value(self, name, value):
        value = str(value).lower()
        flag_values = ["true", "false", "on", "off", "0", "1"]

        if not value in flag_values:
            self.syntax_error("flag option '{}' value is not one of these recognized values: {}".format(name, ", ".join(flag_values)))
        
        # set to True/False so that it can filter boolean properties correctly
        #value = 1 if value in ["true", "on", "1"] else 0
        value = True if value in ["true", "on", "1"] else False
        return value

    def process_prop_op_value(self, value):
        # mini parse of the value: <prop> <op> <value>
        scanner = Scanner(value)
        prop = scanner.scan(False)
        if scanner.token_type != "id":
            self.syntax_error("expected property name in filter expression: " + prop)

        op = scanner.scan()
        if scanner.token_type != "special":
            self.syntax_error("expected relational operator in filter expression: " + op)

        # expressions can be complicated; we want the rest of the string containing the filter
        value = scanner.get_rest_of_text()

        # adjust for for :id: operators
        if op == ":" and ":" in value:
            op2, value = value.split(":", 1)
            op += op2 + ":"

        value = {"prop": prop, "op": op, "value": value}
        #print("process_prop_op_value: value=", value)
        return value

    def process_option_value(self, opt_name, opt_type, value, values):

        if values:
            found = self.match_keyword(value, values)
            if not found:
                self.syntax_error("Value for option {} not recognized: {}, must be one of: {}".format(opt_name, value, ", ".join(values)))
            value = found
        elif opt_type == "flag":
             value = self.parse_flag_value(opt_name, value)
        elif opt_type == "int":
            value = int(value)
        elif opt_type == "float":
            value = float(value)
        elif opt_type == "bool":
            value = value.lower()
            if value in ["true", "1"]:
                value = True
            elif value in ["false", "0"]:
                value = False
            else:
                self.syntax_error("Illegal value for boolean option: " + str(value))
        elif opt_type == "prop_op_value":
            value = self.process_prop_op_value(value)
        elif opt_type == "str_list":
            if not isinstance(value, list):
                value = [value]
        elif opt_type == "named_arg_list":
            if not isinstance(value, list):
                value = [value]
            value = self.convert_str_list_to_arg_dict(value)
        elif opt_type == "int_list":
            if not isinstance(value, list):
                value = [value]
        elif opt_type == "num_list":
            if not isinstance(value, list):
                value = [value]
        elif opt_type == "str":
            value = self.expand_system_values(value)
        else:
            errors.internal_error("unrecognized option type: {}".format(opt_type))

        return value

    def convert_str_list_to_arg_dict(self, values):
        ad = {}
        for value in values:
            if not "=" in value:
                self.syntax_error("named arg value must contain an equals sign ('='): {}".format(value))

            name, val = value.split("=")
            name = name.strip()
            val = val.strip()

            ad[name] = val

        return ad
        
    def get_dispatch_cmd(self):
        return self.dispatch_cmd

    def is_single_token(self, text):
            ms = Scanner(text)

            # scan first token
            tok = ms.scan()

            # try to get second token
            tok = ms.scan()
            tok2 = ms.scan()

            single = (tok is None)
            single_with_comma = (tok == "," and tok2 is None)
            return single, single_with_comma

    def add_quotes_to_string_args(self, args):
        #console.print("BEFORE: self.args=", self.args)

        for i, arg in enumerate(args):

            # we currently process our options and those of ML app

            #if arg.startswith("-"):
            # parse option or tag: name=text
            if "=" in arg:
                # --option=value  (we only care about FIRST '=')
                name, text = arg.split("=", 1)
                single, single_with_comma = self.is_single_token(text)

                if not single and not single_with_comma:
                    # add back quotes that were string by the shell/command processor
                    arg = name + '="' + text + '"'
                    args[i] = arg
            elif arg != "=":
                # parse target or option value
                if not self.is_single_token(arg):
                    arg = '"' + arg + '"'
                    args[i] = arg


    def validate_and_add_defaults(self, arguments, options, arg_dict):
        '''
        args:
            - arguments: list of the arguments for the current cmd 
            - options: list of options for the current cmd
            - arg_dict: dict of name/value pairs for user-specified args and options

        processing:
            - copy arg_dict to "explicit_options"
            - validate all names in arg_dict (against arguments & options)
            - flag as error if any required arguments/options are not specified in arg_dict
            - add default values for all arguments/options not yet specified inarg_dict

        return:
            - fullly populated copy of arg_dict
        '''
        # ensure all names in arg_dict are dash style (for validation)
        full_arg_dict = { key.replace("_", "-"):value for key, value in arg_dict.items() }

        # remember options that were set explicitly (dash-style)
        global explict_options
        explict_options = dict(full_arg_dict)

        # process all aguments, options, and flags; ensure each has a value in arg_dict
        all_args = arguments + options
        all_arg_names = [aa["name"] for aa in all_args]

        # process user args in arg_dict
        for name, value in full_arg_dict.items():

            # validate arg name
            if not name in all_arg_names:
                errors.api_error("unknown args name: {}".format(name))

        # now add default values for all other args
        for info in all_args:
            name = info["name"]
            required = info["required"] if "required" in info else None

            if not name in full_arg_dict:
                if required:
                    self.syntax_error("cmd '{}' missing value for required option: --{}".format(self.cmd_words, name))

                default_value = utils.safe_value(info, "default")

                # expand "$group.value" type values
                default_value = self.get_default_from_config(default_value)

                # add to user's arg dict
                full_arg_dict[name] = default_value

        # finally, convert all names to underscore style
        full_arg_dict = { key.replace("-", "_"): value for key, value in full_arg_dict.items() }

        console.diag("full_arg_dict=", full_arg_dict)
        return full_arg_dict

    def syntax_error(self, msg):
        console.print(msg)
        self.show_current_command_syntax()

        if self.raise_syntax_exception:
            errors.syntax_error("syntax error")
        
        errors.syntax_error_exit()

    def replace_curlies_with_quotes(self, text):
        '''
        replace any {} that appear outside of quotes with single quotes.
        '''

        new_text = ""
        protector = None

        for ch in text:
            if ch == protector:

                # end of a quoted string
                protector = None
                if ch == "}":
                    ch = "'"
            elif not protector:

                # outside of a quoted string
                if ch in ["'", '"', "{"]:
                    # start of a quoted string
                    if ch == "{":
                        protector = "}"
                        ch = "'"
                    else:
                        protector = ch

            new_text += ch

        return new_text

    def dispatch(self, args, is_rerun=False, capture_output=False, raise_syntax_exception=False):
        self.raise_syntax_exception = raise_syntax_exception
        
        # TODO: change to cmd_parts parsing, which naturally separates options cleanly (utils.cmd_split)

        # be sure to reset this for each parse (for multi-command XT sessions)
        global explict_options
        explict_options = {}

        orig_text = " ".join(args)
        self.dispatch_cmd = orig_text

        text = self.replace_curlies_with_quotes(orig_text)
        console.diag("fixed cmd={}".format(text))

        scanner = Scanner(text)
        tok = scanner.scan()
        #console.print("first tok=", tok)

        # process any ROOT FLAGS
        if root_cmd_info:
            tok = self.process_root_options(scanner, tok)
        else:
            # there is no command to process --console, so set it explictly now
            console.set_level("normal")

        console.diag("start of command parsing: {}".format(text))

        # process any options before the cmd as RAW options
        # raw_options = []
        # tok = self.collect_raw_options(raw_options, scanner, tok)

        # process COMMAND keywords
        cmd_info, tok = self.get_cmd_info(tok, scanner)
        self.cmd_info = cmd_info

        if "kwgroup_name" in cmd_info:
            cmd_info = get_command("help")

        self.cmd_info = cmd_info

            # # user type incomplete command - display appropriate help
            # if raise_syntax_exception:
            #     errors.syntax_error("incomplete command")

            # if command_help_func:
            #     # parse any help-specific options
            #     help_options = {}
            #     self.parse_options(help_options, options, scanner, tok)

            #     caller = self.impl_dict[command_help_func.__module__]
            #     kwgroup_help_func(caller, cmd_info)
            #     return
            # else:
            #     errors.env_error("no registered 'help' command")

        cmd_name = cmd_info["name"]
        self.cmd_words = cmd_name.replace("_", " ")
        func = cmd_info["func"]
        options = cmd_info["options"]
        arguments = cmd_info["arguments"]
        options_before_args = cmd_info["options_before_args"]

        # command-specific help?
        # if "help" in raw_options:
        #     help_value = raw_options["help"]
        #     if help_value != None:
        #         self.syntax_error("unexpected text after '--help': " + help_value)
        if tok == "--help":
            help_value = scanner.scan()

            if help_value != None:
                self.syntax_error("unexpected text after '--help': " + help_value)

            caller = self.impl_dict[command_help_func.__module__]
            if self.preprocessor:
                self.preprocessor(caller, arg_dict)

            command_help_func("help", caller, cmd_info)
            return

        # build a dictionary of arguments and options to be passed
        arg_dict = {}

        if options_before_args:
            # options come before arguments
            tok = self.parse_options(arg_dict, options, scanner, tok)
            tok = self.process_arguments(scanner, tok, arguments, arg_dict)
        else:
            # arguments come before options
            tok = self.process_arguments(scanner, tok, arguments, arg_dict)
            tok = self.parse_options(arg_dict, options, scanner, tok)

        # there should be no remaining tokens
        if tok:
            errors.argument_error("end of input", tok)

        full_arg_dict = self.validate_and_add_defaults(arguments, options, arg_dict)

        console.diag("dispatching to command func")

        # select the caller using function's module name
        caller = self.impl_dict[func.__module__]
        if capture_output:
            caller.set_capture_output(True)
 
        if is_rerun:
            full_arg_dict["is_rerun"] = 1

        # call the matching command function with collected func args
        if self.preprocessor:
            self.preprocessor("command", caller, full_arg_dict)

        if cmd_info["pass_by_args"]:
            func(caller, args=full_arg_dict)
        else:
            func(caller, **full_arg_dict)

        console.diag("end of command processing")
        output = None

        if capture_output:
            output = caller.set_capture_output(False)

        return output

    def parse_options(self, arg_dict, options, scanner, tok):
        '''
        TODO: parse scanned option according to the *options* argument, 
        not as "raw options".  
        '''
        raw_options = []

        #tok = self.collect_raw_options(raw_options, scanner, tok)
        #self.process_raw_options(options, raw_options, arg_dict)
        tok = self.process_cmd_options(arg_dict, options, scanner, tok)

        return tok

    def process_cmd_options(self, arg_dict, options, scanner, tok):

        while tok and tok.startswith("--"):
            name = tok[2:]    # remove dashes
            match = self.list_item_by_name(name, options)
            if not match:
                self.syntax_error("cmd '{}' doesn't have an option named: {}".format(self.cmd_words, tok))

            name = match["name"]        # full name
            tok = scanner.scan()        # skip over name
            value = True
            found_equals = False

            if tok == "=":
                found_equals = True
                tok = scanner.scan()        # skip over equals

            values = match["values"] if "values" in match else None
            #value = self.process_option_value(name, match["type"], value, values)
            value, tok = self.parse_option_value(name, match["type"], values, found_equals, tok, scanner)

            arg_dict[name] = value

        return tok

    def parse_option_value(self, name, opt_type, keywords, found_equals, tok, scanner):

        if opt_type == "str_list":
            value, tok = self.parse_string_list(tok, scanner)
            if len(value)==0 and required:
                self.syntax_error("missing value for required option: " + name)

        elif opt_type == "num_list":
            value, tok = self.parse_num_list(tok, scanner)
            if len(value)==0 and required:
                self.syntax_error("missing value for required option: " + name)

        elif opt_type == "int_list":
            value, tok = self.parse_int_list(tok, scanner)
            if len(value)==0 and required:
                self.syntax_error("missing value for required option: " + name)

        elif opt_type == "tag_list":
            value, tok = self.parse_tag_list(tok, scanner)
            if len(value)==0 and required:
                self.syntax_error("missing value for required option: " + name)

        elif opt_type == "prop_op_value":
            value, tok = self.parse_prop_op_value_list(tok, scanner)
            if len(value)==0 and required:
                self.syntax_error("missing value for required option: " + name)

        elif opt_type == "named_arg_list":
            value, tok = self.parse_string_list(tok, scanner)
            if not isinstance(value, list):
                value = [value]
            value = self.convert_str_list_to_arg_dict(value)

        elif opt_type == "flag":
            if found_equals:
                value = tok
                tok = scanner.scan()
                value = self.parse_flag_value(name, value)
            else:
                value = 1
        else:
            # its a simple value
            value = tok
            tok = scanner.scan()

            if opt_type == "int":
                value = int(value)

            elif opt_type == "float":
                value = float(value)

            elif opt_type == "bool":
                value = value.lower()
                if value in ["true", "1"]:
                    value = True
                elif value in ["false", "0"]:
                    value = False
                else:
                    self.syntax_error("Illegal value for boolean option: " + str(value))
            elif opt_type == "str":
                value = self.expand_system_values(value)

            else:
                errors.internal_error("Unsupported opt_type={}".format(opt_type))
        
        return value, tok