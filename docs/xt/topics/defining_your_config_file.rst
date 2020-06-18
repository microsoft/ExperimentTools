.. _defining_your_config_file:

=========================================
Quick Template-Based Setup for XT
=========================================

.. only:: internal

    If you already have an established Azure compute service such as Azure Batch, Philly, Azure Nachine Learning (AML) or want to use your local resources to run XT experiments, you can do so more quickly by using the XT CLI's **xt config --create** command. It uses templates to efficiently create an xt_config.yaml file, that you can edit with your services' ID values to get up and running fast. All you need to know about is the names and settings of your Azure compute service, along with the other Azure services you're running. 

    Supported compute service values include the following:

        - Philly
        - Batch
        - AML
        - Pool 

.. only:: not internal

    If you already have an established Azure compute service such as Azure Batch or Azure Nachine Learning (AML), or want to use your local resources to run XT experiments, you can do so more quickly by using the XT CLI's **xt config --create** command. It uses templates to efficiently create an xt_config.yaml file, that you can edit with your services' ID values to get up and running fast. All you need to know about is the names and settings of your Azure compute service, along with the other Azure services you're running.  

    Supported service values include the following:

        - Batch
        - AML
        - Pool 

The Pool setting denotes your local computer or VMs.

After installing XT, enter the following at the prompt:

.. code-block::

    (xt) C:\ExperimentTools> xt config --create <service-type>

As in:

.. code-block::

    (xt) C:\ExperimentTools> xt config --create batch

The **xt config** command writes a new xt_config.yaml file to the current directory. It will overwrite that file if it is already in the directory, so ensure that file is backed up if necessary. An example of the xt_config file output for the Batch service:

.. code-block::

    # local xt_config.yaml (for Azure Batch compute services)

    external-services:
        phoenixbatch: {type: "batch", key: "$vault", url: ""}
        phoenixkeyvault: {type: "vault", url: ""}
        phoenixmongodb: {type: "mongo", mongo-connection-string: "$vault"}
        phoenixregistry: {type: "registry", login-server: "", username: "", password: "$vault", login: "true"}
        phoenixstorage: {type: "storage", provider: "azure-blob-21", key: "$vault"}

    xt-services:
        mongo: "phoenixmongodb"
        storage: "phoenixstorage"
        target: "batch"
        vault: "phoenixkeyvault"

    compute-targets:
        batch: {service: "phoenixbatch", vm-size: "", azure-image: "dsvm", nodes: 1, low-pri: True, box-class: "dsvm", setup: "batch"}

    azure-batch-images:
       dsvm: {offer: "linux-data-science-vm-ubuntu", publisher: "microsoft-dsvm", sku: "linuxdsvmubuntu", node-agent-sku-id: "batch.node.ubuntu 18.04", version: "latest"}
        ubuntu18: {offer: "UbuntuServer", publisher: "Canonical", sku: "18.04-LTS", node-agent-sku-id: "batch.node.ubuntu 18.04", version: "latest"}

    general:
        advanced-mode: true
        azure-tenant-id: null
        distributed: False
        env-vars: {}
        experiment: "exper1"
        maximize-metric: True
        primary-metric: "test-acc"
        step-name: "step"
        workspace: "ws1"

.. note::

    Compute nodes or local VMs will still require Ubuntu 18.04 LTS to operate as a cluster for XT experiments.

You will still need to refer to your services' Azure Dashboard pages to get the actual names of your service instances and the various settings.

If you are simply using your Local system to test and run XT, you can use the following:

.. code-block::

    (xt) C:\ExperimentTools> xt config --create pool

The config file appears as follows:

.. code-block::

    # local xt_config.yaml (for local machine and Pool compute service)

    external-services:
        phoenixkeyvault: {type: "vault", url: ""}
        phoenixmongodb: {type: "mongo", mongo-connection-string: "$vault"}
        phoenixregistry: {type: "registry", login-server: "", username: "", password: "$vault", login: "true"}
        phoenixstorage: {type: "storage", provider: "azure-blob-21", key: "$vault"}

    xt-services:
        mongo: "phoenixmongodb"
        storage: "phoenixstorage"
        target: "local"
        vault: "phoenixkeyvault"

    compute-targets:
        local: {service: "pool", boxes: ["local"], setup: "local"}
        local-docker: {service: "pool", boxes: ["local"], setup: "local", docker: "pytorch-xtlib-local"}

    boxes:
        local: {address: "localhost", max-runs: 1, actions: [], setup: "local"}

    setups:
        local: {activate: "$call conda activate $current_conda_env", conda-packages: [], pip-packages: []}

    dockers:
        pytorch-xtlib: {registry: "phoenixregistry", image: ""}
        pytorch-xtlib-local: {registry: "", image: ""}

    general:
        advanced-mode: False
        azure-tenant-id: null
        distributed: False
        env-vars: {}
        experiment: "exper1"
        maximize-metric: True
        primary-metric: "test-acc"
        step-name: "step"
        workspace: "ws1"

The config files still reflect the need to have services for MongoDB database, secure Key Vault and storage, :ref:`as described in Creating Azure Cloud Services for XT <creating_xt_services>`. They are the three services all XT installations must use. The templates also do not exclude the need to add other services to the configuration based on the struture of your MI experiments.  

.. seealso::

    Want to let us know about anything? Let the XT team know by filing an issue in our repository at `GitHub! <https://github.com/microsoft/ExperimentTools/issues>`_ We look forward to hearing from you!

    After installation and running the XT demo, you can set up your Azure cloud services to work with XT. You can do so by running an XT command to create an Azure services template. You load this template into Azure to automate your cloud services setup for further work with XT. See :ref:`Creating Azure Cloud Services for XT <creating_xt_services>` for more information.

    For those just beginning to explore ML on the Microsoft Azure cloud platform, see the `What is Azure Machine Learning? <https://docs.microsoft.com/en-us/azure/machine-learning/>`_ page, and `What is Azure Batch? <https://docs.microsoft.com/en-us/azure/batch/batch-technical-overview/>`_, which gives a full explanation of the Azure Batch service.

    After creating your XT services, you need to set up your XT project to do your first job runs. See :ref:`Defining Code Changes for your XT Installation <prepare_new_project>` for more information.



