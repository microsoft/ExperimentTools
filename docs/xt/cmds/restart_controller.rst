.. _restart_controller:  

========================================
restart controller command
========================================

Usage::

    xt restart controller <job-id> [OPTIONS]

Description::

        uses the XT controller to simulate a service-level restart on the specified job/node

Arguments::

  job-id    the name of the job whose node will be restarted

Options::

  --delay         float    the number of seconds to delay after cancelling runs and before restarting the controller
  --node-index    str      the 0-based node index to be restarted

Examples:

  simulate a service-level restart on job23, node 1::

  > xt restart controller job23 --node=1

