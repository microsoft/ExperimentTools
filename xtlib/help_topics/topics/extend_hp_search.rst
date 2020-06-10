.. _extend_hp_search:

=====================================================
Adding HP search providers
=====================================================

XT's built-in set of hyperparameter search algorithms can be extended by the user.

The general idea is to write a python class that implements the **HPSearchInterface** interface.

The  **HPSearchInterface** interface is defined as follows::

    # hp_search_interface.py: specifies the interface for hyperparameter search algorithms
    from interface import Interface

    class HpSearchInterface(Interface):

        def need_runs(self):
            ''' 
            return True if this algorithm requires the summary data for previous runs for its seach call. 
            '''
            pass

        def search(self, run_name, cmd_parts, store, context, hp_records, runs):
            '''
            args:
                run_name: 
                    name of the run that is about to be launched 
                cmd_parts: 
                    the list of command-line strings that will be used to start the run 
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

The steps for adding a new hyperparameter search algorithm to XT are:
    - create a python class with that implements each method of the **HPSearchInterface** interface
    - add a provider name and its **code path**  as a key/value pair to the **hp-search** provider dictionary in your local XT config file
    - ensure your provider package is available to XT (in the Python path, or a direct subdirectory of your app's working directory), so that 
      XT can load it when needed (which could be on the XT client machine and/or the compute node)


As an example of how to implement this interface, here is the code for a random hyperparameter search algorithm::

    # hp_search_random.py: perform a random search of the specified parameters
    import hyperopt.pyll.stochastic as stochastic
    from interface import implements

    from xtlib import console
    from.hparams.hp_search_interface import HpSearchInterface

    class MyRandomSearch(implements(HpSearchInterface)):
        def __init__(self):
            pass

        def need_runs(self):
            return False

        def search(self, run_name, cmd_parts, store, context, records, runs, config_text):
            '''
            sample from each HP record and build a dict of hp name/value pairs.
            '''
            arg_dict = {}

            for record in records:
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


To add our new hp search provider to XT, we include the following YAML section to our local XT config file::

    providers:
        hp-search: {
            "myRandom": "extensions.my_random.MyRandomSearch" 
        }

Where **extensions** is the parent directory of the **my_random.py** file)

.. seealso:: 

    - :ref:`Hyperparameter Searching <hyperparameter_search>`
    - :ref:`XT Config file <xt_config_file>`
    - :ref:`Extensibility in XT <extensibility>`
