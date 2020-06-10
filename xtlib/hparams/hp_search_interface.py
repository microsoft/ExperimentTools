#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# hp_search_interface.py: specifies the interface for hyperparameter search algorithms
from interface import Interface

class HpSearchInterface(Interface):

    def need_runs(self):
        ''' 
        return True if this algorithm requires the summary data for previous runs for its seach call. 
        '''
        pass

    def search(self, run_name, store, context, hp_records, runs):
        '''
        args:
            run_name: 
                name of the run that is about to be launched 
            store: 
                an instance of the XT Store() class, used to access storage
            context: 
                an object containing the run context (a flattened
                subset of the XT config file properties and the cmd-line options)
            hp_records: 
                a list of {name: text, value: text, space_func: space_func} records parsed from 
                the hp search config file (--hp-config).  *space_func* in an instance of 
                a search space function from the hyperopt library, constructed from the *value* text.
            runs: 
                a list of run records.  Each run record is a summary of a completed run, 
                containing the hyperparameters values used in the run, and the resulting metrics.  
                
                info about the primary metric for the run can be found in the context object:
                    context.primary_metric
                    context.maximize_metric

                run records looks like: {run_name: text, hparams: hp_dict, metrics: metrics_dict}

        returns:
            a dictionary containing key/value pairs for each hyperparamer (the hp name and its value)
            to be used for the run about to be launched.

        description:
            typically, a search algorithm reviews the *runs* and then samples a set of hyperparameter
            values from the search space defined by the *hp_records*.   it returns the set of hp
            values as a hp_dict.  
        '''
        pass

