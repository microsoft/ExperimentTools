.. _getting_started:

========================================
Getting Started with XT
========================================

This topic introduces you to XT and its various components, and describes how to install and run the XT package and its :ref:`demonstration Python script <running_the_demo>` (called **xt demo**). We also provide a list of additional resources for reference and inspiration at the end of this topic.

XT is a command line tool to manage and scale Machine learning (ML) experiments, with a uniform model of workspaces and runs, across a variety of cloud compute services. It supports ML features such as :ref:`live and post Tensorboard viewing <tensorboard>`, :ref:`hyperparameter searching <hyperparameter_search>`, and :ref:`ad-hoc plotting <plot>`.

Key XT features include the following:

    - XT's experiment store, based on Azure Storage and Azure Cosmos DB, enables tracking, run compares, reruns, and sharing of your ML experiments. It consists of user-defined workspaces, that can contain sets of user-run experiments. 
    - You can upload data/models to storage before job runs and start new experiments on specified machine(s). 
    - XT supports hyperparameter tuning runs using Grid search, Random search, and :ref:`distributed grid descent (DGD) algorithm <dgd>`. 
    - You can monitor job status with :ref:`Tensorboard <tensorbd>` and XT's event logs, and generate reports during or after job runs and selective use of filtering, sorts and data columns. 

XT provides access to scalable compute resources, so you can run experiments on your local machine, or on other local computers or provisioned VMs. You can run multiple experiments in parallel and on larger computers or arrays of computers, or on other cloud compute services. 

In all cases, you need to make sure both your :ref:`XT client computer <xtclientreqs>` (the machine on which you run and manage XT jobs) and :ref:`the compute nodes you use <computenodereqs>` match the requirements to successfully run XT. 

.. _xtclientreqs:

-----------------------
XT Client Requirements
-----------------------

Requirements for installing and running XT are:
    - Windows 10 
    - Linux OS (tested on Ubuntu 18.04 LTS)
    - Python 3.6 required
    - XT is verified to work with Anaconda, and should work with Virtualenv and other virtual environments
    - User must have a Microsoft account (required for authenticated access to Azure computing storage and resources)

.. only:: internal

    - For Linux users who will be using the Microsoft internal Philly services, you should install **curl**. Go to https://www.cyberciti.biz/faq/how-to-install-curl-command-on-a-ubuntu-linux/ to do so.

.. Note:: XT supports all popular Machine Learning frameworks. The following procedure installs PyTorch because it supports the XT demo. XT also supports important ML tools such as TensorFlow. You can also use :ref:`hyperparameter searching <hyperparameter_search>` to tune and improve your machine learning models.

******************************************
Support for virtualenv Python environments
******************************************

By default, XT supports `Anaconda <https://www.anaconda.com/>`_ without modification. You can use another Python virtual environment by making a few small changes to your XT installation's local xt_config file. 

.. note:: Full details to be added in an upcoming update.

------------------
Installing XT
------------------

XT package installation is straightforward. Follow these steps to set up XT on your computer. You may need to `install Anaconda <https://www.anaconda.com/distribution/>`_ on your system in order to follow these steps:

  **1. Prepare a conda virtual environment:**
      
      .. code-block::

          conda create -n xt python=3.6
          conda activate xt
          conda install pytorch torchvision cudatoolkit=10.1 -c pytorch

  **2. Ensure you have the latest pip**
  
      .. code-block::

          python -m pip install --upgrade pip

  **3. Install XT:**

      .. code-block::

          pip install -U xtlib

