.. _view_controller_status:  

========================================
view controller status command
========================================

Usage::

    xt view controller status <job-id> [OPTIONS]

Description::

        uses the XT controller to view the status of the specified job/node

Arguments::

  job-id    the name of the job whose node will be restarted

Options::

  --node-index    str    the 0-based node index to be restarted

Examples:

  view the status of the 2nd node running job100::

  > xt view controller status job100 --node=1

