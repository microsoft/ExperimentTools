.. _explore:  

========================================
explore command
========================================

Usage::

    xt explore <aggregate-name> [OPTIONS]

Description::

        run the Hyperparameter Explorer on the specified job or experiment

Arguments::

  aggregate-name    the name of the job or experiment where run have been aggregated (hyperparameter search)

Options::

  --cache-dir                 str      the local directory used to cache the Hyperparameter Explorer runs
  --log-interval-name         str      the name of the log interval hyperparameter
  --primary-metric            str      the name of the metric to explore
  --sample-efficiency-name    str      the name of the sample efficiency metric
  --step-name                 str      the name of the step/epoch metric
  --steps-name                str      the name of the steps/epochs hyperparameter
  --success-rate-name         str      the name of the success rate metric
  --time-name                 str      the name of the time metric
  --timeout                   float    the maximum number of seconds the window will be held open
  --workspace                 str      the workspace that the experiment resides in

Examples:

  explore the results of all runs from job2998::

  > xt explore job2998

