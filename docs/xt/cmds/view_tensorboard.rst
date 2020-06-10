.. _view_tensorboard:  

========================================
view tensorboard command
========================================

Usage::

    xt view tensorboard [run-list] [OPTIONS]

Description::

        this cmd will run a separate process that runs the XTLIB tensorboard_reader to run TB and sync TB logs to
    local files.

Arguments::

  run-list    a comma separated list of: run names, name ranges, or wildcard patterns

Options::

  --browse        flag    specifies that a browser page should be opened for the link
  --experiment    str     the experiment that the path is relative to
  --interval      int     specifies interval between polling for changes in the run's 'output' storage
  --job           str     the job id that the path is relative to
  --template      str     specifies a template for building the collected log paths
  --workspace     str     the workspace that the runs are defined within

Examples:

  view tensorboard plots for run23 in the curious workspace::

  > xt view tensorboard curious/run23