.. only:: internal

  **Additional Installation Steps for Internal Microsoft users**

  Microsoft-internal users, including users of the Philly and XT sandbox services, will also need to install the **xtlib-internal** program. 
  
  Take the following steps in your Python virtual environment: 

    **1. Install keyring and artifacts-keyring (to authenticate with Azure artifacts)**
    
      .. code-block::

          pip install keyring artifacts-keyring
    
    **2. Install xtlib-internal**
    
      .. code-block::

          pip install xtlib-internal -i https://pkgs.dev.azure.com/msresearch/e709de22-dd8c-4b66-a84e-688f2a391d01/_packaging/eXperimentTools/pypi/simple/

    **3. Reset the xt config file to include Philly and the sandbox services:** 

    *Note: you'll need to do this again after updating xt or xtlib*

      .. code-block::
      
          xtlib-internal config --reset

Check the following subsections for more information.

After installing XT, decide on the direction you need to follow to run the XT demo, based on whether or not you have an active set of Azure cloud services to support machine learning:

    - If you are running the demo in Basic Mode, you can do so without further preparation.
    
    - If you need to set up some or all of the Azure cloud services to support XT and to support running the demo, you run an XT utility to generate an Azure template and then use it to set up your cloud services through the Azure portal (see :ref:`Creating Azure Cloud Services for XT <creating_xt_services>` for more information).

    - If you already have the needed Azure cloud services, set them up to work with your new XT installation (see :ref:`Understanding the XT Config file <xt_config_file>` for more information);

.. _running_the_demo:

---------------------------
Running the XT Demo
---------------------------

After you finish installing XT, you can run the XT Demo.

XT offers a self-contained demo that walks you through several usage scenarios, using multiple Machine Learning backends. Each step of the demo, which you run from your Python virtual environment's command line interface, provides descriptions explaining what that step does during the course of a sample experiment.

    **1. Start XT on your system:**
        
        .. code-block::

            > activate xt  # activates the XT environment  

    **2. CREATE a set of demo files:**

        .. code-block::

            > xt create demo xt_demo

            This creates 2 files and 1 subdirectory in the *xt_demo* directory:
                - xt_config_overrides.yaml     (xt config settings)
                - xt_demo.py                   (the demo script)
                - code                         (a subdirectory of code for the demo)

    **3. Start the XT demo:**

        .. code-block::

            > cd xt_demo
            > python xt_demo.py

        Once started, you can navigate thru the demo with the following keys:
            - ENTER (to execute the current command)
            - 's'   (to skip to the next command)
            - 'b'   (to move to the previous command)
            - 'q'   (to quit the demo)

While you run the demo, you may hit a point where it stops running. This typically happens when a numbered demo step relies on a cloud service that may not yet be configured. To continue the demo, note the step where the demo stopped, and enter *python xt_demo.py* once again. Then, press the 's' key to step through the demo past the numbered step where you previously stopped.

***********
Demo Modes
***********

The XT Demo, and the XT CLI, can run in two different modes: Basic mode and Advanced mode. 

The XT demo defaults to the shorter Basic mode; which contains a shorter series of steps that rely on a more focused set of cloud services. XT Basic mode provides an accessible, smaller command set that still reflects researchers' key experiment workflows. 

For more information about using XT Basic mode and XT Advanced mode, see the following topic,  :ref:`XT: Using Basic Mode vs. Advanced Mode <xt_operation_modes>`.

------------
Next Steps
------------

Want to let us know about anything? Let the XT team know by filing an issue in our repository at `GitHub! <https://github.com/microsoft/ExperimentTools/issues>`_ We look forward to hearing from you!

After installation and running the XT demo, you can set up your Azure cloud services to work with XT. You do so by editing the properties inside an important configuration file called the local *xt_config* file. See :ref:`Understanding the XT Config file <xt_config_file>` for more information.

For those just beginning to explore ML on the Microsoft Azure cloud platform, see the `What is Azure Machine Learning? <https://docs.microsoft.com/en-us/azure/machine-learning/>`_ page, and `What is Azure Batch? <https://docs.microsoft.com/en-us/azure/batch/batch-technical-overview/>`_, which gives a full description of the Azure Batch service.

To get a closer look at running jobs using the **xt run** command, see :ref:`XT run command <run>`.