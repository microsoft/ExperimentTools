#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# hp_search_random.py: perform a random search of the specified parameters
import hyperopt.pyll.stochastic as stochastic
from interface import implements

from xtlib import console
from xtlib.hparams.hp_search_interface import HpSearchInterface

class RandomSearch(implements(HpSearchInterface)):
    def __init__(self):
        pass

    def need_runs(self):
        # since this isn't normally used as a dynamic search algorithm,
        # we use it for scale testing of MONGO logging and retrieval and
        # return True here to enable that retrieval.
        return True

    def search(self, run_name, store, context, hp_records, runs):
        '''
        sample from each HP record and build a dict of hp name/value pairs.
        '''
        arg_dict = {}

        for record in hp_records:
            prop = record["name"]
            space = record["space_func"]

            # sample value now
            value = self.sample_space(space)
            arg_dict[prop] = value

        #console.print("discount_factor=", arg_dict["DISCOUNT_FACTOR"])
        return arg_dict

    def sample_space(self, space):
        value = stochastic.sample(space)

        if isinstance(value, str):
            value = value.strip()
            if " " in value:
                # surround with quotes so it is treated as a single entity
                value = '"' + value + '"'

        return value


