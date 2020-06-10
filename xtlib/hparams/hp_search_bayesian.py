#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# hp_search_bayesian.py: generate next HP set based according to bayesian search algorithm
import numpy as np
from hyperopt import Domain
from interface import implements
from hyperopt.utils import coarse_utcnow
import hyperopt.pyll.stochastic as stochastic
from hyperopt import hp, tpe, rand, Trials, base

from xtlib import constants
from xtlib import run_helper
from xtlib.hparams.hp_search_interface import HpSearchInterface

class BayesianSearch(implements(HpSearchInterface)):
    def __init__(self):
        pass

    def need_runs(self):
        return True

    def search(self, run_name, store, context, hp_records, runs):
        
        def make_trial(tid, arg_dict, loss_value):
            trial = {"book_time": None, "exp_key": None, "owner": None, "refresh_time": None, "spec": None, "state": 0, "tid": tid, "version": 0}
            #trial["result"] = {"status": "New"}
            misc = {}
            trial["misc"] = misc

            misc["cmd"] = ("domain_attachment", "FMinIter_Domain")
            misc["idxs"] = {key: [tid] for key in arg_dict.keys()}
            misc["tid"] = tid
            misc["vals"] = arg_dict

            trial["state"] = 2   # done
            trial["result"] = {"loss": loss_value, "status": "ok"}
            #trial["refresh_time"] = coarse_utcnow()

            return trial

        dummy_loss = lambda x: None
        param_space = {r["name"]: r["space_func"] for r in hp_records} 
        domain = base.Domain(dummy_loss, param_space)

        rstate = np.random.RandomState()

        # convert runs to Trials
        trial_list = []

        for run in runs:
            # don't trip over inappropriate runs
            if (not "run_name" in run) or (not "hparams" in run) or (not context.primary_metric in run):
                continue

            run_name = run["run_name"]
            arg_dict = run["hparams"]

            loss_value = run[context.primary_metric]
            if context.maximize_metric:
                loss_value = -loss_value

            # extract a unique int from run_name   (parent.childnum)
            tid = run_helper.get_int_from_run_name(run_name)

            trial = make_trial(tid, arg_dict, loss_value)
            trial_list.append(trial)

        # finally, add our trial_list to trials
        trials = Trials()
        trials.insert_trial_docs(trial_list)
        trials.refresh()

        # get next suggested hyperparameter values from TPE algorithm
        tid = run_helper.get_int_from_run_name(run_name)

        min_trials = 3      # before this, just do rand sampling
        seed =  rstate.randint(2 ** 31 - 1)

        if len(trials) < min_trials:
            new_trials = rand.suggest([tid], domain, trials, seed)
        else:
            new_trials = tpe.suggest([tid], domain, trials, seed)

        # apply the suggested hparam values
        trial = new_trials[0]
        arg_dict = trial["misc"]["vals"]
        arg_dict = self.fixup_hyperopt_hparams(param_space, arg_dict)

        return arg_dict

    def fixup_hyperopt_hparams(self, space, orig_hp_dict):
        '''
        the hyperopt library returns values from hp.choice as indexes, instead of 
        actual value, so we correct that issue here.  also, we fixup strings so
        they work correctly when used in command line or config file.
        '''
        hp_dict = dict(orig_hp_dict)

        for prop, value in hp_dict.items():
            value = value[0]     # remove from list of single item
            ss = space[prop]

            if ss.name == "switch":    # hp.choice()
                # convert value from index to actual choice value
                index = 1 + value
                value = ss.pos_args[index]._obj

                if isinstance(value, str):
                    value = value.strip()
                    if " " in value:
                        # surround with quotes so it is treated as a single entity
                        value = '"' + value + '"'
            elif hasattr(value, "real"):
                value = float(value)

            hp_dict[prop] = value

        return hp_dict

