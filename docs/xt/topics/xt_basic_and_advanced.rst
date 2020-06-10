.. _xt_operation_modes:

======================================
Using XT Basic Mode vs. Advanced Mode 
======================================

.. note:: You can run the XT Demo, and the XT CLI, in two different modes: Basic mode and Advanced mode. 

The demo and the XT application default to Basic mode; the demo contains a shorter series of steps that rely on a more focused set of cloud services. XT Basic mode provides an accessible, smaller command set that still reflects researchers' key experiment workflows.

However, Basic mode is powerful enough that you can run experiments at significant scale using Basic mode commands and resources alone. It doesn’t limit the size of your experiment - just the types of resources (and in some cases the number of resources) you’re able to use. For simplicity, Basic mode also reduces the command set that’s available to you. Basic mode does not change the services you can use, although it does exclude Azure ML as a compute node target. 

**************************
The Basic Mode workflow
**************************

In Basic mode, XT helps you follow a specific research workflow. The workflow typically consists of the following:

    1. Select your Azure workspace for XT by adding it to your local XT config file.
    2. Upload your code and testing data to your shared cloud storage.
    3. Define your job in XT.
    4. Submit your experiment. Edit your xt_config file for your job where needed.
    5. Monitor your job status through metrics and logs, for debugging.
    6. Retrieve and list a job report or a run report.

The Basic mode provides a simplified CLI Command set to support this workflow. It is as follows:

.. code-block:: none

    (xt) c:\eXperimentTools> xt ?

     commands:
      cancel job                  cancels the specified job and its active or queued runs
      clear credentials           clears the XT credentials cache
      config                      opens an editor on the user's LOCAL XT config file
      create demo                 creates a set of demo files that can be used to quickly try out various XT features
      create services template    generate an Azure template for creating a set of resources for an XT Team
      extract                     download all files associated with the run to the specified directory
      help                        Shows information about how to run XT
      help topics                 Displays the specificed help topic, or the available help topics
      list jobs                   displays a job report for the specified jobs
      list runs                   displays a run report for the specified runs
      plot                        plot the logged metrics for specified runs in a matrix of plots
      run                         submits a script or executable file for running on the specified compute target
      view console                view console output for specified run

***********************************************
What compute node types does XT Basic support?
***********************************************

XT Basic Mode supports the following compute node resources:

.. only:: not internal

    - Azure Batch
    - Your local computer or VM

.. only:: internal

    - Azure Batch
    - Philly
    - Your local computer or VM

XT Basic mode's demo shows how XT Basic mode runs on both your client computer using a Batch cloud resource as a compute node. It also shows how XT can run using your local computer as a computer node target. 

:ref:`Ensure your compute nodes meet the requirements for your work <computenodereqs>`.

XT's Advanced mode provides an expanded command set, more job and run management and monitoring/debugging features, quick job reruns, and a larger collection of collaboration and resource sharing features.

*********************************
Switching to Advanced mode
*********************************

Users can switch from Basic to the fully-featured Advanced mode by editing the **advanced-mode** parameter in the default xt_config file to the value **true** (its default is **false**). Do the following:

1) Make sure you are in the main directory for your XT installation. In your Python environment's command prompt, enter::

    xt config

2) Your computer's default text editor opens with a new xt_config file instance. It reads as follows::

    # local xt_config.yaml
    # uncomment the below lines to start populating your config file

    #general:
        #workspace: 'ws1'
        #experiment: 'exper1'

3) Add the following line under the 'general' heading::

    general:
        advanced-mode: true   

4) Ensure that the **general** heading is not commented out. Save your changes. The next time you run the XT demo it will run the full demo with a longer series of steps during the demonstration.

.. note:: A **false** value for the advanced-mode setting keeps the XT demo in Basic mode.

The Advanced mode uses the full suite of Azure services supported by XT for ML experiments. (Basic mode can also use them, but normally as a single instance.) It uses the following Azure cloud services to help you develop, test and deploy new Machine Learning experiments:

.. only:: not internal

    - Azure Cosmos DB - MongoDB (**Required**)
    - Azure Storage (**Required**)
    - Azure Key Vault (**Required**)
    - Azure Batch (Optional)
    - Azure Container Registry (Optional)
    - Azure Virtual Machine / Virtual Machine Scale Set (Optional)
    - Generic Remote Server (Optional)
    - Azure Machine Learning Services (Optional)

.. only:: internal

    - Azure Cosmos DB - MongoDB (**Required**)
    - Azure Storage (**Required**)
    - Azure Key Vault (**Required**)
    - Azure Batch (Optional)
    - Azure Container Registry (Optional)
    - Azure Virtual Machine / Virtual Machine Scale Set (Optional)
    - Generic Remote Server (Optional)
    - Azure Machine Learning Services (Optional)
    - Philly (Optional)

Advanced mode also provides support for an expanded set of XT tools and supports the complete XT CLI command set. You conduct your own experiments using the :ref:`**xt run** command <run>` to submit jobs to XT. 

-----------------
Next steps
-----------------

After installation and running the XT demo, you can set up your Azure cloud services to work with XT. You can do so by using an XT command to create an Azure services template. :ref:`You load this template into Azure to automate your cloud services deployment for further work with XT <creating_xt_services>`.