.. _view_metrics:  

========================================
view metrics command
========================================

Usage::

    xt view metrics <runs> [metrics] [OPTIONS]

Description::

        view the set of logged metrics for specified run

Arguments::

  runs       a comma separated list of runs, jobs, or experiments
  metrics    optional list of metric names

Options::

  --export       str         will create a tab-separated file for the report contents
  --hparams      str_list    will list the specified hyperparmeter names and values before the metrics
  --merge        flag        will merge all datasets into a single table
  --steps        int_list    show metrics only for the specified steps
  --workspace    str         the workspace that the run resides in

Examples:

  view the logged metrics for run153 in the current workspace::

  > xt view metrics run153

