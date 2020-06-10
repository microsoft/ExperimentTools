.. _view_mongo:  

========================================
view mongo command
========================================

Usage::

    xt view mongo <name> [OPTIONS]

Description::

        view the mongo-db JSON data associated with the specified run

Arguments::

  name    the name of the run or job to show the mongo-db data for

Options::

  --workspace    str    the workspace that the run is defined in

Examples:

  view the mongo-db information for run23 in the curious workspace::

  > xt view mongo curious/run23

