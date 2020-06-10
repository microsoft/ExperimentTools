.. _config:  

========================================
config command
========================================

Usage::

    xt config [OPTIONS]

Description::

        The --create option accepts a template name to create a new local XT config file.

    The currently available templates are:
        - philly   (create config file for Philly users)
        - batch    (create config file for Azure Batch users)
        - aml      (create config file for Azure Machine Learning users)
        - pool     (create config file for users running ML apps on local machines)
        - all      (create config file for users who want to have access to all backend services)
        - empty    (create an empty config file)


Options::

  --create      str     specifies that a local XT config file should be created with the specified template [one of: philly, batch, aml, pool, all, empty]
  --default     flag    specifies that the XT DEFAULT config file should be viewed as a readonly file
  --reset       flag    the XT default config file should be reset to its original setting
  --response    str     the response to use if a new config file needs to be created

Examples:

  edit the user's local config file::

  > xt config

.. seealso:: 

    - :ref:`XT Config File <xt_config_file>`
    - :ref:`Preparing a new project for XT <prepare_new_project>`
