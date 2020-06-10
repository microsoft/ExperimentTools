.. _xt_controller:

========================================
The XT Controller
========================================

The XT controller app provides several services to ML apps running under its control.  Users can elect
to bypass the XT controller and run directly under the control of the backend service by specifying
the --direct flag on the XT run command.

--------------------------------------
XT Controller Services
--------------------------------------

The services provided by the XT controller include:

    scheduling:
        - scheduling runs on the node (up to --concurrent simultaneous runs)
        - creating child runs (from parent runs)
        - running parent prep scripts before starting the child runs

    dynamic hyperparameter search:
        - generating new app config files or command line options for child runs, based on selected search algorithm

    run support:
        - downloading code files at start of runs
        - uploading after files at end of runs
        - mirroring of specified files (copy them to run storage as they change)
        - logging of job and run events

    XT client support:
        - attach/detach to streaming console output
        - cancel runs, jobs
        - get status of node, jobs, and runs
        - restart controller, to simulate a service restart (and test related checkpointing code in user app)

--------------------------------------
XT Controller Processing
--------------------------------------

Here is an outline of processing done by the XT controller:

    - opens MRC file (Multi Run Configuration) to load a list of the script 
      commands to be run, along with the run context (dictionary of property name/value pairs)

    - ensures that no more then `--concurrent` number of run are executing at the same time

    - a PARENT run is a run whose search style is a value other than **single**

    - PARENT run processing:
        - if a parent script was specified for the parent:
            - the PARENT script is run. 
            - after the PARENT script completes, the PARENT run is requeued
        - gets the **run_index** for the next child run, allocated dynamically using MongoDB job data (using the **static** or **dynamic** schedule).
        - the **run_index** is used to select the next script command to run from the MRC file (modulo the number of script commands, if needed)
        - a CHILD run is created from the PARENT run context
        - if the search style of the run is **dynamic**, a hyperparam search is done to determine a hyperparameter set for the child run
        - the CHILD run is started

    - for started runs:
        - download and unzip code (from job and run stores)
        - a "download_before" event is logged for the Run
        - a "started" event is logged for the Run
        - if no RUN script was found, one is created with default settings
        - the RUN script is executed (with environment variables set for the run)

        - as the Run process executes, STDOUT and STDERR output are monitored and redirected:
            - to a "output.txt" file in the current directory
            - to any "xt attach" listeners

        - the Run process does it's user-level logging:
            - hyperparameter settings
            - metric snapshots

        - mirroring of specified files to run storage

        - when the Run process terminates:
            - an "ended" event is logged for the Run
            - the run's AFTER files are uploaded to Run's cloud storage
            - an "capture_after" event is logged for the Run


