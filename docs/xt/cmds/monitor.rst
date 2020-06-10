.. _monitor:  

========================================
monitor command
========================================

Usage::

    xt monitor <name> [OPTIONS]

Description::

        view a job's log file, as it grows in real-time

Arguments::

  name    The name of the run or job to be monitored

Options::

  --escape        int      breaks out of attach or --monitor loop after specified # of seconds
  --jupyter       flag     to monitor a job from a jupyter notebook (AML only)
  --log-name      str      the name of the log file to be monitored
  --node-index    int      the node index for multi-node jobs
  --sleep         float    the number of seconds between download calls
  --workspace     str      the workspace that the run resides within

Examples:

  monitor job3321's primary log file::

  > xt monitor job3321

