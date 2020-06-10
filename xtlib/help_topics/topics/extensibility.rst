.. _extensibility:

======================================
Extensibility in XT 
======================================

XT can be customized and extended by the user.  The main method of customization is thru a local XT config file and
the XT command line options.

The main methods of extending XT are:

    - adding additonal entries to the list properties of the XT config file:

        - external-services
        - compute-targets
        - environments
        - azure-batch-images
        - boxes

    - adding additional code providers to the providers sections in the XT config file:

        - command
        - compute
        - hp-search
        - storage

-----------------------------------
Adding new code providers
-----------------------------------
   
The general way to add a new code provider is to:
    - create a python class that implements the interface associated with the provider type (compute, hp-search, or storage)
    - add the provider name and its **code path** as a key/value pair to the associated provider dictionary in a local XT config file
    - ensure the provider package is available to XT (in the Python path, or a direct subdirectory of your app's working directory), so that 
      XT can load it when needed (which could be on the XT client machine and/or the compute node)

A **code path** is a string of the form: 

    package.module.class

Where:

     - **package** is your provider code directory
     - **module** is the name of your Python file containing the provider code class implementation (without the ".py" file extension)
     - **class** is the name of your Python class that implements the provider interface

--------------------------
Adding new XT commands
--------------------------

Adding new XT commands is slightly different than adding other code providers.  Instead of implementing a provider interface, you will need to:
    - import the **xtlib.qfe** module so that you can use its decorators
    - create a python class that will hold one or more command implementations
    - for each new command, add a decorated method to your class
    - add the provider name and its **code path**  as a key/value pair to the **command** provider dictionary in a local XT config file
    - ensure the provider package is available to XT (in the Python path, or a direct subdirectory of your app's working directory), so that 
      XT can load it when needed (which could be on the XT client machine and/or the compute node)
 
---------------------------------------------------------
How to ensure your provider code is available to XT
---------------------------------------------------------

There are a few basic ways to make the provider code available to XT; choose the method that fits your working style
and meets the needs of the provider code being on the local machine, a VM whose configuration you manage, or a service-managed compute node.

You can make your provider code available to XT by:
   - setting the environment variable PYTHONPATH (for the machine in question) to point to the **parent** directory of your provider code directory
   - install your code provider on the machine in question using an associated setup.py file and the **pip install -m .** command
   - for service-managed compute nodes, you can include your code provider's directory in the code that gets uploaded to storage 
     when your job is run.  use the **code-dirs** property of the **code** section of your local XT config to specify this.  this will
     ensure that your provider directory will be downloaded on the compute node as a direct subdirectory of your working directory, and available
     to XT.

.. seealso:: 

    - :ref:`XT Config file <xt_config_file>`
    - :ref:`Command options <cmd_options>`
    - :ref:`Adding new XT commands <extend_commands>`
    - :ref:`Adding a new XT compute service <extend_compute>`
    - :ref:`Adding a new XT Hyperparameter Search algorithm <extend_hp_search>`
    - :ref:`Adding a new XT storage service <extend_storage>`
    - `The hitchhiker's guide to Python packaging <https://the-hitchhikers-guide-to-packaging.readthedocs.io/en/latest/quickstart.html>`_
