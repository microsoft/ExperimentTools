.. _hyperparameter_search:

========================================
Hyperparameter Searching 
========================================

This page describes how to do Hyperparameter searching with XT.

The general steps involved in a hyperparameter search:
    - decide which hyperparameters you want to include in the search
    - decide the values you want to search to draw form (the value distribution)
    - launch your job with the run command:
        - specify the hyperparameters and their associated distributions
        - specify the search algorithm with the `--search-type` option
        - specify how many runs (searches) should be performed using the `--runs` or `--max-runs` options
        - specify how many nodes (VM's) to use with the `--nodes` option 
    - analyze the results of your search

----------------------------------------------------------
Parent and child runs:
----------------------------------------------------------

For hyperparameter searches, a single **parent** run is created on each node. The actual search runs
are created as **child** runs of the associated **parent**.  Child run names are of the form::

    <parent run>.<child run number>

For example, **run235.2** would be the 2nd child run for the parent **run235**.

----------------------------------------------------------
Search styles:
----------------------------------------------------------

There are 4 overall approaches or styles that you can choose for searching:
    - **static**: using a search algorithm, where all of the hyperparameter search values are generated before the job is submitted
    - **dynamic**: using a search algorith, where the hyperparameter values for each child run 
    - **multi**: generating your own list of script commands with hyperparameter values as options on those commands
    - **repeat**: repeating your single script command multiple times (and optionally calling a search algorithm at the start of each run)

We will start by explaining the most commonly used styles, **static** and **dynamic**.

----------------------------------------------------------
Value distributions:
----------------------------------------------------------

When providing values to be searched over for a hyperparameter, you can specify them in 
these forms:

    - a comma-separated list of numbers
    - a comma-separated list of strings
    - $disttype(value, value, ...)

The **$disttype** form of the above specifies a value distribution function from the **hyperopt** library.  The following 
distribution types are supported::

    - choice(value, value, ...)
    - randint(upper)                      
    - uniform(low, high)
    - normal(mu, sigma)
    - loguniform(low, high)
    - lognormal(mu, sigma)
    - quniform(low, high, q)
    - qnormal(mu, sigma, q)
    - qloguniform(low, high, q)
    - qlognormal(mu, sigma, q)

The meaning of each of these functions is defined in the **hyperopt** library (see the link at the bottom of this page).

------------------------------------------------
How to specify the hyperparams to search
------------------------------------------------

There are 2 ways to specify the hyperparameters and their associated values:
    - as special command line arguments to your ML script
    - using the `--hp-config` run option to specify a .yaml file 

-------------------------------------------------------------
Specifying hyperparameters in ML app's command line options
-------------------------------------------------------------

XT supports specifying hyperparameters names and spaces to search as command line opions to your ML script, where the space to search is surround by square brackets:

    - name=[value list]
    - name=[$func(values)]

The "func" here must be one of the hyperopt search functions.

Here is an example of specifying a hyperparameter search in the ML script options::

    xt run --target=batch --runs=10 --nodes=5 code\miniMnist.py --lr=[.01, .03, .05] --optimizer=[adam, sgd] --seed=[$randint()]

The above command will create 10 runs on 5 nodes (2 runs per node), each running the miniMnist.py with different values of the `--lr`, 
`--optimizer`, and `--seed` options as returned from the hyperparameter search algorithm.  Since the `--search-type` option was not specified
in the above command, it will default to the value specified in the xt config file.

------------------------------------------------
Format of hp-config search file (.yaml)
------------------------------------------------

When specifying hyperparameters and their values distributions in a .yaml file, it should follow this form::

    hparams:
        name: value
        ...

Here is an example of a .yaml hp-config file::

    hparams:
        seed: $randint()
        lr: [.001, .003, .007]
        optimizer: ["adam", "sgd", "radam"]
        beta1: $uniform(.91, .99)

---------------------------------------------
Enabling a hyperparameter search
---------------------------------------------

A hyperparameter search is enabled when --search-type is set to a supported seach algorithm (on the command line or
in the XT confile file) and a source of hyperparameter search spaces is found in one of the following:

    - the ML app's command line options
    - a hyperparameter search file is specifed with the --hp-config option

---------------------------------------------
Static searches
---------------------------------------------

Static searches are when the total list of search runs is generated by the seach algorithm before the job 
is submitted to the compute target.  Static searches are used when:

    - search-type is **grid** or **random**  (and hyperparameter search is enabled)

Here is an example of an XT commands that result in static search::

    - > xt --search-type=random --hp-config=my_search_spaces.yaml run code\miniMnist.py

For a **grid** search, there is an inherit number of runs (all combinations of all discete hyperparameter values) associated with the 
search.  If you have a small number of discrete hyperparameters and want to search overall all combinations, you can specify, for example::

    xt run --search-type=grid --max-runs=500 --nodes=50 code/miniMnist.py
    
The `--max-runs` option will run all combinations of hyperparameter values in a **grid** search, up to the specified limit (500 in this example).

---------------------------------------------
Dynamic searches
---------------------------------------------

Dynamic searches are when the hyperparameter set (a dict where a value is assigned to each hyperparameter) for each child run is created dynamically on each compute node, 
when the XT controller is ready to start the child run.  Dynamic searches are used when:

    - search-type is a value other than **grid** or **random** (and hyperparameter search is enabled)

Here is an example of XT commands that results in a dynamic search:

    - > xt run --search-type=dgd --hp-config=my_search_spaces.yaml code\miniMnist.py

---------------------------------------------
Scaling the search runs
---------------------------------------------

There are several XT properties that work together to control the scaling of the search runs:

    - nodes  (compute target property or **run** command option)
        - the number of compute nodes to allocate for the search
        - defaults to compute target property

    - runs   (**run** command option)
        - the total number of runs to be performed
        - defaults to 1*nodes 

    - concurrent    (config file property or **run** command option)
        - maximum number of concurrent runs per node 
        - defaults to config file property

    - max-runs    (hyperparameter-search property or **run** command option)
        - limits the number of runs in search (e.g. grid search, where size of the search may be unknown to user)
        - defaults to null (not set) 

---------------------------------------------
How dynamic hyperparameter searching works
---------------------------------------------

On each node, the associated XT controller controls the scheduling of runs.  When a new run slot is available and an HP search run is at the top of the queue:
    - the controller calls MongoDB to determine the next child run for the specified job and node
    - if no child run is found, the **parent** run is terminated
    - otherwise:
        - The XT controller creates a new **child run**
        - the HP search algorithm is given a history of past runs and the hyperparameter distributions to draw a sample from
        - the HP search algorithms returns a hyperparameter set (dictionary of hyperparameter name/value pairs)
        - XT then applies the hyperparameter set to the command line for the run and/or a config file for the run 
        - the child run is then launched
        - the HP search run (**parent**) is requeued for subsequent processing

----------------------------------------------------------
**repeat** style searches
----------------------------------------------------------

The **repeat** style is the simplest.  You simply use a normal **run** command with the `--runs` options set to a number. For example::

    xt run --runs=3 code/miniMnist.py  --epochs=25  --lr=.001

The above command will create 3 child runs, with the specified script options for each.  The difference for the runs will come from
random number generation used by the script, its associated machine learning framework, or its associated libraries.  

When you use the **random** search style, your script can optionally call make an explicit call to a hyperparameter search algorithm to use the history of runs for this job or experiment and return a new hyperparameter set (a set of hyperparameter values) to be applied by the script for the current run. This is done by creating an instance of the xtlib.run.Run class and calling its method:

        get_next_hp_set_in_search(hp_space_dict, search_type)

The **hp_space_dict** is a dictionary of hyperparameter names (as keys) and search distribution strings (as values). **Search_type** is the name of a hyperparameter search algorithm (one of: random, grid, bayesian, dgd).

.. note:: The DGD search algorithm only accepts hyperparameter search distributions in specific formats, as follows::
 
    - [value, value, value] (YAML list of values)
    - $randint()

The DGD algorithm does not the other distribution functions from the *hyperopt* library.

Calling this method is considered an advanced option - the normal way to use a hyperparameter search algorithm is explained above.

----------------------------------------------------------
**multi** search style
----------------------------------------------------------

The `--multi-commands` option essentially allows users to generate and run a set of commands (distributed across the specified set of nodes) 
that comprise their own explict hyperparameter search.

To use the **multi** search style, you first generate your own set of script commands, one per line, each with a specific set of hyperparameter values
specified as options on each command.  Then, you can either:

    - include the commands in your xt_config.yaml file (under a new outer property called **commands**)
    - use the following form of the run command::

            xt run xt_config.yaml

or you can:
    - save them to a text file called, for example **commands.txt**
    - use that file in your run command as follows::

            xt run --multi-commands commands.txt

---------------------------------------------
The `--schedule` **run** option
---------------------------------------------

The `--schedule` option of the run command determines how search runs are allocated to the available nodes for a job.  

The default value of `--schedule` is **static**, which means the search runs are assigned to each node (in a round-robin fashion) before the job is submitted.  
This provides a predictable set of assigments, where each nodes will run about the same number of runs (within 1).

The other value of `--schedule` is **dynamic**, means that each search run is assigned on-demand, when a node is ready to accept another run.  The advantage of
this schedule is that it can use otherwise idle nodes to help finish the remaining searches (in the case of long-running searches or slow nodes).

---------------------------------------------
how to analyze results of a HP search
---------------------------------------------

There are many ways to analyze the results of a HP search, but XT provides 3 recommended tools:

    - the hyperparameter explorer (GUI tool)
    - the XT 'list runs' command
    - the XT 'plot' command

For example, to find the best performing runs in a hyperparamete search whose job id is **job2338** and whose 
primary metric is **test-acc**, you can use the command::

    xt list runs --job=job2338 --sort=metrics.test-acc 

This will list the runs from job2338, sorted such that the best performing run (as measured by **test-acc**) are shown last.

To compare the training curve for some runs of interest (say, run23.1 thru run 23.10), we can use the command::

    xt plot run23.1-run23.10 train-acc, test-acc --x=epoch --break=run --layout=2x5
    
.. seealso:: 

    - `the hyperopt library <http://hyperopt.github.io/hyperopt/>`_
    - :ref:`XT controller<xt_controller>`
    - :ref:`explore command <explore>`
    - :ref:`list runs command <list_runs>`
    - :ref:`plot command <plot>`
    - :ref:`Understanding the XT Config file <xt_config_file>`

