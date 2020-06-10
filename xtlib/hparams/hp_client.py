#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# hp_client.py: HPClient class supports the XT client side of hyperparameter processing

import numpy as np
import hyperopt.pyll.stochastic as stochastic

from xtlib import utils
from xtlib import constants
from xtlib import errors
from xtlib import file_utils
from xtlib.hparams import hp_helper

class HPClient():
    def __init__(self):
        pass


    def extract_dd_from_cmdline(self, cmd_line, option_prefix):
        '''
        args:
            cmd_line: <file> <args> <options>
            option_prefix: usually "-" or "--" (denotes the start of an argument)

        processing:
            parse the cmd_line looking for options. for each option value that is a
            hp search directive, collect it into a data dictionary.

        return:
            the data dictionary of hp search directives
        '''

        dd = {}
        parts = cmd_line.split(option_prefix)
        options = parts[1:]    # skip over text before first option
        new_cmd_line = parts[0]

        if options:
            for option in options:
                found = False
                name = None

                if "=" in option:
                    parts = option.split("=")
                    if len(parts) == 2:
                        name, value = parts
                elif " " in option:
                    name, value = option.split(" ", 1)

                if name:
                    name = name.strip()
                    if "[" in name:
                        errors.syntax_error("option name and value must be separated by a space or '=': {}".format(name))

                    # user may have added these thinking there were needed 
                    value = utils.remove_surrounding_quotes(value)

                    if value.startswith("[") and value.endswith("]"):
                        value = value[1:-1].strip()
                        if not "$" in value:
                            values = value.split(",")
                            value = [utils.get_python_value_from_text(val) for val in values]

                        dd[name] = hp_helper.parse_hp_dist(value)
                        found = True

                if not found:
                    new_cmd_line += " " + option_prefix + option 

        return dd, new_cmd_line


    def yaml_to_dist_dict(self, fn):
        '''
        args:
            fn: name of .yaml file

        processing:
            load data from .yaml file

        return:
            data
        '''
        yd = file_utils.load_yaml(fn)
        if not constants.HPARAM_DIST in yd:
            errors.config_error("hyperparmeter search file missing '{}' section: {}".format(constants.HPARAM_DIST, fn))

        hparams = yd[constants.HPARAM_DIST]
        dd = {}
        for key, value in hparams.items():
            dd[key] = hp_helper.parse_hp_dist(value)

        return dd

    def generate_hp_sets(self, dd, search_type, num_runs, max_gen, node_count):
        '''
        args:
            dd: a dict of HP name/dist_dict pairs (dist_dict has keys: func, args)
            search_type: 'grid' or 'random'
            num_runs: the number of runs to be generated (if None, defers to max_gen)
            max_gen: max # of HP sets to generate (if None, one entire grid pass is generated)

        processing: 
            we wrap each dist_dict in *dd* with a nifty class that knows how
            to do grid sampling for discrete ($choice) values and random sampling of any
            dist func.  Then we calculate max_gen (total # of grid samples) and 
            generate a hp_set (hp name/value dict) for each.

        return:
            a list of hp_set dictionaries (name/value pair for each HP)
        '''

        hp_wrappers = {}

        # wrap each dist func
        for name, dist_dict in dd.items():
            func = dist_dict["func"]
            args = dist_dict["args"]

            if func == "choice":
                wrapper = ListWrapper(args, search_type)
            else:
                dist_func = hp_helper.build_dist_func_instance(name, func, args)
                wrapper = DistWrapper(dist_func)
            hp_wrappers[name] = wrapper

        # set the cycle len of each hp_set
        cycle_len = 1
        for wrapper in hp_wrappers.values():
            cycle_len = wrapper.set_cycle_len(cycle_len)

        # generate hp_sets from hp_wrappers
        hp_sets = []
        #console.print("hp_wrappers=", hp_wrappers)

        if hp_wrappers:   #  and not self.collect_only:

            if not num_runs:

                if search_type == "grid":
                    if max_gen is None:
                        num_runs = cycle_len
                    else:
                        num_runs = min(int(max_gen), cycle_len)
                else:
                    num_runs = max_gen if max_gen else node_count

            while len(hp_sets) < num_runs:

                # generate a hp_set
                hp_set = {}
                for name, wrapper in hp_wrappers.items():
                    value = wrapper.next()
                    #console.print("generate value: ", value)
                    hp_set[name] = value

                hp_sets.append(hp_set)

        return hp_sets

    def dd_to_yaml(self, dd):
        '''
        args:
            dd - the data dict of hp_name/func_arg pairs
            fn - name of YAML file to create
            
        processing:
            for each item in dd, produce a yaml property.  Write resulting
            YAML to fn.

        returnls:
            None
        '''

        props = {}
        for name, value in dd.items():
            props[name] = value["yaml_value"]

        yd = {constants.HPARAM_DIST: props}
        return yd

    def generate_runs(self, hp_sets, cmd_line):
        run_cmds = []

        for hp_set in hp_sets:
            cmd = cmd_line

            for name, value in hp_set.items():
                cmd += " --{}={}".format(name, value)

            run_cmds.append(cmd)

        return run_cmds

class DistWrapper():
    '''
    HP generator that wraps a hyperopt distribution.  Can perform random sampling of the dist.
    '''
    def __init__(self, dist_func):
        self.dist_func = dist_func

    def set_cycle_len(self, cycle_len):
        # this class doesn't change the cycle len
        return cycle_len

    def next(self):
        value = stochastic.sample(self.dist_func)

        if isinstance(value, str):
            value = value.strip()
            if " " in value:
                # surround with quotes so it is treated as a single entity
                value = '"' + value + '"'

        return value

class ListWrapper():
    ''' 
    HP generator that wraps a list of discrete values.  Can perform random or GRID sampling of values, 
    using cycle_len trick).
    '''
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
