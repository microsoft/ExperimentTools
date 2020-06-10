#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# hp_search_dgd.py: generate the next HP set based on DGD algorithm

import time
import random
import numpy as np
import json
from interface import implements

from xtlib import console
from xtlib import constants
from xtlib.hparams.hp_search_interface import HpSearchInterface

# TERMINOLOGY
# config.py - The file defining the controls and hyperparameters for a run.
# control - A non-tunable variable defined and given a value in config.py.
# hyperparameter - A tunable variable defined in config.py along with one or more potential values.
# hp - Short term for hyperparameter, or prefix for something related to hyperparameters.
# hparam - An object of the Hyperparameter class.
# hp, setting, value - If a hp is a dial, a setting is one mark on the dial, and each mark has a value.
# Setting - The class used to instantiate setting objects. The Hyperparameter class contains a list of these.
# value_str - The string form of the value for some hp setting.
# configuration - A single combination of hyperparameter settings, one setting per hp.
# config - Short term for configuration.
# RunSet - The class encapsulating a list of runs that share the same configuration.


dgd_rand = random.Random(time.time())  # For 'truly' random hyperparameter selection.


class DGDSearch(implements(HpSearchInterface)):
    def __init__(self):
        pass

    def need_runs(self):
        return True
        
    def search(self, run_name, store, context, hp_records, runs):
        '''
        use dgd module to perform dgd search for next hparam set.
        '''
        dgd = DGD()
        dgd.build(store, hp_records, runs, context.primary_metric)
        
        runset = dgd.choose_config()
        arg_dict = dgd.arg_dict_from_runset(runset)

        return arg_dict

class MetricReport(object):
    def __init__(self, metric_dict, primary_metric):
        self.score = float(metric_dict[primary_metric])


class RunSet(object):
    def __init__(self, hp_id__setting_id__list, config_str):
        self.hp_id__setting_id__list = hp_id__setting_id__list
        self.config_str = config_str
        self.runs = []
        self.num_runs = 0
        self.metric = None
        self.id = -1  # For temporary usage.

    def report(self, title):
        sz = "{}  {}".format(title, self.config_str)
        if self.metric is not None:
            sz += "    {:12.5f},  {} runs".format(self.metric, self.num_runs)
        console.print(sz)


class Run(object):
    def __init__(self, run_data, primary_metric):
        self.hpname_hpvalue_list = []
        self.reset_metrics()

        # process hparams subrecord
        if "hparams" in run_data:
            hparams = run_data["hparams"]    
            for prop, value in hparams.items():
                self.hpname_hpvalue_list.append( (prop, value) )

        # process "metrics" subrecord
        if "metrics" in run_data:
            metrics = run_data["metrics"]
            self.add_metric_report(metrics, primary_metric)

        self.normalize_overall_score()

    def reset_metrics(self):
        self.metric_reports = []
        self.overall_score = 0.

    def add_metric_report(self, metrics, primary_metric):
        metric_report = MetricReport(metrics, primary_metric)
        self.metric_reports.append(metric_report)
        self.overall_score += metric_report.score

    def normalize_overall_score(self):
        num_reports = len(self.metric_reports)
        if num_reports > 0:
            self.overall_score /= num_reports


class HyperparameterSetting(object):
    def __init__(self, id, hparam, value):
        self.id = id
        self.hparam = hparam
        self.value = value


class Hyperparameter(object):
    def __init__(self, id, name, value_string, comment_string, in_hp_section):
        self.id = id
        self.name = name
        self.in_hp_section = in_hp_section
        self.value_setting_dict = {}
        self.settings = []
        self.single_value = None
        self.has_multiple_values = False
        value_strs = value_string.split(',')
        self.values = []
        self.default_setting = None

        for value_str in value_strs:
            value = self.cast_value(value_str.strip())
            self.values.append(value)
            self.single_value = value
        self.values.sort()
        for value in self.values:
            self.add_setting(value)
        self.has_multiple_values = (len(self.settings) > 1)
        if comment_string is not None:
            comment_tokens = comment_string.split(' ')
            if comment_tokens[0] == 'default':
                value = self.cast_value(comment_tokens[1])
                if value in self.value_setting_dict.keys():
                    self.default_setting = self.value_setting_dict[value]

    def cast_value(self, value_str):
        if value_str == 'None':
            new_value = None
        elif value_str == 'True':
            new_value = True
        elif value_str == 'False':
            new_value = False
        else:
            try:
                new_value = int(value_str)
            except ValueError:
                try:
                    new_value = float(value_str)
                except ValueError:
                    new_value = value_str
        return new_value

    def add_setting(self, value):
        #assert value not in self.value_setting_dict.keys()
        # allow and ignore duplicate values
        if not value in self.value_setting_dict.keys():
            setting = HyperparameterSetting(len(self.settings), self, value)
            self.value_setting_dict[value] = setting
            self.settings.append(setting)

    def report(self):
        sz = "{} = {}".format(self.name, self.values)
        if self.default_setting is not None:
            sz += "  # default {}".format(self.default_setting.value)
        console.print(sz)


