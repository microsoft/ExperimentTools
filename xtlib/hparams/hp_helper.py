#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# hp_helper.py: helper functions for hparam processing
from hyperopt import hp
import numpy as np

from xtlib import utils

def parse_func_with_args(text):
    '''
    args:
        text: a func call in form: name(arg1, arg2, ...)

    processing:
        parse the *text* function call into name and args.

    return:
        func:  name of function
        args: list of arg values (floats)
    '''
    func, rest = text.split("(")
    args_str, _ = rest.split(")")

    if args_str:
        args = args_str.split(",")
        # convert from strings to floata
        args = [utils.get_python_value_from_text(arg) for arg in args]
    else:
        args = []

    return func, args

def arg_check(func, args, count):
    if len(args) != count:
        errors.config_error("this function requires {} args: ".format(func, count))

def build_dist_func_instance(hp_name, func, args, hp_size=None):
    '''
    args:
        hp_name: the name of the hyperparameter associated with this func
        func: name of hyperopt dist func 
        args: list of float values

    processing:
        instantiate the named dist func with specified args

    return:
        instance of hyperopt dist func
    '''
    if func == "choice":
        dist = hp.choice(hp_name, args)

    elif func == "randint":
        max_value = 65535 if len(args) == 0 else args[0]

        # specify "size=None" to workaround hyperopt bug
        if hp_size:
            # let size default to () (error if we try to set it explictly)
            dist = hp.randint(hp_name, max_value)
        else:
            dist = hp.randint(hp_name, max_value, size=None)

    elif func == "uniform":
        arg_check(func, args, count=2)
        dist = hp.uniform(hp_name, *args)

    elif func == "normal":
        arg_check(func, args, count=2)
        dist = hp.normal(hp_name, *args)

    elif func == "loguniform":
        arg_check(func, args, count=2)
        dist = hp.loguniform(hp_name, *args)

    elif func == "lognormal":
        arg_check(func, args, count=2)
        dist = hp.lognormal(hp_name, *args)

    elif func == "quniform":
        arg_check(func, args, count=3)
        dist = hp.quniform(hp_name, *args)

    elif func == "qnormal":
        arg_check(func, args, count=3)
        dist = hp.qnormal(hp_name, *args)

    elif func == "qloguniform":
        arg_check(func, args, count=3)
        dist = hp.qloguniform(hp_name, *args)

    elif func == "qlognormal":
        arg_check(func, args, count=3)
        dist = hp.qlognormal(hp_name, *args)

    return dist


def parse_hp_dist(value):
    '''
    args:
        value: value of the HP (number, text, $dist_func)

    processing:
        parse value to 1 of 10 hyperopt search distribution functions
        
    return:
        a dict with "func" and "args" key/value pairs
    '''
    if isinstance(value, (list, tuple)):
        # parse a list of choices
        func = "choice"
        args = value
    elif isinstance(value, str) and value.startswith("$"):
        # linspace or hyperopt dist function
        func, args = parse_func_with_args(value[1:])
        
        if func == "linspace":
            args = np.linspace(*args)
            func = "choice"
    else:
        # single value
        func = "choice"
        args = [value]

    fa = {"func": func, "args": args, "yaml_value": value}
    return fa