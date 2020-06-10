.. _delete_blobs:  

========================================
delete blobs command
========================================

Usage::

    xt delete blobs [path] [OPTIONS]

Description::

        deletes specified Azure store blobs

Arguments::

  path    the path for the store blob or wildcard

Options::

  --experiment    str    the experiment that the path is relative to
  --job           str    the job id that the path is relative to
  --run           str    the run name that the path is relative to
  --share         str    the name of the share that the path is relative to
  --workspace     str    the workspace name that the path is relative to

Examples:

  delete the blobs under project-x for workspace curious::

  > xt delete blobs project-x --work=curious

