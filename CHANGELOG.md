# What's new
Below is our list of changes for each build of XTLib. 

### Jun-09-2020 (version 1.0.0)
[] Same as version 1.0.0.rc2

### Jun-09-2020 (version 1.0.0.rc2)
[] misc fixes:
    [done] restricted users to upload only to a share location
    [done] fixed docker login / logout commands
    [done] fixed errors with xt view log
    [done] fixed errors with xt view status
    [done] removed hardcoded windows paths
[] misc improvements
    [done] simplified templates for xt config --create command
    [done] added workspace import / export commands
    [done] default mongodb instances are now free tier

### Jun-08-2020 (version 1.0.0.rc.ie)
[] quicktest:
    [done] added needed services to top of xt quicktest config file
    [done] auto delete/import of xt-demo workspace
    [done] fix bug in rerun command (get correct job_id from prev run)
    [done] run both BASIC and ADV xt demos
[] xt demo:
    [done] export new set of jobs/runs used by xt demo to: xt_demo_archive.zip
    [done] create demo cmd: import xt_demo workspace from xt_demo_archive.zip if not already present
    [done] more consistent key handling (q, control-c, and escape all stop demo)
    [done] prompt user with keyboard shortcuts if input is unrecognized
    [done] fix error messages for arrow keys
    [done] update demo to use new job/run/experiment names
[] new import cmd
    [done] single workspace, subset by tags or runlist
    [done] write storage and mongo jobs, workspace, runs to .zip output file
[] new export cmd
    [done] import to new target workspace name (or keep same name?)
    [done] write storage and mongo jobs, workspace, runs from .zip input file
[] misc:
    [done] list jobs cmd: expand options from single name to list of names (experiment, target, service-type, username)
    [done] list runs cmd: expand options from single name to list of names (job, experiment, box, target, service-type, username)
    [done] remove temp dir used by runner (w/ tempfile.TemporaryDirectory context class)
    [done] enable progress feedback on upload/download commands


### Jun-03-2020 (version 1.0.0.rc.rc)
[] remove c:\ paths from code
    [] use primary drive: psm.py
    [] use ~/.xt: default_config.py, xt_config_file.rst


### Jun-02-2020 (version 1.0.0.rc.dj)
[] delete workspace:
    [done] delete associated jobs from storage
    [done] delete associated jobs from mongo

### May-29-2020 (version 1.0.0.rc1)
[] updated docs
    [done] integrated all doc changes for 1.0.0.rc
    [done] removed leftover docs and references to txt
    [done] updated installation instructions for 1.0.0.rc1
    [done] reordered topics, removed mini_mnist
    [done] fixed all warnings

[] updated config API
    [done] removed post install scripts
    [done] updated config API to support merging the internal config file on demand

### May-28-2020 (version 1.0.0.rc)
[] updated advanced demo
    [done] updated/removed steps that refer to previously created artifacts (runs, jobs)
    [done] labelled philly specific steps so they get skipped depending on demo parameters
 
[] removed sensitive assets, general cleanup
    [done] removed hardcoded IPs and references to Philly and sandbox resources
    [done] removed extraneous files and updated .gitignore

### May-26-2020 (version 0.1.1.od)
[] fix mapping of XT_OUTPUT_DIR for multi-node jobs
    [done] batch: add RUN_NAME arg to wrapper.sh & use it
    [done] pool/aml: add RUN_NAME arg to wrapper.sh & use it
[] Pool bugs 
    [done] bug fix: PSM not transferring psm.py when slashes are wrong
    [done] bug fix: when monitoring a POOL job, we sometimes think job is completed when it is not
    [done] bug fix: PSM - don't process entry until copy of it has completed
    [done] bug fix: don't try to remove local mapping paths with "rm" 
    [done] bug fix: if remote/local box is running old version of psm.py; restart PSM process (will update psm.py)
    [done] robust: psm.py - improved logging and exception handling
    [done] robust: catch exceptions in PSM on processing a request (log error & skip entry)
    [done] robust: when starting PSM, client must verify it really is running or issue an error    

### May-23-2020 (version 0.1.1.sic)
[] set_internal_config
    [done] create default_config.yaml in XT resource dir on-demand (from helpers\default.config.yaml)
    [done] implement merge_internal_xt_config()
    [done] cleanup of merge_configs()
    [done] pretty YAML dump to text
[] quick test
    [done] bring in test_base from xt_dilbert branch (captures/compares cmd results)
    [done] bring in tagTests from xt_dilbert branch (improved tag command testing)
    [done] add config tests (merge config  API)

