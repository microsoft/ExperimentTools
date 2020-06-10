.. _upload:  

========================================
upload command
========================================

Usage::

    xt upload <local-path> [store-path] [OPTIONS]

Description::

        copy local files to an Azure storage location

Arguments::

  local-path    the path for the local source file, directory, or wildcard
  store-path    the path for the destination store blob or folder

Options::

  --experiment    str     the experiment that the path is relative to
  --feedback      flag    when True, incremental feedback will be displayed
  --job           str     the job id that the path is relative to
  --run           str     the run name that the path is relative to
  --share         str     the name of the share that the path is relative to
  --workspace     str     the workspace name that the path is relative to

Examples:

  copy python files from local directory to the BLOB store area associated with workspace 'curious'::

  > xt upload *.py . --share=data --work=curious

  copy the local file 'single_sweeps.txt' as 'sweeps.txt' in the BLOB store area for job2998::

  > xt upload single_sweeps.txt sweeps.txt --share=data --job=job2998

  copy MNIST data from local dir to data upload folder name 'my-mnist'::

  > xt upload ./mnist/** my-mnist --share=data

