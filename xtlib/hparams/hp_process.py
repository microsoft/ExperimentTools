#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# HPProcess.py: code for processing hyperparameter settings in cmd line arguments of an app
import numpy as np
import copy

from xtlib import utils
from xtlib import constants
from xtlib import errors
from xtlib import file_utils
from xtlib.console import console

def make_param(value):
    value = value.strip()
    try:
        value = int(value)
    except:
        try:
            value = float(value)
        except:
            # value must be a string
            value = str(value)
    return value

class HPProcess():
    def __init__(self, collect_only):
        self.collect_only = collect_only    
        
    def parse_hp_set(self, text, dist_name, search_type):
        '''
        parse a range or distrubution of values for a HP, specified
        in "text".  Return "hp_set", a distribution object describing the
        values (HPDist, HPList, HPRange).
        '''
        hp_set = None
        #console.print("parse_hp_set: text=", text)

        if dist_name:
            hp_set = HPDist(dist_name, text)
        elif "*" in text or "?" in text:
            # expand directory or file wildcard
            values = file_utils.get_files_dirs(text)
            values = [make_param(value) for value in values]
            hp_set = HPList(values, search_type)
        elif ":" in text:
            # min:max values
            parts = text.split(":")
            vmin = make_param(parts[0])
            vmax = make_param(parts[1])
            vmean = make_param(parts[2]) if len(parts) > 2 else None
            vstddev = make_param(parts[3]) if len(parts) > 3 else None
            
            hp_set = HPRange(vmin, vmax, vmean, vstddev)
        elif "," in text:
            # comma separated list
            values = text.split(",")
            values = [make_param(value) for value in values]
            hp_set = HPList(values, search_type)
        else:
            # treat as a single value in a list (user is trying out different ideas)
            hp_set = HPList( [text], search_type )

        return hp_set

    def hp_set_to_sweeps_line(self, name, hp_set):
        '''
        Convert "hp_set" (an object describing a range of values to be searched)
        to a line of text compatible with the sweeps file.
        '''
        if name.startswith("--"):
            name = name[2:]
        elif name.startswith("-"):
            name = name[1:]
            
        if isinstance(hp_set, HPList):
            #console.print("hp_set.values=", hp_set.values)
            text = "{} = ".format(name)
            text += ", ".join((str(v) for v in hp_set.values))
        else:
            #console.print("hp_set.min=", hp_set.min, ", hp_set.max=", hp_set.max)
            text = "# {} = [{}:{}".format(name, hp_set.min, hp_set.max) 
            if hp_set.mean:
                text += ":{}".format(hp_set.mean)
                if hp_set.stddev:
                    text += ":{}".format(hp_set.stddev)
            text += "]"
        return text

    def generate_hparam_args(self, orig_cmd_parts, max_gen=None, search_type="grid"):
        ''' this is the main function for this class.  it parses the specified argument name/values of 'orig_cmd_parts', 
        converts each search list/range into a hyperparameter generator, and then generates a set of cmd_parts 
        that comprise the hyperparameter search.
       
        returns:
            'arg_sets' - a set of command line argument VALUES (one for each run)
            'cmd_parts' - a template to be used to create a command line for the app (when applied to one of the arg sets)
        '''
        cmd_parts = copy.copy(orig_cmd_parts)
        sweeps_text = ""

        # cmdline = " ".join(sys.argv[1:])
        # console.print("ORIG cmdline: ", cmdline)

        hp_sets = {}
        last_part = None

        for i, part in enumerate(cmd_parts):
            part = part.replace('"', '')    # remove double quoted sub-parts
            #console.print("part=", part)
            found = False
            dist_name = None

            '''
            we support two basic forms of specifying hparam distributions to search:
                name=[values]
                name=@disttype(values)

            the name, the "=", and the right-hand expression can be seen all in one part, or 
            in 2 parts (no "="), or in 3 parts.
            '''

            if part == "=":
                # skip over optional "=" in its own part
                continue

            if "=[" in part and "]" in part:
                index = part.index("=[")
                name = part[:index]
                part = part[index+2:]

                if part.endswith("]"):
                    part = part[:-1].strip()
                    cmd_parts[i] = cmd_parts[i][0:index+1] + "{}" 
                    #console.print("part=", part, ", cmd_part=", cmd_parts[i])
                    found = True
            elif "=@" in part and "(" in part and part.endswith(")"):
                index = part.index("=@")
                name = part[:index]
                part = part[index+2:]

                dist_name, value = part.split("(")
                if not dist_name in constants.distribution_types:
                    errors.syntax_error("Unsupported distribution type: " + dist_name)
                part = value[:-1].strip()   # remove ending paren
                cmd_parts[i] = "{}" 
                found = True
            elif part.startswith("[") and part.endswith("]"):
                part = part[1:-1].strip()
                name = last_part
                cmd_parts[i] = "{}" 
                found = True
            elif part.startswith("@") and "(" in part and part.endswith(")"):
                part = part[1:]   # skip over "@"
                dist_name, value = part.split("(")
                if not dist_type in constants.distribution_types:
                    errors.syntax_error("Unsupported distribution type: " + dist_name)
                name = last_part
                part = value[:-1].strip()   # remove ending paren
                cmd_parts[i] = "{}" 
                found = True

            if found:   
                hp_set = self.parse_hp_set(part, dist_name, search_type)
                if not self.collect_only:
                    text = self.hp_set_to_sweeps_line(name, hp_set)
                    if text:
                        sweeps_text += text + "\n"
                    #console.print("hp_set=", hp_set)
                if hp_set:
                    hp_sets[name] = hp_set

            last_part = part

        if sweeps_text:
            sweeps_text = "# sweeps.txt: generated from xt command line hyperparameter arguments\n" + \
                        "# note: this file is not sampled from directly\n" + \
                        sweeps_text

        # set the cycle len of each hp_set
        cycle_len = 1
        for hp_set in hp_sets.values():
            cycle_len = hp_set.set_cycle_len(cycle_len)

        # generate arg_sets from hp_sets
        arg_sets = []
        #console.print("hp_sets=", hp_sets)
        using_hp = len(hp_sets) > 0

        if hp_sets and not self.collect_only:
            if max_gen is None:
                max_gen = cycle_len
            else:
                max_gen = int(max_gen)

            while len(arg_sets) < max_gen:
                values = []
                for name, hp_set in hp_sets.items():
                    value = hp_set.next()
                    #console.print("generate value: ", value)
                    values.append(value)

                arg_sets.append(values)

        return using_hp, hp_sets, arg_sets, cmd_parts, sweeps_text

    def fill_in_template(self, template_parts, values):
        cmd_parts = copy.copy(template_parts)
        for i, part in enumerate(cmd_parts):
            if "{}" in part:
                value = values.pop(0)
                cmd_parts[i] = part.format(value)

        #console.print("ACTUAL cmd_parts=", cmd_parts)
        return cmd_parts

