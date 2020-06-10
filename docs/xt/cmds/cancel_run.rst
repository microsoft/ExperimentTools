.. _cancel_run:  

========================================
cancel run command
========================================

Usage::

    xt cancel run <run-names> [OPTIONS]

Description::

        cancels the specified run(s)

Arguments::

  run-names    the list of run names to cancel

Options::

  --workspace    str    the workspace that contains the runs

Examples:

  cancel run103 in curious workspace::

  > xt cancel runs run103 --work=curious

