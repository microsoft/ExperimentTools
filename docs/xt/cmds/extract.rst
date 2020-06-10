.. _extract:  

========================================
extract command
========================================

Usage::

    xt extract <runs> <dest-dir> [OPTIONS]

Description::

        download all files associated with the run to the specified directory

Arguments::

  runs        a comma separated list of runs, jobs, or experiments
  dest-dir    the path of the directory

Options::

  --browse       flag    specifies that an folder window should be opened for the dest_dir after the extraction has completed
  --response     str     the response to be used to confirm the directory deletion
  --workspace    str     the workspace that the runs resides in

Examples:

  extract files from curious/run26 to ./run26_files::

  > xt extract curious/run26 ./run26_files

