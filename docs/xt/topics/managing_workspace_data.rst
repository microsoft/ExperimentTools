.. _xt_workspaces:

========================================
Managing XT workspaces
========================================

XT workspaces contain three vital types of machine learning data:

    - Jobs
    - Job runs
    - Experiments

You can export and import any amount or unit of each of these types of data for use by other XT teams and researchers. All data is exported in a Zip archive file. To maintain control over importing and exporting, the **xt list** commands allow you to keep a grip on what job and experiment data is present in your XT installation and what you can single out for exporting to other researchers. We'll have a look at this tool before showing you how to export and import data.

.. note:: Many capabilities in this feature set are not available in XT Basic mode.

--------------------------------------------------------
Using the List commands to navigate your experiment data
--------------------------------------------------------

The **xt list** commands most relevant to the subject at hand are for workspaces, experiments, jobs and runs. 

.. code-block::

    (xt) C:\ExperimentTools> xt help list

    list commands:
      list blobs          lists the Azure store blobs matching the specified path/wildcard and options
      list boxes          list the boxes (remote computers) defined in your XT config file
      list experiments    list experiments defined in the current workspace
      list jobs           displays a job report for the specified jobs
      list runs           displays a run report for the specified runs
      list shares         list currently defined shares
      list tags           list tags of the specified jobs or runs
      list targets        list the user-defined compute targets
      list workspaces     list currently defined workspaces

You can inspect your current workspace with the **xt list experiments** command. To see just what you have available for export in your current workspace:

.. code-block::

    (xt) C:\ExperimentTools>xt list experiments
        Experiments for workspace: ws1
        exper2
        mini1
        exper19
        exper21
        exper24
        training2
        training3
        miniSearch
        ...

To view the list of workspaces in your XT environment; enter the following:

.. code-block::

    (xt) C:\ExperimentTools>xt list workspaces

        XT workspaces:
          abc
          curious
          peanuts
          ml-maze
          mnist
          qt-jl-remove-c7
          quick-test
        ...

You can check for blobs in experiments, jobs, job runs, shares, subdirectories and workspaces:

.. code-block::

    (xt) C:\ExperimentTools>xt help list blobs

      Usage: xt list blobs [path] [OPTIONS]

      lists the Azure store blobs matching the specified path/wildcard and options

    Arguments:
      path    the path for the source store blob or wildcard

    Options:
      --experiment    str    the experiment that the path is relative to
      --job           str    the job id that the path is relative to
      --run           str    the run name that the path is relative to
      --share         str    the name of the share that the path is relative to
      --subdirs       int    controls the depth of subdirectories listed (-1 for unlimited)
      --workspace     str    the workspace name that the path is relative to

    Examples:
      list blobs from store for job2998:
      > xt list blobs --job=job2998

      list blobs from 'models' share:
      > xt list blobs --share=models

------------------------------------
Exporting Workspace data
------------------------------------

.. note:: You don't have to switch between workspaces to export them, or to export smaller bodies of data from them. To change workspaces, edit the local xt_config file's **workspace** field under the **General** category.

At any time, you can enter the following Help command: 

.. code-block::

    (xt) C:\ExperimentTools>xt help export workspace

    Usage: xt export workspace <output-file> [OPTIONS]

    exports a workspace to a workspace archive file

    Arguments:
      output-file    the name of the output file to export workspace to

    Options:
      --experiment    str_list    matches jobs belonging to the experiment name
      --jobs          str_list    list of jobs to include
      --tags-all      str_list    matches jobs containing all of the specified tags
      --tags-any      str_list    matches jobs containing any of the specified tags
      --workspace     str         the workspace that the run resides in

    Examples:
      export workspace ws5 to ws5_workspace.zip:
    > xt export workspace ws5_workspace.zip --workspace=ws5

***********************************
Exporting jobs
***********************************

Using additional arguments to the **export workspace** command, uou can specify individual jobs or a list of jobs to export:

.. code-block::

    (xt) C:\ExperimentTools>xt export workspace magic-maze.zip --workspace magic-maze --jobs=job2209

    exporting workspace magic-maze (1 jobs) to: magic-maze.zip
      exporting: job2209 (1 runs)
    no matching blobs found in: blob-store://xt-store-info/jobs/job2209
    no matching blobs found in: blob-store://magic-maze/runs/run1
      export completed

Insert a comma between job IDs to export multiple jobs:

.. code-block::

    (xt) C:\ExperimentTools>xt export workspace magic-maze.zip --workspace magic-maze --jobs=job2209,job2210

    exporting workspace magic-maze (1 jobs) to: magic-maze.zip
      exporting: job2209 (1 runs)
    no matching blobs found in: blob-store://xt-store-info/jobs/job2209
    no matching blobs found in: blob-store://magic-maze/runs/run1
      exporting: job2210 (1 runs)
    no matching blobs found in: blob-store://xt-store-info/jobs/job2210
    no matching blobs found in: blob-store://magic-maze/runs/run2
      export completed

********************************
Exporting workspaces
********************************

By default, if you export the entire workspace, you can wind up with a very large Zip file that can take hours to finish exporting. Fortunately, you can specify a single experiment, or even a single job run within any workspace, for export to a file. Be aware that even moderately sized workspaces or experiments can scale to tens or hundreds of megabytes or much more. 

The workspace data typically exists in the cloud; the scale of machine learning data often exceeds the capacity of even the largest local computer hard disks. Bear this in mind when you consider importing and exporting workspace and experiment data.

If you don't specify a workspace for export, the command will use the current workspace specified in the xt_config file.

To select and export an individual workspace in XT, specify it within the command. The arguments are, in this order:

.. code-block::

    (xt) C:\ExperimentTools> xt export workspace <output-file> --workspace <originating workspace name>

An example:

.. code-block::

    (xt) C:\ExperimentTools> xt export workspace ml-maze.zip --workspace ml-maze

    exporting workspace ws1 (1 jobs) to: ws1_workspace.zip
      exporting: job1322 (1 runs)
    no matching blobs found in: blob-store://xt-store-info/jobs/job1322
      exporting: job1323 (1 runs)
      exporting: job1324 (1 runs)
      exporting: job1325 (1 runs)
      ...
      export completed

Each Zip file contains a Contents JSON text file that lists the entire contents of the file. A Workspaces export will contain a complete set of the workspace's jobs and job runs data. 

To export an experiment, use **xt export workspace --experiment**:

.. code-block::

    (xt) C:\ExperimentTools> xt export workspace ml-maze.zip --workspace ml-maze

    exporting workspace ws1 (1 jobs) to: ws1_workspace.zip

------------------------------------------
Importing workspace data
------------------------------------------

Similarly, you can import workspace data from any Zip file exported by another researcher:

.. code-block::

    (xt) C:\ExperimentTools>xt help import workspace

    Usage: xt import workspace <input-file> [new-workspace] [OPTIONS]

        imports a workspace from a workspace archive file

    Arguments:
      input-file       the name of the archive file (.zip) to import the workspace from
      new-workspace    the new name for the imported workspace

    Options:
      --job-prefix    str     the prefix to add to imported job names
      --overwrite     flag    When specified, any existing jobs with the same prefix and name will be overwritten

    Examples:
      import workspace from workspace.zip as new_ws5:
      > xt import workspace workspace.zip new_ws5

Unlike blobs, zip files can come from anywhere including your local hard disk. You can also overwrite an existing workspace with imported information if necessary. Make sure to properly define a name for the new workspace so it is readily recognizable. You can also apply a new job prefix to imported job data. 

.. note:: Avoid overwriting your current workspace unless you absolutely intend to do so. If you omit a workspace name as one the the command arguments, the imported data will be placed directly in the current workspace.

By default, the data will inhabit the blob-store specified in the xt_config file.