### May-06-2020 (version 0.1.1.hs)
[] hyperparameter search
    [done] only use static searches if args_prefix is specified (don't use when app needs generated runset file)
    [done] change generated runset file to be YAML (with outer property: hyperparameter-runset)
    [done] rename outer property of hp-config to "hyperparameter-distributions"
    [done] change miniMnist to use runset file, if found
    [done] add --tag-job switch to miniMnist.py

[] misc
    [done] remove obsolete code from qfe and other modules
    [done] fix version logging for child runs

### May-16-2020 (version 0.1.1.ie)
[] xt demo:
    [done] export new set of jobs/runs used by xt demo to: xt_demo_archive.zip
    [done] create demo cmd: import xt_demo workspace from xt_demo_archive.zip if not already present
    [done] more consistent key handling (q, control-c, and escape all stop demo)
    [done] prompt user with keyboard shortcuts if input is unrecognized
    [done] fix error messages for arrow keys
    [] update demo to use new job/run/experiment names

### May-15-2020 (version 0.1.1.ie)
[] new import cmd
    [done] single workspace, subset by tags or runlist
    [done] write storage and mongo jobs, workspace, runs to .zip output file
[] new export cmd
    [done] import to new target workspace name (or keep same name?)
    [done] write storage and mongo jobs, workspace, runs from .zip input file
[] misc:
    [done] list jobs cmd: expand options from single name to list of names (experiment, target, service-type, username)
    [done] list runs cmd: expand options from single name to list of names (job, experiment, box, target, service-type, username)
    [done] remove temp dir used by runner (w/ tempfile.TemporaryDirectory context class)
    [done] enable progress feedback on upload/download commands
    
### May-15-2020 (version 0.1.1.ie)
[] new import cmd
    [] single workspace, subset by tags or runlist
    [] write storage and mongo jobs, workspace, runs to .zip output file
[] new export cmd
    [] import to new target workspace name (or keep same name?)
    [] write storage and mongo jobs, workspace, runs from .zip input file

### May-14-2020 (version 0.1.1.qt)
[] demo changes (for quicktest)
    [done] substitute new runs for runs used in demo that have been deleted 
    [done] raise exception in xt demo if error returned from running system cmd
    [done] --nomonitor and --nogui switches for xt_demo 

### May-14-2020 (version 0.1.1rc)
[] run/job reports:
    [done] bug fix: list runs --export 
    [done] bug fix: list jobs --export 
    [done] list runs: for logged hparams, auto-adjust precision to show all decimal digits of number (up to 15)

### May-06-2020 (version 0.1.1.hs)
[] hyperparameter search
    [done] only use static searches if args_prefix is specified (don't use when app needs generated runset file)
    [done] change generated runset file to be YAML (with outer property: hyperparameter-runset)
    [done] rename outer property of hp-config to "hyperparameter-distributions"
    [done] change miniMnist to use runset file, if found
    [done] add --tag-job switch to miniMnist.py
[] misc
    [done] remove obsolete code from qfe and other modules
    [done] fix version logging for child runs

### May-06-2020 (version 0.1.1cs)
[] create service template cmd:
    [done] get user's object id from AAD graph and inject into template
    [done] add flags for various template pieces: base, batch, aml, all

### Apr-30-2020 (build v1.1)
[done] Fix demo nav keys issue

### Apr-30-2020 (build v1.0)
[done] Correctly import the fule_utils module
[done] Correctly pass in a prefix parameter to utility to make temp folder

### Apr-30-2020 (build v.199)
[done] Added the psm module to setup.py

### Apr-30-2020 (build v.198)
[done] bug fixes for running quicktest under linux
[done] bug fix for xt demo keyboard handling 
[done] upgrade to rpyc 4.1.2 (Microsoft security advice)
[done] use save_load() (vs. load) for ruamel_yaml (Microsoft security advice)
[done] fix special key flag for key press checker on windows
[done] perf: don't load AML packages in Run class unless app in running on AML
[done] fix bug in formatting of value (list runs)
[done] separate logging of xt_version, xt_build (run log)
[done] add --username for list jobs, list runs command


### Apr-27-2020 (build v.197)
[] new root flag
    [done] --new specifies that the current command should be run in a new console window
    [done] --echo echos the cmd at the start of execution

[] monitor command:
    [] works on all backends: philly, batch, aml, pool
    [done] control-c: kill job with confirmation
    [done] can stop with escape
    [done] can stop with control-c (and optionally cancel job or run)
    [done] new run command --monitor option (monitors the primary run of new job)
    [done] new general.monitor config file property (for --monitor) on run cmd
    [] remove obsolete:
        [done] attach command
        [done] show-controller (config property & run option)
        [done] attach (config property & run option)
        [done] stop controller command

[] plot command:
    [done] consistent ordering of groups 

[] view metrics command:
    [done] 1st argument: support for list of run names
    [done] 2nd argument: support for optional list of metrics to display
    [done] --steps option: only show specified reports
    [done] --metrics option: only show specified metrics
    [done] --hparams option: display name/value of specified hparams for each run 
    [done] --merge flag: merge metrics from multiple metrics sets (by step_name)

[] misc:
    [done] on windows, also support curl config file (for problem debugging)
    [done] fix consistency of miniMnist model and mnist data paths (local vs. cloud)
    [done] bug fix for view blob command

### Apr-22-2020 (build v.196)
[done] scale testing: for hparam search, getting LOTS of hyperparameter search
[done] make --username a visible option for run command 
[done] fix error where we can't display result from Philly when its HTML (vs. JSON)
[done] make all mongo db access use retry function
[done] add in-memory caching of run history for hyperparameter searching

### Apr-20-2020 (build v.195)
[done] xt run command: move options to right of "run" keyword
[done] fix sync_run_ssh when called from linux

[] update docs:
    [done] finish starting new project help topic

### Apr-19-2020 (build v.192)
[done] fix issues with local linux runs 

### Apr-19-2020 (build v.191)
[] misc:
    [done] fix problem with plot command and col in split data frames
    [done] fix problem with first-time storage
    [done] server keys: add home directory location as alternate to local
    [done] always show stack trace when exception being thrown is not an XT exception
    [done] don't add "xt" in front of service names in 'create team' template
    [done] fix location and tenant id in 'create team' template

[] update docs:
    [done] update hparam processing help topic
    [done] added tensorboard help topic


### Apr-15-2020 (build v.190)
[done] fix bug where "show-controller" attempted on linux local machine
[done] fix plot command bug regarding selecting x_col 


### Apr-14-2020 (build v.187)
[] controller restart support:
    [done] mongo db tracks which run index and run_name each node is working on
    [done] controller calls mongo_db to get next_child_run (name and run_index)
    [done] new 'restart controller' command 
    [done] new testRunIndexes (unit testing for above)

[] other:
    [done] fix bug with plot cmd: correctly use logged step name from 2nd metric set as x_col
    [done] consistency: renamed XT added metrics to:  __step_name__, __time__, and __index__


### Apr-12-2020 (build v.186)
[] list runs cmd:
    [done] FIXED bug with uppercase-hdr config property
    [done] ADDED: support for "metrics.*" in columns
    [done] API EXPAND: run.log_metrics(): add "step_name" and "stage" params
    [done] API BREAK: remove run.log_metric()  (use run.log_metrics() instead)

[] plot cmd:
    [done] ADDED: --plot-args (pass thru name/value pairs to matplotlib)
    [done] ADDED: --legend-args (pass thru name/value pairs to matplotlib)
    [done] example of above: xt plot job7600 train-acc, test-acc --aggre=mean --group=job 
    
    --legend-args={loc=center}, {font=arial} 
    --plot-args={linestyle=--}, {marker=o}, {ms=15}
    
    [done] FIXED: fix bug when plotting only col in 2nd dataset and using aggregation
    [done] RENAMED: rename of plot options: range_type => shadow_type, range_alpha => shadow_alpha
    [done] ADDED: --shadow-type option (value is one of: "none", "pre-smooth", "min-max", "std", "var", "sem")
    [done] plot cmd: use logged step_name when available as default x_col
    [done] ADDED support for options: colors, color_map, and color_steps
    [done] REMOVED support for options: plot-type, alpha, cap-size, edge-color, marker-shape, marker-size 

[] storage/mongo pairing, versioning, and sequence id generation
    [done] mark paired_storage in mongo, and paired_mongo in storage
    [done] use mongodb to allocate all sequential unique numbers (jobs, runs, child runs, run_end_id)

[] other:
    [done] tensorboard workaround to cause flushed files to be written to azure blob storage (XT_OUTPUT_MNT)
    [done] add tensorboard scalar logging to XT Run (will also log to Philly tensorboard storage, as appropriate)
    [done] ADDED: user now opts-in for using XT Controller remote control (config file: general/remote-control) 


### Apr-04-2020 (build v.184)
[done] fix a few small bug with v.183

### Apr-03-2020 (build v.183)
[] default to xt basic mode
    [done] general.advanced-mode: False
    [done] replace "TXT" occurances with "XT" in basic mode docs 

[] output mapping:
    [done] add XT_OUTPUT_MNT to batch and AML

[] list runs command:
    [done] fix "-all" in list runs (broken by --last)
    [done] --available: do NOT filter by user-specified column list

[] plot command:
    [done] help: show set of values for option (e.g., std, var, ...)
    [done] fix: --legend-titles="abc def" (improved but official spec should be single quotes)
    [done] remove quotes from legend titles
    [done] add: --x-label 

[] run command:
    [done] feedback: output job first, without upper case

[] philly from linux:
    [done] XT cannot assume that the logged in username works for philly...

[] specifying strings for option and argument values
    [done] added support for {} as alternative to single and double quotes
    [done] updated cmd_options help topic
    
### Mar 31 2020 (build v.182)
[] misc:
    [done] allow TXT user to overwrite "target" and "workspace" options
    [done] new --error-bars option for plot command
    [done] repair --smoothing-factor option for plot command
    [done] new plotTests for quick-test
    [done] new --add-columns option for list runs command
    [done] add support for .yaml config file as target of run command
    [done] add support for 'commands' property in config file
    
[] update docs:
    [done] update controller help topic
    [done] topic: XT job submission and running
    [done] created: manual_service_creation topic
    [done] renamed/updated creating_xt_services
    [done] updated: how_xt_works


### Mar 28 2020 (build v.180)
[done] experimental tiny XT (txt.exe)

### Mar 28 2020 (build v.179)

[done] dilbert stuff:
    [done] move run context file to working-dir
    [done] add to, but never overwrite PYTHONPATH
    [done] set qfe.explict_options for ags passed in thru API
    [done] fix name checking at qfe.py line 974 ("-" vs. "_")
    [done] some way to validate args passed to run api?   ensure no unknown names are used.

[done] plot revival:
    [done] plot <run source> (can now be list of: run name/wildcard/range, job name/range, experiment name)
    [done] plot: ensure working: 
        [done] --break=cols
        [done] --break=runs
        [done] --break==cols,runs 
        [done] with or without an explicit --layout option 
    [done] plot grouping and aggregation
        [done] --aggregate=mean
        [done] --group-by=node  
        [done] see "xt help plot" for more info
    [] after aggregation smoothing 
    [] aggregation/smoothing shadows


### Mar 26 2020 (build v.178)

[] misc:
    [done] add code.working-dir property to control where run executes
    [done] JIT command piping (so we don't trip over SSH / debugger console and try to read input)
    [done] ensure 8x distributed AML runs OK (and only primary does HP/stats logging)
    [done] for direct-mode apps that use Run(), make needed calls for status changes and QUEUED/DURATION times

[] redesign XT client code 
    [done] new 'restart controller' command to simulate a service restart
    [done] get access to controller connnect thru new backend API: get_client_cs()
    [done] use open port on philly to connect XT controller/client
    [done] new small/clean xt_client.py 

[] redesign restart support in controller:
    [done] mongo db allocates "runs_remaining" index UNLESS node has been restarted

### Mar 24 2020 (build v.177)
[] misc:
    [done] update docs (graduating_sandbox, create_team doc strings)
    [done] fixed problem with empty option-prefix HP processing
    [done] fixed several issues with RunTests
    
### Mar 22 2020 (build v.174)
[] support for target-specific setup dependencies
    [done] rename "environments" section to "dockers"
    [done] rename target property "environment" to "docker"
    [done] new "setups" section that holds "setup" records:
        [done] properties: activate, conda-packages, pip-packages
    [done] move python-packages and conda packages to setup records
    [done] use setup.activate cmd for activating conda for controller (and subsequent runs)

[] misc:
    [done] pure syntax errors now show syntax for recognized cmd after error msg

[] rework controller for local, pool boxes:
    [done] only run controller JIT, for specific job on box
    [done] always exit as soon as job is done
    [done] remove "restart controller cmd"
    [done] remove the controller scripts

[done] new quick-test: runsTest
    [done] 100 fake-submit combo of runs test (sampled from 4000)
    [done] 5 actual-submit
    [done] compare results to approved copy of log files
    [done] zip/unzip approved files as appropriate

[] event logs:
    [done] new 'view events' command to view formatted record from xt_info.log
    [done] use logging library to create event logs:
        [done] xt_events.log
        [done] controller_events.log
        [done] quick_test_events.log

[] clean up submit-time hparam processing
    [done] integrate new client-side HP processing code 
    [done] finalize run number control: nodes, runs, concurrent, max-runs
    [done] ensure child runs created unless search_style == "single"

[] security issues:
    [done] fixed issues around box_secret passed from XT client to controller
    [on-hold] xt client talking to controller: use only public half of "xt-servercert"

### Mar 14 2020 (build v.173)
[done] box secrets:
    [done] replace token-based authentication in XT controller with box_secret
    [done] store box_secrets for services in job props (mongo) 
    [done] store box_secrets for pool boxes in local file

### Mar 13 2020 (build v.172)
[] misc:
    [done] new "create team" command (generates an Azure template to create team set of resources)
    [done] added schema for XT config files and validation of default/local files on load
    [done] cmd rename: xt stop controller (was kill controller)
    [done] cmd rename: xt clear credentials (was kill cache)
    [done] authenticate XT controller requests using AAD token to match owner user_principle_name
    [done] use client_cert and server_cert from vault for communication between XT client and controller 
[] docs:
    [done] updated internal page on build/release of documentation
    [done] added new internal page on "remote control" (xt client talking to xt controller)


### Mar 02 2020 (build v.165)
[] misc:
    [done] fix multi-run plot bug
    [done] support for "group" in list runs
    [done] add "number-group" option to list runs
    [done] remove use of 'xt meta' for creds in controller
    [done] regenerate sandbox keys
    [done] new "xt grok" command to start XT Grok in browser
[] team support:
    [done] add xt-team name to general config section
    [done] change cache server/client to get/set cache settings by team-name
    [done] create a new help topic for "Adding a new team to XT"

### Feb 21 2020 (build v.164)
[] misc:
    [done] support for data-local when running in pool (substitutes for data-store-path)
    [done] support for YAML hp-search files
[] support for credential caching (placeholder for azure SDK support)
    [done] cache_client.py
    [done] cache_server.py
[done] provider support:
    [done] add to config YAML
    [done] implementation and unit tests: storage providers
    [done] implementation and unit test: hp search algorithms
    [done] implementation: command providers
    [done] implementation: compute providers
[] update docs
    [done] extensibility in XT (cover extentsibility thru services and providers)
    [done] how to add new compute provider
    [done] how to add new command provider
    [done] how to add new hp search provider
    [done] how to add new storge  provider
    [done] credential caching and 'kill cache' command (explain placeholder for Azure SDK support)
    [done] philly credential / curl config file 
    [done] complete hyperparameter_search help topic (including new YAML support and hyperopt distribution space functions)


### Feb 08 2020 (build v.163)
[done] convert xt controller communication to SSH
    [cone] create certificate and store in key value
    [done] download cert on XT client and XT Controller
    [done] pass cert to rpyc for SSH encryption

### Feb 06 2020 (build v.162)
[] remove secret credentials into Azure key vault
    [done] support for browser authentication (without device code)
    [done] put creds into vault; replace with "$vault" in config file
    [done] auto expand values of "$vault"
    [done] add backup vault (azure storage, until credential caching is working)

### Feb 04 2020 (build v.161)
[done] xt_config file
    [done] renamed "data.data-store" to "data.data-share-path"
    [done] renamed "model.model-store" to "model.model-share-path"
    [done] renamed "after-files.after-files" to "after-files.after-dirs"
    [done] support for --create=template (one of: philly, aml, batch, pool, empty)
    [done] add "xt_config_file" help topic

### Feb 03 2020 (build v.160)
[] update docs
    [done] bi-directional cross links between list runs/columns/filters
    [done] bi-directional cross links between list jobs/columns/filters
    [done] ensure plot cmd is covered by docs
    [done] help topic for xt cmd line piping
    [done] added "see_also" command decorator (generates "see also" entries at bottom of help page)
    [done] added "image" property for examples (generates inline image in help page)
[] cmd line piping
    [done] can pipe RUNS and JOBS from one XT cmd to another; examples:
        xt list runs --status=created --target=philly | xt set tags * dead
        xt list runs --filter="metrics.test-acc>.75" | xt plot * test-acc
    [done] add to xt_demo
[] enhanced plot cmd
    [done] implement
    [done] add to demo


### Jan 27 2020 (build v.159)
[done] stdout control:
    [done] new console.py: add Philly Tools type of console control: none, normal, diagnostics, detail (low level diagnostics) 
    [done] combine this with --timing, so that --output >= 2 always shows timing information (nice!)
    [done] REMOVE GLOBAL FLAGS and CONFIG FILE properties: --diagnostics, --timing
    [done] ADD GLOBAL FLAG and CONFIG FILE property: --console
[done] faster queries (list runs, list jobs):
    [done] add code to detect that RUNS or JOBS mongo fixup and perform the fixups
[done] column names (list runs, list jobs):
    [done] for consistency, changed all standard col names to use "_" instead of "-"
    [done] for more readable default reports, changed "run_name" to "run", "job_name", to "job", "search_type", to "search"
[] bugs/misc:
    [done] fix bug in "list runs -all" ("-all error not caught.  maybe display "did you mean --all?")
    [done] fix bug: xt list runs run1772.1  (single run not found?)
    [CNR] do NOT automatically blank any zero values anymore 
    [done] fix "portal_url" col for "view status --target=aml" (was blank, now set to info returned by batch)
    [done] code cleanup: broke large utils.py into smaller modules
    [done] new command: view portal <target>
    [done] RENAMED run option "--commands" to "--multi-commands"
    [done] EXPAND SUPPORT: for "xt ssh name" (where name can be the name of a philly run)
    [done] implement custom format codes: $bz, $to, $do
    [done] --target=all option in "xt view status" to step thru all targets
    [done] add AML exper_name, run_number to MONGO data for runs
    [done] add --export to "view metrics" 
    [done] --queued, --active, --completed options to filter "xt view status" 
[done] improved tag filtering
    [done] --tags-all filter options on list runs, list jobs (match existance of all specified tags)
    [done] --tags-any filter options on list runs, list jobs (match existance of any specified tags)
[done] update docs
    [done] unify console help topics with HTML help topics (all help topics are now .rst files)
    [done] update docs: custom column formating codes: "$bz" (blank out zeros), "$do" (date portion of datetime, "$to" (time portion of datetime))
    [done] add new arguments for "help": "topics" and "internals"
    [done] update docs: for FILTERS and COLUMNS, must now prefix hyperparameter names with "hparams." and metrics with "metrics."
[done] view tensorboard
    [done] new --template for 'view tensorboard' cmd (allows user to specify log naming template based on run properties, hparams, metrics, tags)!
[] xt_demo
    [done] add uses of "view portal --browse" cmd to demo
    [done] submit a parallel training run
    [done] argument support: list of step numbers/ranges and --auto
[done] faster startup 
    [done] make all azure libraries load-on-demand
    [done] make a "load on demand" wrapper class for Store class
    [done] measure progress: for "xt help" cmd: before 4.0 secs, after 1.2 secs (but azure-dependent cmds only slightly faster)

### Jan 22 2020 (build v.156) 
[] misc:
    [done] added "--browse" to "xt extract" command (and added usage to xt_demo)
[] faster queries (list runs, list jobs):
    [done] add code to log following RUN properties to storage AND mongo:
        [done] start_time (when run actually starts on node)
        [done] queue_duration (difference between start_time and create_time)
        [done] run_diration (difference between end_time and start_time)
        [done] is_child, is_parent, is_outer
    [done] add DYNAMIC job columns: job_status, running_nodes, running_runs, completed_runs, error_runs

### Jan 21 2020 (build v.155) 
[done] support for tags on jobs and runs:
    [done] set tags <name list> <tag list>
    [done] clear tags <name list> <tag list>
    [done] list tags <name list>
    [done] remove METRICS and HPARAMS "flattening" code for mongo info (overwriting std run property values)
    [done] use nested TAGS, HPARAMS, and METRICS in report COLUMNS: tags.urgent, metrics.test-acc, hparams.epochs, etc.
    [done] use nested TAGS, HPARAMS, and METRICS in report FILTERING: tags.urgent, metrics.test-acc, hparams.epochs, etc.
    [done] new filter operators: :regex:, :exists:, :mongo:
[done] faster queries (list runs, list jobs):
    [done] get mongo sort working with first/last so that we can sort and LIMIT records on server (much faster)
    [done] add code to log following RUN properties to storage AND mongo:
        [done] run_num
        [done] path
        [done] script
    [done] add code to log following JOB properties to storage AND mongo:
        [done] job_num
    [done] cleanup LISTBUILDER code (move RUN-specific code to run_helper.py, rename REPORTBUILDER)
    [done] cleanup IMPLSTORAGE code (move JOB-specific code to job_helper.py)
[] misc:
    [done] xt view mongo: also support jobname here
    [done] update quick-test and demo for "run" keyword required
    [done] rename "remove" cmd to "delete blobs"
    [done] turned OFF stack traces in default config file
    [done] xt list runs --work=xxx (workspace being ignored)
    [done] make "run" keyword required (avoid confusion for unknown cmd vs. can't find script)
    [done] view tensorboard: open new cmd window in the temp tensorboard_reader dir
    [done] view tensorboard: set logdir to "batch" to short paths in TB UI
[done] improved error reporting
    [done] add --syntax option to help comannd (only show syntax)
    [done] add --args option to help comannd (only show syntax, args, and options)
    [done] created 8 new classes of errors; moved error-related functions into new file: errors.py
    [done] reclassify all user_error() calls into 1 of new error classes
    [done] on syntax-related errors, show command syntax, args, and options

### Jan 17 2020 (build v.154) 
[done] list jobs enhancements:
    [done] log additional properties to job_info (and mongo)
    [done] format and filtering using ReportBuilder code
    [done] default config file: renamed "reports" to "run-reports"
    [done] default config file: added "job-reports"
[done] misc
    [done] fix "missing log_interval HP" error in xt_demo (xt explore job2651)
    [done] added --export=file option to 'list runs' and 'list jobs' (creates a TAB separated file)
    [done] add support for filtering report rows using symbols: $none, $empty, $true, $false
    [done] fix "gpu not found" for batch
    [done] clean up --num-nodes/--low-pri confusion: change "--low-pri" to boolean 
    [done] add documentation to 'list runs' about custom column names and formatting codes

### Jan 14 2020 (build v.153) 
[done] misc:
    [done] pass username to app via env var XT_USERNAME
    [done] support custom column format code in reports.columns of config file
    [done] correct null fig error in xt explore
    [done] give controller more time to restart (fix 'no connection' error)
    [done] fix bug in generated HP config file name/downloading
    [done] fix "command too long" error when viewing tensorboard of LOTS of runs
    [done] remove exception catching in controller (any error should be fatal and exit the controller app, not hold the VM open)
    [done] remove display on per-node cmds and run names unless search-type = "grid"
    [done] add optional "::dest-dir" for code directories in code section of config file
    [done] added miniMnist.py to quick-test for selected usage (and updated xt_config.yaml for quick-test as appropriate)
    [done] fix "can't find GPU" issue on Philly (caused by torchvision==0.4.1 dependency; changed to ">=0.4.1" to fix)
    [done] added "pip freeze" in startup script for Philly, Batch, AML (for easier debugging of package dependencies)
    [done] adjusted cmdlineTest\xt_config.yaml to get torchvision working correctly on philly, batch, and aml 
    [done] fix "missing generate" bug for generating doc pages (made "generate_help()" function a hidden command)
    [done] display created ws/run_name when running simple job on batch

### Jan 08 2020 (build v.152) 
[done] Hyperparameter Explorer 
    [done] integrate latest HX
[done] convert config file to YAML
    [done] xt_default.yaml
    [done] cmdlineTest/xt_config.yaml
    [done] quick-test/xt_config.yaml
    [done] demo/xtconfig.yaml
    [done] xt config  (create/edit yaml, remove 'local' option)
[done] 'list runs' adjustments:
    [done] allow column renaming in 'list runs' (use "actual_col_name=new_name:precision" form of column name in reports.columns)
    [done] rename "target" to "script" (stdcol)
    [done] rename "compute" to "target" (stdcol)
[done] target machine prep adjustments:
    [done] change xt_config: code.code-dir to code.code-dirs  (make it an array of string)
    [done] move 'pip-packages', 'conda_packages', and 'env-vars' from aml-options to general 
    [done] support 'pip-packages', 'conda_packages', and 'env-vars' for BATCH
    [done] support 'pip-packages', 'conda_packages', and 'env-vars' for PHILLY
    [done] for pip-packages, support "name==*" to match 'pip freeze' version of package
[done] cleanup of blob/file commands with regard to file SHARES:
    [done] add --share=name option (upload, download, delete, dir cmds)
    [done] remove support for "files" (upload, download, delete, dir cmds)
    [done] remove keyword argument for blobs/files/data/model (upload, download, delete, dir cmds)
    [done] rename "dir" cmd to "list blobs"
[done] misc:
    [done] add "console_scripts" section to setup.py to create xt.exe on install (or run install.bat for xt development work)
    [done] correct timing calculations for --timing
    [done] add timeit.py internal tool for clocking elapsed time of windows/linux command
    [done] fix problem with xt_demo where no initial data/model exist for upload to share

### Dec 21 2019 (build v.151)
[done] DGD
    [done] integrate latest DGD
    [done] add bayesian search
    [done] turn caching on for 'get_all_runs()" from hparam_search
[done] logging:
    [done] write "~/.xt/xt_logging.log" file to job AFTER (and delete)
    [done] write "~/.xt/cwd/controller_inner.log" file to job AFTER (and delete)
    [done] log XT version in each run
    [done] turn off "report-rollup" for now (confusing results for epoch/metrics in 'list runs')
[done] misc:
    [done] fixed --target=vm10 bug
    [done] in controller exception, always raise it so the machine is given back to service
    [done] quick-test: refactor into all python code
    [done] quick-test: add xt_demo --auto-mode=1
    [done] fixed bug when "xt remove data xxx" for nested folders
    [done] fixed bug with "xt view mongo runxxx" cmd
    [done] add "values" argument to "option" decorator (can match cmd line option value to list of predefined values)
    [done] add "repeat" and "search-type" to log and as columns in 'list runs' cmd
    [done] fix bug where philly AFTER files were copied to RUN store without the "runs" parent folder being specified
[done] fix bug: metrics roll-ups need to all be from same record, based on primary metric:
    [done] remove [hyperparameter-explorer] metric property  (use primary-metric)
    [done] move [hyperparameter-search] "primary-metric" and "maximize-metric" properties to [general]
    [done] remove [metrics] section of config file
    [done] add [report] "rollup-metric" property (boolean)
    [done] apply record-level roll-up of metrics by "primary-metric", "maximize-metric", "report-rollup" properties
[done] data and model storage:
    [done] data-action config property: none, download, mount
    [done] model-action config property: none, download, mount
    [done] data-write, model-write flags
    [done] add "actions" property to boxes to opt-in on enabling data/model actions for a box
    [done] implement in backends:
        [done] philly
        [done] batch
        [done] pool boxes (including local)
        [done] aml
    [done] add tests for all of these to quickTest.py

### Dec 04 2019 (build v.150)
[done] TOML file changes:
    [done] the MASTER TOML file is now read-only and hidden from editing (xtlib/helpers/default_config.toml)
    [done] "xt config" now always edits the local "xt_config.toml" file
[done] help command:
    [done] renamed "@config" to "@hidden"
    [done] added 5 options to help command: --about, --version, --flags, --docs, --topics, 
    [done] removed standalone cmd "version"
    [done] added first text-based help topic "how"
[done] tensorboard support:
    [done] --mirror-dest=storage  (to mirror TB log files to run's storage area)
    [done] view tensorboard <run name>  
        [done] --job option
        [done] --exper option
        [done] --interval option
        [done] --open flag
    [done] add to xt_demo
[done] quick-test changes:
    [done] localCancelTest
    [done] phillyCancelTest
    [done] batchCancelTest

### Nov 26 2019 (build v.147)
[done] quick-test changes:
    [done] added philly, aml runs
    [done] fixed some missing error checks
[done] config file adjustments
    [done] changed format of roll-up metrics in xt config 
    [done] replace "--pool" option with "--target"  
    [done] replace "[pools]" section with "[compute-targets]"
    [done] reorganized the XT config file around compute target and external services 
    [done] remove list of std columns from report section of config file
    [done] list runs: --available option (shows avail cols)
    [done] recognize and expand "$username" when found in config file entries 
[done] run command adjustments:
    [done] --commands=commands.txt (user-specified multiple run commands)
    [done] change "--controller" flag to "--direct-run" (to flip default value)
    [done] logging/reporting: new std columns: "compute" and "service-type"
[done] philly jobs: basic operations
    [done] direct run of script
    [done] controller-based run of script, children, etc.
    [done] add --queue option (in addition to: --cluster, --vc, and --sku)
    [done] xt view console job343 (for philly jobs))
    [done] xt view status job343 (for philly jobs))
    [done] kill philly run
[done] easier upload/download/viewing of data/models in store
        [done] --data-store=name option for runs
        [done] xt upload/download/view data   (store container: xt-data-xt)
        [done] xt upload/download/view models (store container: xt-models-xt)
[done] refactor code for backends
    [done] new backend_base.py (defines API and common code)
    [done] use backend API: xt run command
    [done] use backend API: xt status
    [done] use backend API's: xt cancel_xxx
[done] quick-start feature (config file param)
    [done] reduces start-up time of xt
[done] cmd cleanup/reorg:
    [done] @keyword_arg (specifies that an argument's vaule will be chosen from a list of keywords)
    [done] xt upload cmd: 
        [done] absorb "upload files" and "upload blobs" cmds
        [done] full argument values: files, blobs, data, models
    [done] xt download cmd: 
        [done] absorb "upload files" and "upload blobs" cmds
        [done] full argument values: files, blobs, data, models
    [done] xt remove cmd:
        [done] absorb "delete files" cmd
        [done] full argument values: files, data, models
    [done] xt dir cmd:
        [done] absorb "list blobs", "list files" cmds
        [done] full argument values: files, blobs, data, models
    [done] remove duplicated cmds:
        [done] remove "status" (use "view status")
        [done] remove "python" (use "run")
        [done] remove "docker run" (use "run")
        [] remove "config local" (use "config --local")
    [done] ensure cmds start with a verb:    
        [done] rename "workspace" to "view workspace"
        [done] rename "experiment" to "view experiment"
    [done] rename root flag "raise" to "stack-trace"
[done] Help adjustments
    [done] add @faq decorator for commands
    [done] for help, compress common list/view commands into 1 command each
        [done] QFE: kw-group property for commands
        [done] help: show all kw-group commands by their unique value
        [done] @kwgroup_help function decorator (specify function to handle help on kwgroups like 'list' or 'view')
        [done] xt help list/view --> call kwgroup func (to show all list/view commands)
[demo] xt_demo.bat
    [done] demo of key commands on multiple platforms (ENTER key for next command)
    [done] xt_demo.py - helper program for user navigation among commands (skip/back/quit)
    [done] ensure all cmds in demo run without error
[done] use logging library to log all exceptions to ~/.xt/xt_logging.log file


### Nov 12 2019 (build v.145)
[] bug fixes/adjustments:
    [done] list runs --filter="username=myname"  (tripping over string as value of prop/op/value triple)
    [done] not parsing cmd line hyperparameters correctly ("not enough values to unpack" error)
    [done] also store xt-run-name in run tags (currently stored in run properties)
    [done] xt hyperdrive runs - no mongo/xt run logging being done

### Nov 09 2019 (build v.143)
[] bug fixes/adjustments/clean up:
    [done] exception when username not defined in env
    [done] show msg about notebook being created for 'xt monitor run'
    [done] refactor mongodb code into mongo_db.py
[] AML backend: add XT controller (TOML, option, implementation)
    [done] basic functionality
    [done] HX functionality
[] cmd_line.py refactoring (big):
    [done] qfe.py: quick-front-end generator (modeled after Click library)
        [done] multi word commands
        [done] 4 char abbreviations
        [done] cmd flags
        [done] cmd options
        [done] cmd arguments
        [done] general help
        [done] command-specific help
        [done] config file integration
        [done] example support
        [done] cloning and overwriting of arguments, options, flags
        [done] config decorator (for parameters coming soley from config file)
        [done] merge options/flags internally 
        [done] in help, merge options and flags, showing the option type (str, flag, etc.)
        [done] customization: remove specified commands 
        [done] pass_by_arg commands, keyword_optional command, @config decorator
        [done] command help: in-line argument names with <> and [] as appropriate
        [done] change options_before_args to options_before_cmd
    [] help/docs:
        [done] generate RST-compatible help pages
        [done] use function doc string for command help and help generation
        [done] add at least 1 example per command
        [done] write-up about QFE
        [done] tiny write-up about XT help build/generation procedure
    [] impl-xxx modules: decorated entrypoints for all commands, by group
        [done] impl_help
        [done] impl-utilities
        [done] impl-storage
        [done] impl-compute


### Oct 31 2019 (build v.142)
[done] create new "xt and azure ml" doc page
[done] new cmd: xt create demo pathname (creates 3 xt demo files in specified directory)
[done] "--monitor" option to generate jupyter notebook to monitor azure ML runs
[done] "xt list files --run=xxx" for azure ML run files
[done] "xt download files * c:/temp --run=xxx" for azure ML run files
[done] new cmd: xt monitor aml-run-name
[done] xt attach aml-run-name
[done] azure ML hyperdrive support 
    [done] search-type: 
        [done] random
        [done] grid
        [done] bayesian
    [done] params dist types:
        [done] choice
        [done] randint
        [done] uniform
        [done] normal
        [done] loguniform
        [done] lognormal
        [done] qchoice
        [done] quniform
        [done] qnormal
        [done] qloguniform
        [done] qlognormal
    [done] termination policies: 
        [done] bandit
        [done] median
        [done] truncation
        [done] none
    [done] source: 
        [done] cmd-line
        [done] --hp-config=file.txt
    [done] new [aml-options] properties / options:
        [done] max-seconds
    [done] new [hp-search] properties / options:
        [done] primary-metric
        [done] maximize-metric
        [done] max-minutes
        [done] max-concurrent-runs
    [done] new [early-stopping] properties / options:
        [done] policy
        [done] evaluation-interval
        [done] delay-evaluation
        [done] slack-factor
        [done] slack-amount
        [done] truncation-percentage
    [done] route child-runs metrics to mongo-db
        [done] add the missing "create" log for child runs

### Oct 18 2019 (build v.136)
[done] use "exper.runNN" as official aml run_name in xt
[done] support "xtlib-capture" (awesome option!) for aml runs
[done] fix bug where aml stats not being recorded to mongo-db

### Oct 17 2019 (build v.133)
[done] improve aml cmd feedback 
[done] add AML support to xt cmds: list work, list exper, list runs, python, kill runxx
[done] distributed training for AML runs

### Oct 16 2019 (build v.132)
[done] RESIZE POOL as each task exits (using autoscale formula)
[done] add "sandbox" service credentials to default_config.toml
[done] renamed "exper-name" TOML option to "experiment" (was previously inconsistent)
[done] AML proof-of-concept:
    [done] using TOML [aml-workspaces] section
    [done] create aml-sandbox-ws service and add to default_config.toml
    [done] create sandbox-compute service and add to default_config.toml
    [done] new cmd: xt aml <target> <args>

### Oct 10 2019 (build v.129)
[done] --parent and --child filters for list runs cmd
[done] new cmd: xt status mirror (report of mirror workers from controller)
[done] fix bug where restarting a preempted job doesn't process hparams
[done] --mirror <path> (during run, controller will mirror all changes in path to the user's xt-grok server)
[done] new cmd: xt collect logs (copy specified log files from run store to grok server, post run completion)

### Oct 4 2019 (build v.127)
[done] status for azure-batch: was busted, now fixed (we new correctly find ip_addr and controller/tb ports)
[done] attach for azure-batch: was busted, now fixed
[done] new cmd: xt scp <from fn> <to fn>  (expands boxname correctly, works without passwords)
[done] catch all mongodb exceptions
[done] cmd-line hyperparameter searching: add support for wildcard paths and BFD codes (e.g., module=[foo/*;bd])
[done] new utility cmd: xt show mongo-db run23.2
[done] bug fix: correctly MERGE metrics/hparams dict into mongo db 
[done] bug: we need to specify --repeat=1 on single cmd per node (Azure Batch)
[done] bug: azure batch "box" name in log always uses "node0"
[done] bug: xt attach run34 (broken for azure batch runs)

### sept 21 2019 (build v.126)
[done] controller: when updating run script, change "python" to "python -u", if needed

### sept 20 2019 (build v.125)
[done] verify 25x box run of miniMnist, hp search, repeat=10 (xt explore job, xt list runs --job=)
[done] --sort=test-acc: not working
[done] run script: args from cmdline not being applied on box (vm10)
[done] --hp-config: enable user to override hp generated values with options at end of cmd
[done] new cmd: xt hex <file> - console.print contents of file in hex
[done] xt test.sh: script file not being rewritten (and won't run with CR chars in it)

### sept 18 2019 (build v.120)
[done] simplify XT:
    [done] remove all applications and prep script from the TOML
    [done] remove use of TOML prep scripts; allow user to run XT against .bat/.sh files
    [done] support for expanded CMD LINE arguments when using RUN scripts
    [done] --parent-script option (to specify a parent script)
    [done] run script (target): issue warning if .sh/.bat doesn't match box os
    [done] --parent-script: issue warning if .sh/.bat doesn't match box os
[done] TOML cleanup:
    [done] remove special "azure-batch" handling; now its just an entry in TOML [pools] section
    [done] remove special "dsvm" box-class; now its specified in the Azure Batch pool entry
    [done] fix bug where missing global TOML gets created with LOCAL content
    [done] "restart controller": add "status" display at end of cmd
    [done] when new TOML created, set "username" from env variable username/user

### sept 17 2019 (build v.110)
[done] TOML cleanup:
    [done] move some options from [general] to new section: [internal]
    [done] move some options from [general] to new section: [capture]
    [done] move some options from [general] to new section: [logging]
    [done] move "username" back into [general] section
    [done] moved [general] section to top of TOML 
    [done] move all azure credentials into dictionary properties under [azure] section
[done] faster BEFORE capture/BEFORE download:
    [done] --zip-before-files (config, option) to zip up before files before sending to store
    [done] upzip before files when downloading to rundir
[done] misc:
    [done] "xt extract": update cmd to work with job-level before files
    [done] rework "rerun" cmd to make it leverage normal parse_python_or_run_cmd()
    [done] --snapshot option for "download blobs" - for changing blobs
    [done] --response to automate cmds that ask for user input (rerun, workspace creation, config creation, delete workspace)

### sept 14 2019 (build v.103)
[done] correctly import pymongo.errors (import pymongo.errors)
[done] when controller faults in queue_check, we stop queuing jobs
[done] when many runs listed, show HDRS and COUNT at bottom of report
[done] improve feedback for azure-batch (1000 boxes scenario)
[done] list runs: include specified run names in mongo-db query
[done] list runs: include --first and --last specs in mongo-db query
[done] xt view log jobxxx
[done] remove pytorch dependency in store (read/write cache file)


### sept 11 2019 (build v.102)
[done] XT "50K runs" changes (end_id, mongo-db + caching)
[done] for azure-batch: when process dies of its own accord, ensure we schedule a shut down correctly
[done] renamed Azure Batches boxes from job-boxN to job-nodeN

### sept 09 2019 (build v.101)
[done] misc:
    [done] remove --tqdm-enabled option
    [done] --local option to specify overrides TOML file
    [done] retry all mongo db calls on OperationFailure error:
    [done] only initialize mongo-db on-demand (high startup costs)
[done] FILE and BLOB store commands:
    [done] progress feedback for download/upload of FILES/BLOBS
    [done] --feedback=false to disable progress feedback for file upload/download
    [done] support for MULTIPLE download/upload of FILES
    [done] support for MULTIPLE download/upload of BLOBS
    [done] new quick-tests for BLOB and FILE: list, download, upload, delete
    [done] support for delete MULTIPLE (with WILDCARDS) from FILE store

### sep 01 2019 (build v.100)
[] download files:
    [done] use Azure delimiter-trick for getting blob listings
    [done] better bug fix for downloading files from subfolders
    [done] fix miniMnist.py bug where it gets reloaded multiple times
        --> was not a bug; just artifact of Pytorch DataLoader w/multiple workers

### aug 31 2019 (build v.99)
[done] fix bug where subfolder files are not downloaded

### aug 30 2019 (build v.98)
[] "list runs" command:
    [done] --columns option for "list runs" cmd to show available column names
    [done] --filter option: translate from report col names to filter names
    [done] --filter option: make the "hparams." and "metrics." col name prefixes optional 
    [done] expose missing run fields to reports: "guid", "node", "from_ip"  
    [done] fix bug where sort on a key not present in all included runs kills report 
[] misc:
    [done] help: various updates
    [done] support for running single command in a .bat or .sh file
    [done] support for multi instances of --before-files, --after-files, and omit-files
    [done] all XT options must now start with "--"
[] FILE and BLOB store commands:
    [done] all FILE/BLOB cmd: set relative PATH using options: --workspace, --exper, --run, --job
    [done] disallow delete from BLOB store
    [done] organize FILE store to more closes match BLOB store
    [done] remove "dir cmd" (replaced by list blobs/files)
    [done] "list blobs": use directory style listing
    [done] "list files": use directory style listing


### aug 27 2019 (build v.97)
[done] docker runs on linux: run "nvidia-docker"
[done] app argument symbol: $MR-INDEX; caculate as: (child index-1) % max-runs
[done] for docker runs on windows: replace "$(pwd)" with "%cd%"
[done] for docker runs on linux: replace "%cd%" with "$(pwd)"
[done] miniMnist: log/display train-acc
[done] fix issue with RESTART CONTROLLER vs. ATTACH to run
[done] redirect RETRY errors and stack traces to an azure_errors.txt file
[done] write initial run info to mongo db
[done] update run info to mongo db on RUN EVENTS
[done] update run info to mongo db at end of run
[done] list runs - SPEED UP by using only use mongo db info
[done] --filter option to by specified: name operator value 
[done] support "median", "mode" roll-ups
[done] replace "$registry" with user's ARL entry: xtcontainerregistry.azurecr.io
[done] explore job/experiment - only use mongo db info
[done] upload once to JOB (not to each RUN) - save time and 25x upload msgs

### aug 20 2019 (build v.96)
[done] TOML: add "omit-files" property under [general]
[done] option: "--experiment" (override app's experiment property)
[done] TOML property rename: rename "before-files" to "before-files" in [general] section
[done] TOML property rename: rename "after-files" to "after-files" in [general] section
[done] new option: --before-files (specify wildcard filenames for BEFORE files to capture)
[done] new option: --after-files (specify wildcard filenames for AFTER files to capture)
[done] API CHANGE: rename logger.py to run.py
[done] API CHANGE: rename Logger() class to Run() class

### aug 16 2019 (build v.95)
[done] TOML: add "tqdm-enabled" option under [general]
[done] allow "python" keyword to be optional (so this works: xt miniMnist.py)
[done] suport for running in docker containers:
    [done] new cmd: docker run <args>
    [done] new cmd: docker login 
    [done] new cmd: docker logout 
    [done] TOML: new [azure.container.registry] section (with 4 properties)
    [done] new "--login" option to control if docker should be logged into user's azure container registry

### aug 14 2019 (build v.93)
[done] default --search-type to "random"
[done] enable "xt config" to run BEFORE we open the config file

### aug 14 2019 (build v.92)
[done] log "path" of ML app for runs; include PATH and TARGET in 'list runs' report columns
[done] add "--local" options for 'xt config' cmd
[done] removed user_settings file usage
[done] changed cmds to only show current settings: "xt workspace", "xt max-runs"
[done] add "description" to 'list runs' report columns in default TOML
[done] changed aggregated run names file (for experiment/job) to only contain names of ENDED runs
[done] add stack trace output to Azure RETRY code

### aug 12 2019 (build v.91)
[done] TOML file option (--xtlib-capture) to capture and use latest XTLIB source code from local machine for Azure Batch
[done] TOML defaults: attach=False
[done] change Logger() CTR to accept optional XTConfig and Store objects (so that run_cache_dir can be set)
[done] safegard cache file read/write with try/except/logging
[done] ensure "xt explore job/exper" can reliably find the user-named hp-config file
[done] LOCAL TOML files for apps (they overwrite base TOML file)


### aug 9 2019 (build v.90)
[done] explicit check at start of store initialization:
    [done] 5 config items: core.username, azure.storage-name, azure.storage-key, azure.batch*
[done] TOML CHANGE: switch over to new design of app information and prep scripts in TOML file 
[done] TOML CHANGE: [box-class.xxx] sections that specify "shell-launch-prefix" for linux box classes
[done] consolidate all app-info related functions into app_information.py
[done] consolidate all box-info related functions into box_information.py
[done] fix monitor-bug introduced by importing tqdm into store.py

### aug 8 2019 (build v.88)
[done] add --xt-config option
[done] rework default "xt" response to be a shorter help screen
[done] renamed "config.py" to "xt_config.py"
[done] renamed "Config" class to "XTConfig" class
[done] add --search-type TOML and option
[done] support for random sampling of discrete values (search-type=random)
[done] show "dry run" info even if --dry-run not specified
[done] renamed TOML section [sweep] to [hp-search]
[done] renamed --sweeps option to --hp-config
[done] support for xt-controller and simpel apps to run local and on Azure Batch without explicit prep script entries
[done] add progress bar while reading direct runs (summary and allruns)
[done] TOML file: moved "username" from [general] to [core]
[done] add progress-bar for download files from non-cache
[done] get CONDA current environment (for use with XT and APP, if not specified)

### aug 6 2019 (build v.87)
[done] fix bug in controller: new code that calculates # of truely active runs
[done] fix bug where get_experiment_run_names() was using exper_name vs. ws_name for bs.exists() call
[done] fix (long-standing) bug where after run completes, it would get error with random cmd line being run
[done] fix bug where "xt view console" was ignoring --workspace option (also fixed related cmds with same pattern)

### aug 5 2019 (build v.86)
[done] allruns: only use and cache results for COMPLETED runs
[done] add "run-cache-dir" to TOML config file
[done] ensure azure-batch doesn't exit until all of runs have completed their wrapup 
[done] fix "access denied" error for c:\users\username\.xt\.tmp directory

### aug 3 2019 (build v.84)
[done] fix issues with "get_experiment_runs" API

### aug 3 2019 (build v.83)
[done] expose "exper_name" on logger instance

### aug 2 2019 (build v.82)
[done] fix problems with EXPERIMENT file API
[done] when deleting a workspace, zap its associated SUMMARY RUN cache file

### aug 1 2019 (build v.81)
[done] update legacy runs for "list runs" type cmds (one-time upgrade)

### aug 1 2019 (build v.80)
[done] create SWEEPS file for cmdline hparam searches (to work with HP explorer)
[done] fix problem with azure-batch and cmdline hparam searching
[done] INCREMENTAL accumulation of summary files (client-based caching):
    [done] xt list 
    [done] xt explore

### Jul 31 2019 (build v.76)
[done] fix azure batch problem with cmd line hparm searching
[done] specify version numbers on azure to get compatible components

### Jul 30 2019 (build v.73)
[done] rework cmds for multi-run changes:
    [done] rework cmd-line hparam searching with sweeps file (local, remote, pool, azure-batch)
[done] implement: parent/child prep scripts
    [done] run of parent script before putting parent run into queue
        [done] start run of parent with parent_prep_script
        [done] when run completes and is succeesful, requeue the parent run with flag=False
        [done] ensure child is run using child_prep_script
[done] new azure file system support (file API)
[done] file share cmds:
    [done] share at multiple levels: job, workspace, experiment
    [done] upload file
    [done] download file
    [done] delete files
    [done] list files
[done]low-pri run resumption (parent run: update existing runs/adjust repeat):
    [done] create a run option (--demand) that forces xt controller to run in azure-batch mode
    [done] support for restarting runs with '--demand' and 'restart controller'
    [done] log restarted job as "resumed"
[done] TOML file: option for aggregating runs (job, experiment, none)
[done] adjust: don't upload ".git" directories to BEFORE dir in store
[done] fix bug in captured console output for progress-style msgs (CR vs. LF chars)
[done] rework all 4 x 10 file API's in Store library to be based on a common implementation.  External API not changed.

### Jun 24, 2019 (build v.71)
* removed bold/dim text on help; removed future commands from help
* support for restarting flat, parent, and child runs in controller 
* new "restarts" standard reporting column

### Jun 22, 2019 (build v.70)
* TOML file: in [sweeps], renamed "hx-score-name" to "hx-metric"
* TOML file: in [sweeps], new property "aggregate-dest = "job" (to control where to aggregate jobs & write hx_config.txt)
* new option: --hx-metric (sets score name used by 'explore' cmd)
* new option: --auto-start (when true, 'status' cmd will start controller, if needed)
* renamed all xtlib files that started with "xt_" to the names without the prefix (and associated classes)

### Jun 21, 2019 (build v.69)
* new cmd: list boxes
* new cmd: list pools
* TOML file: default "attach" to "true"
* new options for list cmd: --first=num, --last=num
* list runs cmd: add support for wildcards in run names

### Jun 20, 2019 (build v.68)
* TOML file: rename "image-class" to "box-class"
* TOML file: rename "prep-script" to "app-class"
* TOML file: remove "-scripts" part of prep-script section names
* TOML file: new "[metrics]" section replaces old "[metric-rollups]"
* TOML: added optional "bounds" property for each metric (defaults for HX score range)
* new logging API: set_checkpoint()
* new logging API: get_checkpoint()
* changes "hx" cmd to: xt explore experiment

### Jun 18, 2019 (build v.66)
* fix "cancel all job=xx"
* correct prep_scrips for dsvm/azure-batch in default_config.toml
* TOML file: change all "shell_launch_prefix" to "shell-launch-prefix"
* TOML file: change all "node_agent_sku_id" to "node-agent-sku-id"
* TOML file change: add "low-pri: 0" to all azure pool definitions (and “low-pri = 0” in [azure] section (under nodes = 1)
* support for %XT_TAGET_FILE% env variable in to help generalize data loading 
* --low-pri count (specify # of low priority nodes for azure batch)
* --resume name (resume an interupted run)

### Jun 17, 2019 (build v.65)
* "xt dir" command (show Storage containers/blobs by path)
* --sweep option: copy specified file to associated experiment folder ("hp_sweeps.txt")
* --sweep and --repeat: specify cmd line args from sweep file 
* --sweep and --repeat: put HP's in BEFORE folder config file ("hp_config.txt")
* enable option override of custom azure pool properties: nodes, vm-size, vm-image
* new "hx" cmd to launch the Hyperparameter Explorer from xt 

### Jun 9, 2019 (build v.60)
* "cancel all" --> loop killing until idle (before, some child runs still survived)
* fix bug logging string metrics (now supported)
* fix bug in 'list runs' when custom azure-batch pool used
* --max-runs option now sets max-runs on the destination box when run is queued
* "cancel all job=xxx" now kills azure-batch job (some more needed wrapping up run logs)
* "--user" option for pip install no longer needed (default script prefix now contains 'sudo -A')

### Jun 6, 2019 (build v.59)
* fix issues in linux "restart controller" cmd

### Jun 6, 2019 (build v.58)
* in-progress: support for "cancel" cmd for normal and azure-batch runs

### Jun 4, 2019 (build v.57)
* first cut of azure-batch support (python/run, attach)
* "view log controller" cmd (see output of xt controller log)

### Jun 4, 2019 (build v.56)
* add "run_xt.py" to setup.py

### Jun 4, 2019 (build v.55)
* refactor multiple runs (pool-based) for azure batch

### May 29, 2019 (build v.54)
* misc changes for azure batch support

### May 29, 2019 (build v.53)
* misc changes for azure batch support

### May 29, 2019 (build v.52)
* use specified port to run xt controller (for azure batch)

### May 29, 2019 (build v.51)
* use "--hold" option to keep xt controller running indefinetly on Azure Batch
* use "/bin/sh --login <script>" to run user app (for Azure Batch)

### May 28, 2019 (build v.49)
* added "image_class" to boxes to match updated [scripts] section of config file
* correctly exit controller when "single_run" completed (azure batch mode)

### May 28, 2019 (build v.48)
* correctly upload specified "output" directory to AFTER folder in store
* new "pool" and "job" API's in xt_store (for use with Azure Batch)
* default app in xt_config.toml renamed back to original "__default__"
* azure-batch support (in-progress)

### May 26, 2019 (build v.47)
* xt_config.toml cleanup:
    - added new [windows-scripts] and [linux-scripts] sections
    - replaced "conda" property with more general "prep-script" property in app entries 
    - removed "requirements" property for app config entries
    - removed column formatting section
    - added new general formatting properties in new [reports] section
    - renamed "exper" to "experiment" property for app config entries
    - move some properties from "core" to "general"
    - move some properties from "general" to "reports"
    - replaced "_" with "-" in all keywords, value, and sample names 
    --> USERS NEED TO delete their user_settings.json file
    --> USERS NEED TO rename their xt_config.toml and move custom values into newly created file

* list runs cmd: 
    - only use explicit box/compute for box filtering
    - add --repair=True option to skip repairing phantom runs
    - skip over unknown and unreachable hosts during phantom run repair
    - add new filter: --app=
    
* deleted "test port 22" cmd (obsoleted by "xt ssh" cmd)

* exception handling:
    - catch all exceptions in central place (outer part of cmdline)
    - --raise option (re-raise exception after catching and reporting it)

### May 24, 2019 (build v.46)
* status cmd: don't set the "workspace required" flag for this cmd
* kill cmd: don't set the "workspace required" flag for this cmd
* list runs cmd: validate unfinished jobs and repair phantom runs
* rerun cmd: implemented basic support (TODO: support POOL, support --repeat, support HPARAM searches)

### May 23, 2019 (build v.45)
* for jobs killed while in run queue (like repeat=N parent jobs), correctly call run.wrapup() to log summary record, etc.

### May 23, 2019 (build v.44)
* list runs cmd: collect & rollup metrics and hyperparams for runs without an ending summary record
* keysend cmd: don't overwrite existing key unless the "--overwrite" option is specified

### May 23, 2019 (build v.43)
* validate run_names on cmds: view log, view console, view metrics, plot, list runs
* xt status: include workspace for each run
* xt_controller: key for runs (running and queued dictionaries) now includes workspace name
* child runs on remote boxes: correct logged box name
* list runs: add support for box/pool filtering
* max-runs: correctly set on remote boxes
* config file, boxes section: make "max-runs" optional for box definitions
* allow 'list runs running' (use full run name validation)
* use workspace-level summary file to speed up "list runs" cmd
* new xt_run_log module (and associated class XTRunLog) for simplified logging/store access

