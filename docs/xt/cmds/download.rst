.. _download:  

========================================
download command
========================================

Usage::

    xt download <store-path> [local-path] [OPTIONS]

Description::

        copy Azure store blobs to local files/directory

Arguments::

  store-path    the path for the source store blob or wildcard
  local-path    the path for the destination file (if downloading a single file) or directory (if downloading multiple files)

Options::

  --experiment    str     the experiment that the path is relative to
  --feedback      flag    when True, incremental feedback will be displayed
  --job           str     the job id that the path is relative to
  --run           str     the run name that the path is relative to
  --share         str     the name of the share that the path is relative to
  --snapshot      flag    when True, a temporary snapshot of store files will be used for their download
  --workspace     str     the workspace name that the path is relative to

Examples:

  download all blobs in the 'myrecent' folder (and its children) of the BLOB store area for job2998 to local directory ./zip::

  > xt download myrecent/** ./zip --job=job2998