class DGD(object):
    def __init__(self, unit_test=False):
        self.unit_test = unit_test
        self.runsets = []
        self.configstr_runset_dict = {}

    def build(self, store, records, all_runs, primary_metric, report=True):
        self.store = store
        start_time = time.time()

        # Create Hyperparameter objects as defined in config.txt
        self.define_hyperparameters(records)

        self.create_run_objects(all_runs, primary_metric)
        self.finalize_runsets()

        if report:
            self.report()

    def define_hyperparameters(self, records):
        self.name_hparam_dict = {}  # This should go away.
        self.hparams = []

        # REVIEW: we no longer support sections in this call (all hparams are searcharble)
        in_hp_section = True    #  False
        comment = None

        for record in records:

            name_string = record["name"]
            value_string = record["value"]

            if "in_hp_section" in record:
                # legacy text source 
                in_hp_section = record["in_hp_section"]
                comment = record["comment"]

            hp = Hyperparameter(len(self.hparams), name_string, value_string, comment, in_hp_section)
            self.hparams.append(hp)
            self.name_hparam_dict[name_string] = hp

    def create_run_objects(self, run_reports, primary_metric):
        self.runs = []

        for record in run_reports:
            if self.unit_test:
                run = Run(json.loads(record))
            else:
                run = Run(record, primary_metric)
            ignore_run = False
            if len(run.metric_reports) == 0:
                continue  # Skip parent runs.
            # Try to assemble a configuration string for this run.
            hp_id__setting_id__list = []
            for hp_name, hp_value in run.hpname_hpvalue_list:

                # we no longer require that all run-reported hparams are present in the hp-config file
                #assert hp_name in self.name_hparam_dict.keys()  # hparams must not be removed from config.txt
                if not hp_name in self.name_hparam_dict:
                    continue    

                hparam = self.name_hparam_dict[hp_name]
                if not hparam.in_hp_section:  # Ignore controls.
                    continue

                if hp_value not in hparam.value_setting_dict:
                    # REVIEW: why are we landing here?
                    ignore_run = True
                    break  # Skip this run. Its value must have been removed from config.txt.

                if hparam.has_multiple_values:  # Filter to HPs with multiple values.
                    setting = hparam.value_setting_dict[hp_value]
                    hp_id__setting_id__list.append((hparam.id, setting.id))
            
            if ignore_run:
                continue

            config_str = str(hp_id__setting_id__list)

            # Keep this run in a corresponding runset.
            self.runs.append(run)
            if config_str not in self.configstr_runset_dict.keys():
                runset = RunSet(hp_id__setting_id__list, config_str)
                self.configstr_runset_dict[config_str] = runset
                self.runsets.append(runset)
            runset = self.configstr_runset_dict[config_str]
            runset.runs.append(run)

    def finalize_runsets(self):
        for runset in self.runsets:
            runset.num_runs = len(runset.runs)
            # Average the run scores (like reward).
            sum = 0.
            for run in runset.runs:
                sum += run.overall_score
                runset.metric = sum / runset.num_runs

    def report(self):
        self.max_runs_per_runset = 0
        n1 = 0
        for runset in self.runsets:
            num_runs = len(runset.runs)
            if num_runs > self.max_runs_per_runset:
                self.max_runs_per_runset = num_runs
            if num_runs == 1:
                n1 += 1
        console.print("{} runs".format(len(self.runs)))
        console.print("{} runsets".format(len(self.runsets)))
        console.print("{} have 1 run".format(n1))
        console.print("{} max runs per runset".format(self.max_runs_per_runset))
        # for runset in self.runsets:
        #     runset.report()

    def x_at_y(self, y, xs, ys):
        x1 = 0.
        y1 = 0.
        for i in range(len(xs)):
            x2 = xs[i]
            y2 = ys[i]
            if y2 >= y:
                return x1 + (x2 - x1) * (y - y1) / (y2 - y1)
            else:
                x1 = x2
                y1 = y2
        return x1

    def assign_settings(self, hp_config):
        console.print('assigning settings')
        return

    def choose_config(self):
        # Gather the subset of hparams with multiple values.
        self.multivalued_hparams = []

        for hparam in self.hparams:
            if hparam.has_multiple_values:
                self.multivalued_hparams.append(hparam)

        # for hparam in self.multivalued_hparams:
        #     console.print("{} = {}".format(hparam.name, [setting.value for setting in hparam.settings]))

        # If there are no runs yet, just return a random configuration.
        if len(self.runsets) == 0:
            hp_id__setting_id__list = []
            for hparam in self.multivalued_hparams:
                last_setting_id = len(hparam.settings) - 1
                if hparam.default_setting is None:
                    # Select from all settings.
                    setting_id = dgd_rand.randint(0, last_setting_id)
                else:
                    # Select from the default setting, +/- one.
                    default_setting_id = hparam.default_setting.id
                    min_id = default_setting_id
                    if min_id > 0:
                        min_id -= 1
                    max_id = default_setting_id
                    if max_id < last_setting_id:
                        max_id += 1
                    setting_id = dgd_rand.randint(min_id, max_id)
                hp_id__setting_id__list.append((hparam.id, setting_id))
            config_str = str(hp_id__setting_id__list)
            chosen_runset = RunSet(hp_id__setting_id__list, config_str)
            chosen_runset.report('Random runset   ')
            return chosen_runset

        # Find the best runset so far.
        best_runset = self.runsets[0]
        best_metric = best_runset.metric
        for runset in self.runsets:
            if runset.metric >= best_metric:
                best_metric = runset.metric
                best_runset = runset
        best_runset.report('Best runset    ')

        # Build a neighborhood around (and including) the best runset.
        neighborhood = [best_runset]
        for hp_i, hparam in enumerate(self.multivalued_hparams):
            best_hparam_id = best_runset.hp_id__setting_id__list[hp_i][0]
            assert hparam.id == best_hparam_id
            best_setting_id = best_runset.hp_id__setting_id__list[hp_i][1]
            best_setting = hparam.settings[best_setting_id]
            # console.print("For hp={}, best config's setting is {}".format(hparam.name, best_setting.value))

            if best_setting_id > 0:
                neighbor = self.get_neighbor_runset(best_runset, hp_i, best_hparam_id, best_setting_id - 1)
                neighborhood.append(neighbor)
            if best_setting_id < len(hparam.settings) - 1:
                neighbor = self.get_neighbor_runset(best_runset, hp_i, best_hparam_id, best_setting_id + 1)
                neighborhood.append(neighbor)

        # Choose one runset, weighted by how many runs it needs to exceed those of the runset with the most.
        ceiling = max([len(runset.runs) for runset in neighborhood]) + 1
        console.print("ceiling = {} runs".format(ceiling))
        probs = np.zeros((len(neighborhood)))
        for i, runset in enumerate(neighborhood):
            gap = max(0, ceiling - runset.num_runs)
            probs[i] = gap
        sum = np.sum(probs)
        probs /= sum
        for i, runset in enumerate(neighborhood):
            runset.id = i
            runset.report(" {:2d} prob={:6.4f}".format(runset.id, probs[i]))
        chosen_runset = dgd_rand.choices(neighborhood, probs)[0]
        chosen_runset.report(' {:2d} was chosen '.format(chosen_runset.id))
        return chosen_runset

    def get_neighbor_runset(self, best_runset, hp_i, best_hparam_id, new_setting_id):
        hp_id__setting_id__list = best_runset.hp_id__setting_id__list[:]  # Clone the best config.
        hp_id__setting_id__list[hp_i] = (best_hparam_id, new_setting_id)  # Change one setting.
        config_str = str(hp_id__setting_id__list)
        if config_str in self.configstr_runset_dict.keys():
            runset = self.configstr_runset_dict[config_str]
        else:
            runset = RunSet(hp_id__setting_id__list, config_str)
        return runset

    # def apply_config(self, runset, cf):
    #     for hp_i, hparam in enumerate(self.multivalued_hparams):
    #         hparam_id = runset.hp_id__setting_id__list[hp_i][0]
    #         assert hparam.id == hparam_id
    #
    #         value_id = runset.hp_id__setting_id__list[hp_i][1]
    #         value = hparam.settings[value_id]
    #
    #         prop = cf.settings[hparam.name]
    #         prop.value = chosen_setting.value

    def arg_dict_from_runset(self, runset):
        arg_dict = {}

        # first, output single-valued hparams
        for hparam in self.hparams:
            if not hparam.has_multiple_values:
                value =  hparam.single_value
                if value == "$randint()":
                    value = np.random.randint(2147483647)
                arg_dict[hparam.name] = value

        # now, output values used in runset
        for hp_i, hparam in enumerate(self.multivalued_hparams):
            hparam_id = runset.hp_id__setting_id__list[hp_i][0]
            assert hparam.id == hparam_id
            
            value_id = runset.hp_id__setting_id__list[hp_i][1]
            value = hparam.settings[value_id]

            arg_dict[hparam.name] = value.value

        return arg_dict

if __name__ == '__main__':
    dgd = DGD(unit_test=True)
    console.print()
    for hp in dgd.hparams:
        hp.report()
    console.print()
    dgd.runs = []
    dgd.runsets = []
    dgd.configstr_runset_dict = {}
    chosen_runset = dgd.choose_config()
    chosen_runset.report("Chosen runset")