class HPDist():
    ''' an Azure ML hyperdrive distribution.  Consists of a dist name and a list of values.'''
    def __init__(self, dist_name, values):
        self.dist_name = dist_name
        self.values = values

    def set_cycle_len(self, cycle_len):
        pass

class HPList():
    ''' a hyperparmeter generator that operates off a specified list of discrete values. 
    values from this object can be sampled randomly or sequentially (using cycle_len).'''
    def __init__(self, values, search_type):
        self.values = values
        # cycle_len is how many times we repeat the current value, before moving to next
        self.cycle_len = 1
        self.cycle_count = 0    # how many times have we repeated current value
        self.index = 0          # the current value we are repeating
        self.search_type = search_type

    def set_cycle_len(self, cycle_len):
        self.cycle_len = cycle_len
        return len(self.values) * cycle_len

    def next(self):
        if self.search_type == "random":
            # uniform random sample
            index = np.random.randint(len(self.values))
            value = self.values[index]
        else:
            # grid type search over values
            value = self.values[self.index]
            self.cycle_count += 1

            if self.cycle_count >= self.cycle_len:
                self.index += 1
                self.cycle_count = 0

                if self.index >= len(self.values):
                    self.index = 0

        return value

class HPRange():
    ''' a hyperparmeter generator that operates off a specified range of values. 
    values from this object are always sampled randomly.
    '''
    def __init__(self, min, max, mean=None, stddev=None):
        self.min = min
        self.max = max
        self.diff = max - min
        self.mean = mean
        self.int_values = isinstance(min, int) and isinstance(max, int) and mean is None

        if mean and stddev is None:
            stddev = self.diff * .25            
        self.stddev = stddev

    def set_cycle_len(self, cycle_len):
        # ranges don't use cycle_len
        return cycle_len

    def next(self):
        if self.mean:
            # generate normalized random value
            value = self.stddev * np.random.randn() + self.mean

            # clip to min/max, in case we sampled outside our limits
            value = np.clip(value, self.min, self.max)
        else:
            # generate uniform random value
            value = self.min + self.diff * np.random.random()
            if self.int_values:
                value = int(value)

        return value
