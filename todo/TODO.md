# XTLib To-do Items (Mar 15, 2020)

## XT to-do items (short term)

[] support latest pytorch and python 3.8
    [] exper38 is set up, but "xt rerun" command fails in xt_demo due to problem with pywin32/pypiwin32 (needs investigation)
[] misc:
    [] implementation of 'view run' command
    [] run quicktest under linux
[] update docs
    [] update "xt_and_docker" help topic 
    [] view run command

[] misc
    [] enhance "portal_url" col for "view status --target=aml" to be run-specific
    [] xt extract: for AML runs, download all AML logs
[] test improvements
    [] run each command's set of EXAMPLES
    [] more assert checking of immediate results (command output, storage changes, file system changes)
    [] strategies for delayed checking/reporting for service run results
[] xt view jupyter
    [] <run name> [ <fn_notebook> ]   (on box for specified run, open a jupyter notebook (empty or as specified))
    [] --jupyter flag or option on run cmd (?)
[] Hyperparameter Explorer 
    [on-hold] remove the old "append runs" in storage (?)

### High
[] Philly jobs: 
    [] --max-retries=N (since philly GPU's are less reliable, we need to be able to specify a retry count for each run)
[] AML backend: add missing support for:
    [] XT/controller PORT-based communication
    [] proper AML logging of child runs (under child, not parent) 
[] help topics to be written:
    [] philly work-thru doc page
    [] how to use early-termination policies (azure concepts, examples)
    [] how to use parameter distributions (azure concepts, examples)
    [] how to use DGD
    [] how to use HX
    [] for all help topics, design approach to write once all render in text (for console) and rich text (for HTML)

[20 hrs] Web site updates:
    [] xt videos
    [] XT CHEAT SHEET
    [] add HELP COMMANDS output
    [] write PER-COMMAND HELP (syntax, options, semantics, examples)
    [] finish DOCS (XT, Logging/Store APIs)
    [] get XT notebook tutorials working (hosted on biased VM)

[16 hrs] Distributed training support:
    [] --gpus=1,2,3,4  ?
    [] --horovod       (used to initiate a horovod job across using the specified pool of machines)

### Medium

[] --retries: error retry of runs
[] --update=True ==> only upload/download missing (or out of date?) files

[] misc:
    [] list runs: filtering: errors=False (hide runs with errors)    (None=default, False=hide, True=Show)

[] phone app or compatible web-site to check run status:
    [] kill unpromosing runs
    [] rerun with changed parameters
    [] email a view to others
[] "show detail" commands:
    [] run
    [] experiment
    [] job
    [] workspace
    [] azure-batch pool (?)

[] unified commands that can work on mixture of these:
        [] local file system   (c:/foo, local:)
        [] remote box          (box://vm15/~/.xt..)
        [] Azure file storage  (afs://ws15/...)
        [] Azure blob storage  (abs://workspaces/ws15...)
        [] HTTP/web            (https://foo.com/)
        [] zip file            (using one of the above references)
    [] dir <source>
    [] copy <source> <destination> ; each can be one of:
    [] cat <source>
    [] edit <source>
[] command to download all job files (for debugging)
[] more zip/unzip:
    [] upload blobs/files: --zip option, --unzip option
    [] download blobs/files: --zip option, --unzip option
[] misc:
    [] "list blobs --run=xxx": fix bug - child runs look like ".1", "2", etc. subdirs
    [] at end of run, log "azure-retries" and "mongo-retries" retried error counts (and retry time waiting...)
[] fix docker vs. c:\users issue (docker cannot map c:\user\username\.xt path):
    [] new YAML property: windows-rundirs path
    [] use windows-rundirs path for allocating rundirs (controller)
    [] ensure we bind to RUNDIR (not capture dir) with %cd%/$(pwd)

[] find a way to still exclude ".git" files when user specifies other --omit-files=xxx files
[] --update option: upload/download of FILES (not blobs) - only update if different size or MD5 HASH values don't agree
[] speed up 1000x box azure batch job creation?
[] tensorwatch support (TBD what this entails)
[] team portal for experiments
[] azure batch RESIZE:
    [6 hrs] new cmd: resize job xxx --nodes=3 --low-pri=4 (azure-batch pool resizing)
    [] auto delete/resize as needed when we get an "error box" in new pool
    [] auto-size the pool: as EACH TASK completes, we release the assoc. node; big savings when elapsed on nodes varies by hours)
[] azure batch:
    [] add box-class to azure pools 
    [] new cmd: report on COMPUTING costs by run/job/exper/workspace
    [] new cmd: report on STORAGE costs by run/job/exper/workspace

[] when running docker, we need a way to avoid uploading the current directory files needlessly
   (harder to detect "wrong dir" since we don't have a target file)
[] fix bug when using "=" in quoted --description option value
[] --zip and --unzip options for upload/download cmds (zip and unzip files on the fly)
[6 hrs] kill command for multi-run:
    [] kill job (wrapup child runs)
    [] runXXX (for azure-batch run)

[2 hrs] change "is_controller_running()" to use process info (more reliable than communication)
[] cmd to free up STORE space (old models, error-stopped runs, killed runs) based on user-specified POLICES
[] --export= (csv, txt, excel)
[8 hrs] expand scope of RERUN cmd:
    [] remote box
    [] pool
    [] azure batch
    [] --repeat
    [] --hp-config
    [] command line hp search
[] language design
    [] new cmd: "cat" or "view file" (to view text files in store)
    [] revisit cmd: "list files" for "dir"?
    [3 hrs] rework cmd parsing so that "xt config" and "xt --xt-config=xx  config" are executed BEFORE initializing config object
[] azure-batch enhancements
    [] ssh to azure-batch box (need ab keypair set-up)
    [] STATUS command for azure-batch boxes (show status of runs for that ab box)
    [] authenticate connection to xt_controller (keypair)
    [] support for opening incoming port on ML app (and API for getting port MAPPING)
[] user collaboration:
    [] new cmd: share <ws name> with <username>   # share the specified workspace with another user

### Low
[] --mount option: --mount="data=>data"
[] list run:
    [] --repair: something is not working here - many azure jobs not being cached after multi "list runs"
[] better cmdline error checking
    [] validate "workspace" and "experiment" values (for cmds not creating them)
[]  misc low priority cmds
    [] new cmd: delete run <name>                     # delete the specified run 
    [] new cmd: delete experiment <name>              # delete the specified experiment and all of its associated runs
    [] new cmd: copy run <name> to <ws name>          # copy run to another workspace
    [] new cmd: view hparms <name>                    # view hparam settings for run
    [] new cmd: xt view args <name>                      # view command line args for run
    [] list work  -> "counts" option to show experiment/run counts
    [] list exper  -> "counts" option to show run counts

### On-Hold
[on-hold] cache jobs (with experiment,workspace) in mongo-db for filtered job queries

[deferred] fix problem where console output is slow to console.print on attach listeners
    --> seems to be the overhead of RPC in sending each line to the client; could try buffering multiple
        lines, but that introduces its own set of problems.  for now, defer. rfernand2, 09/20/2019.

