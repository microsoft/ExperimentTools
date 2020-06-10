.. xt_release_notes_1_0:

========================================
Welcome to XT
========================================

Welcome to eXperimentTools Release 1.0! This document describes key items for this release in a quick-reference format.

eXperimentTools (XT) is a command line tool and API to manage and scale Machine Learning (ML) experiments, with a consistent model of workspaces and job runs, across a variety of Azure cloud compute services. 

XT data management, based on Azure Storage and Azure Cosmos DB, enables tracking, run compares, reruns, and sharing of your ML experiments. Experiment storage contains user-defined workspaces, that contain sets of user-run experiments. Upload your data/models to cloud storage before job runs, and start new experiments on specified local or cloud compute machines.

eXperimentTools 1.0 supports the following operating systems:

 - Windows 10
 - Ubuntu 18.04 LTS

XT provides a demonstration program through a separate Python script called **xt_demo**, where you can explore XT's features using a simplified Basic mode or a full-featured Advanced mode.

.. note:: You can run the XT Demo, and the XT CLI, in two different modes: Basic mode and Advanced mode. 

You define XT's configuration through an **xt_config** settings file. It is designed to contain all the key settings and reachability information for your Azure cloud services that XT relies on for running experiments and analyzing machine learning (ML) data. You can use multiple copies of the xt_config file to manage different configurations. 

XT provides a **default xt_config file** that contains examples of every key cloud service settings block. After you install XT, you can activate it in your Python virtual environment and then open the default xt_config file:

.. code-block::

    > activate xt
    > xt config --default

You will not be able to edit this file (you can copy and paste settings from it at any time); it is managed by the XT application. To create a new xt_config file for editing your own settings, enter:

.. code-block::

    > xt config 

This is called the *local* xt_config file. You can place this file in any directory where you will run XT commands. You can also use as many versions as needed for different ML configurations.

**********************
XT in Basic mode
**********************

The demo and the XT CLI default to Basic mode, which contains a series of steps that rely on a limited set of cloud services. It uses a single compute target based on Azure Batch or your local computer. 

In Basic mode, the XT CLI supports the following capabilities:

    - Single workspace 
    - Single experiment 
    - Multiple jobs 
    - Multiple runs 
    - Single blob container  
    - Supports custom Docker containers 

XT Basic Mode Demo supports a single instance of the following types of compute services:

    .. only:: not internal

        - Azure Batch (optional)
        - Local computer or VM

    .. only:: internal

        - Azure Batch 
        - Local computer or VM
        - Philly

For XT operation in Basic mode, the following Azure cloud services will also work:

    - Azure Key Vault (required)
    - Azure Storage (required)
    - Azure Cosmos DB - MongoDB (required)
    - Azure Container Registry (Optional)
    - Azure Virtual Machine (Optional)
    - Generic Remote Server (Optional)
 

XT in basic mode supports a subset of the XT command set. 

****************************
XT in Advanced mode
****************************

Users can switch XT from Basic mode to the fully-featured Advanced mode by editing the **advanced-mode** parameter in their local xt_config.yaml file to the value **true** (its default is **false**).

.. code-block::

    general:
        advanced-mode: true    #sets XT CLI to Advanced mode

The Advanced mode uses the full suite of Azure services supported by XT for ML experiments:

.. only:: not internal

    - Azure Batch
    - Azure Container Registry
    - Azure Cosmos DB - MongoDB
    - Azure Storage
    - Azure Key Vault
    - Azure Virtual Machine / Virtual Machine Scale Set
    - Generic Remote Server
    - Azure Machine Learning Services

.. only:: internal

    - Azure Batch
    - Azure Container Registry
    - Azure Cosmos DB - MongoDB
    - Azure Storage
    - Azure Key Vault
    - Azure Virtual Machine / Virtual Machine Scale Set
    - Generic Remote Server
    - Azure Machine Learning Services
    - Philly

.. note:: You can also use your local system or VMs as a compute target in either Basic or Advanced mode. 

The XT Demo also expands to a longer sequence of steps. Advanced mode also supports an expanded set of XT tools and CLI command set. You conduct your own experiments using the :ref:`xt run command <run>` to submit jobs to XT. 

For more information, see the :ref:`Getting Started <getting_started>` topic.

.. only:: internal

    ******************************
    XT Tutorials
    ******************************

    The XT documentation also provides a :ref:`Micro_Mnist tutorial <micro_mnist>`, which is a Python script that demonstrates how programs run under XT write log and checkpoint information to the cloud and use that information to detect and process job run restarts on low-priority compute services. If you will run this experiment from a Ubuntu Linux 18.04 host, you will also need to ensure correct operation of the Blobfuse virtual file system for use on the Azure blob storage cloud service. 

    The XT Demo also uses the features demonstrated through MicroMnist.

    .. note:: You will need to use the same target names if you decide to use your local xt_config file in the demo scenario. 

-------------
What's Next?
-------------

Go to :ref:`Getting Started with XT <getting_started>` for a deeper introduction to XT and its features.

After installation and running the XT demo, you can set up your Azure cloud services to work with XT. You can do so by running an XT command to create an Azure services template. You load this template into Azure to automate your cloud services setup for further work with XT. See :ref:`Creating Azure Cloud Services for XT <creating_xt_services>` for more information.

:ref:`Go here to find out more about XT Basic mode and XT Advanced mode <xt_operation_modes>`.

Want to let us know about anything? Let the XT team know `by filing an issue in our repository on GitHub! <https://github.com/microsoft/ExperimentTools/issues>`_ We look forward to hearing from you!
