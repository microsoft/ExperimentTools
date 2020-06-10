.. _list_experiments:  

========================================
list experiments command
========================================

Usage::

    xt list experiments [wildcard] [OPTIONS]

Description::

        list experiments defined in the current workspace

Arguments::

  wildcard    a wildcard pattern used to select matching experiment names

Options::

  --detail       str    when specified, some details about each workspace will be included
  --workspace    str    the name of the workspace containing the experiments

Examples:

  list the experiments in the current workspace::

  > xt list exper

  list the experiments starting with the name 'george' in the 'curious' workspace::

  > xt list exper george* --work=curious

