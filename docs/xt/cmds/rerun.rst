.. _rerun:  

========================================
rerun command
========================================

Usage::

    xt rerun <run-name> [OPTIONS]

Description::

        submits a run to be run again

Arguments::

  run-name    the name of the original run

Options::

  --response     str    the automatic response to be used to supplement the cmd line args for the run
  --workspace    str    the workspace that the runs reside within

Examples:

  rerun run74::

  > xt rerun curious/run74

