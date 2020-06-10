.. _view_console:  

========================================
view console command
========================================

Usage::

    xt view console <name> [OPTIONS]

Description::

        view console output for specified run

Arguments::

  name    the name of the run or job

Options::

  --node-index    str    the node index for the specified job
  --workspace     str    the workspace that the run resides in

Examples:

  view the console output for run26 in the curious workspace::

  > xt view console curions/run26

  view the console output for job201, node3::

  > xt view console job201 --node-index=3

