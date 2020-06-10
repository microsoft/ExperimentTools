.. _view_blob:  

========================================
view blob command
========================================

Usage::

    xt view blob <path> [OPTIONS]

Description::

        display the contents of the specified storage blob

Arguments::

  path    the relative or absolute store path to the blob)

Options::

  --experiment    str    the experiment that the path is relative to
  --job           str    the job id that the path is relative to
  --run           str    the run name that the path is relative to
  --share         str    the share name that the path is relative to
  --workspace     str    the workspace name that the path is relative to

Examples:

  display the contents of the specified file from the 'after' snapshot for the specified run::

  > xt view blob after/output/userapp.txt --run=curious/run14

