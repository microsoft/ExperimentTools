.. _list_blobs:  

========================================
list blobs command
========================================

Usage::

    xt list blobs [path] [OPTIONS]

Description::

        lists the Azure store blobs matching the specified path/wildcard and options

Arguments::

  path    the path for the source store blob or wildcard

Options::

  --experiment    str    the experiment that the path is relative to
  --job           str    the job id that the path is relative to
  --run           str    the run name that the path is relative to
  --share         str    the name of the share that the path is relative to
  --subdirs       int    controls the depth of subdirectories listed (-1 for unlimited)
  --workspace     str    the workspace name that the path is relative to

Examples:

  list blobs from store for job2998::

  > xt list blobs --job=job2998

  list blobs from 'models' share::

  > xt list blobs --share=models

