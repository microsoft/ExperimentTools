.. _view_status:  

========================================
view status command
========================================

Usage::

    xt view status [run-name] [OPTIONS]

Description::

    The view status command is used to display status information about the XT controller process
    running on a box (or pool of boxes).

    The'tensorboard' flag is used to return information about the running tensorboard-related processes.
    The 'mirror' flag is used to return information about Grok server mirroring processes.

Arguments::

  run-name    return status only for the specified run

Options::

  --active          flag    when specified, only active runs are reported
  --auto-start      flag    when specified, the controller on the specified boxes will be started when needed
  --cluster         str     the name of the cluster to be viewed
  --completed       flag    when specified, only completed runs are reported
  --escape-secs     int     how many seconds to wait before terminating the monitor loop
  --job             str     query all boxes defined for the specified job
  --max-finished    int     the maximum number of finished jobs to show
  --mirror          flag    shows the status of mirror processes on the box
  --monitor         flag    continually monitor the status
  --queued          flag    when specified, only queued runs are reported
  --status          str     only show jobs with a matching status
  --target          str     the name of the compute target to query for status
  --tensorboard     flag    shows the status of tensorboard processes on the box
  --username        str     the username used to filter runs
  --vc              str     the name of the virtual cluster
  --workspace       str     the workspace used to filter runs

Examples:

  show the status of runs on the local machine::

  > xt view status

  show the status of run68::

  > xt view status curious/run68

