.. _view_controller_log:  

========================================
view controller log command
========================================

Usage::

    xt view controller log <job-id> [OPTIONS]

Description::

        uses the XT controller to view it's log on the specified job/node

Arguments::

  job-id    the name of the job whose node will be restarted

Options::

  --node-index    str    the 0-based node index to be restarted

Examples:

  view the conntroller log for single node job100::

  > xt view controller status job100

