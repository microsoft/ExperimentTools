.. _run:  

========================================
run command
========================================

Usage::

    xt run [OPTIONS] <script> [script-args]

Description::

        The run command is used to run a program, python script, batch file, or shell script on
    one of following compute services:

    - local (the local machine)
    - pool (a specified set of computers managed by the user)
    - Azure Batch
    - Azure ML
    - Philly

Options::

  --after-upload             flag     when true, the after files are upload when the run completes
  --cluster                  str      the name of the Philly cluster to be used
  --code-upload              flag     when true, code is uploaded to job and download for each run of job
  --concurrent               int      the maximum concurrent runs to be allowed on each node
  --data-action              str      the data action to take on the target, before run is started
  --data-upload              flag     when true, the data for this job will be automatically upload when the job is submitted
  --data-writable            flag     when true, a mounted data path can be written to
  --description              str      your description of this run
  --direct-run               flag     when True, the script is run without the controller (on Philly or AML)
  --distributed              flag     when True, the multiple nodes will be put into distributed training mode
  --docker                   str      the docker entry to use with the target (from one of the entries in the config file [dockers] section
  --dry-run                  flag     when True, the planned runs are displayed but not submitted
  --escape                   int      breaks out of attach or --monitor loop after specified # of seconds
  --experiment               str      the name of the experiment to create this run under
  --fake-submit              flag     when True, we skip creation of job and runs and the submit (used for internal testing)
  --hold                     flag     when True, the Azure Pool (VM's) are held open for debugging)
  --hp-config                str      the path of the hyperparameter config file
  --jupyter-monitor          flag     when True, a Jupyter notebook is created to monitor the run
  --low-pri                  bool     when true, use low-priority (preemptable) nodes for this job
  --max-minutes              int      the maximum number of minutes the run can execute before being terminated
  --max-runs                 int      the total number of runs across all nodes (for hyperparameter searches)
  --model-action             str      the model action to take on the target, before run is started
  --model-writable           flag     when true, a mounted model path can be written to
  --monitor                  str      how to monitor primary run of the new job [one of: new, same, none]
  --multi-commands           flag     the script file contains multiple run commands (one per line)
  --nodes                    int      the number of normal (non-preemptable) nodes to allocte for this run
  --parent-script            str      path of script used to initialize the target for repeated runs of primary script
  --queue                    str      the name of the Philly queue to use when submitting this job
  --resume-name              str      when resuming a run, this names the previous run
  --runs                     int      the total number of runs across all nodes (for hyperparameter searches)
  --schedule                 str      specifies if runs are pre-assigned to each node or allocate on demand [one of: static, dynamic]
  --search-type              str      the type of hyperparameter search to perform [one of: random, grid, bayesian, dgd]
  --seed                     str      the random number seed that can be used for reproducible HP searches
  --sku                      str      the name of the Philly SKU to be used (e.g, 'G1')
  --submit-logs              str      specifies a directory to which log files for the submit are saved
  --target                   str      one of the user-defined compute targets on which to run
  --use-gpu                  bool     when True, the gpu(s) on the nodes will be used by the run
  --username                 str      the username to log as the author of this run
  --vc                       str      the name of the Philly virtual cluster to be used
  --vm-size                  str      the type of Azure VM computer to run on
  --workspace                str      the workspace to create and manage the run
  --xtlib-upload             flag     when True, local source code for xtlib is included in the source code snapshot 

Arguments::

  script         the name of the script to run
  script-args    the command line arguments for the script

Examples:

  run the script miniMnist.py::

  > xt run miniMnist.py

  run the linux command 'sleep3d' on philly::

  > xt run --target=philly --code-upload=0 sleep 3d

