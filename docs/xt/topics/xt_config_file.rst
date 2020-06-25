.. _xt_config_file:

================================
Understanding the XT Config file
================================

This topic describes how to fully onboard to your XT environment. 

To create a new set of Azure cloud services for your XT installation, follow the steps in this topic to get up and running. 

By default, XT does not come with predefined Azure services. 

.. note:: If you are starting from scratch, and need to configure the Azure services to support your new XT deployment, see :ref:`Creating your Azure Cloud Services for XT <creating_xt_services>`.

------------------------------
Overview of the XT Config File
------------------------------

You control XT using an extensive set of properties in the *XT config file*. Its properties, organized into sections, determine how you work with XT and what cloud resources you use with XT.

XT's *default XT config file* defines these properties when you install XT. It is a *read-only* file that's installed as part of the XTLib package. Users customize their Experiment Tools installation by editing a *local XT config file*, which resides in the user account's home directory. It overrides the default settings.

To ensure XT works with your cloud services, you must copy, paste, and edit selected entries from the default xt_config file to your local version. Your XT installation runs based on the settings you define here.

You can find the original copy of the local xt_config file in the home directory for your user account.

.. note:: In Windows, for a user named "Contoso," their local XT config file (xt_config.yaml) is located in the C:/Users/contoso/ folder. In Linux, the local config file is in the /home/<username>/ folder, as in /home/contoso/xt_config.yaml.

Your local config file should only contain the XT properties that you change. It is typically smaller then the default config file. 

You can also use XT command options to override XT Config properties during your experiments. Check the help for each command to see available options.

For quick reference, enter the following command to view the default xt_config file in the XT installation:

.. code-block::

    (xt) C:\ExperimentTools> xt config --default

The default xt_config file appears in your computer's default editor.

.. _xt_config_external:

**************************************
Config File Section: External Services
**************************************

The **external-services** section defines the service names and credentials for the cloud services used by your XT installation.

XT works with 4 types of external cloud services.

+-------------------------------+-----------------------------------+
| External service type         | Description                       |
+===============================+===================================+
| **Compute service**           | Services that can run ML jobs     |
+-------------------------------+-----------------------------------+
| **Storage service**           | Services where files (blobs) can  |
|                               | be read, written and updated      |
+-------------------------------+-----------------------------------+
| **MongoDB Service**           | Database services that uses       |
|                               | the MongoDB interface             |
+-------------------------------+-----------------------------------+
| **Container registry**        | Services that can store (register |
|                               | and retrieve) Docker containers   |
+-------------------------------+-----------------------------------+

Entries for external services in the XT config file use the following syntax:

    name: {type: "servicetype", prop: "value"}

Where:

    - **name** is the service name that's recognized by the service
    - **servicetype** is one of the following constants: **batch**, **aml**, **storage**, **mongo**, **registry**
    - **prop** and **value** represent other credentials appropriate to the associated service.

Service properties by each service type are the following:

    - batch       - **key**, **url**
    - aml         - **subscription-id**, **resource-group**
    - storage     - **key**
    - mongo       - **mongo-connection-string**
    - registry    - **login-server**, **username**, **password**, **login**

XT's default xt_config file contains a complete sample list of cloud services that you can adapt in your local xt config file, to use the services under your Azure account. 

.. only:: not internal

  .. code-block::

    external-services:
        # compute services
            xtsandboxbatch: {type: "batch", key: "$vault", url: "https://xtsandboxbatch.eastus.batch.azure.com"}
            aml-sandbox-ws: {type: "aml", subscription-id: "43de1a51-d0f9-4494-8c57-bcc6ba4202e4", resource-group: "xt-sandbox"}
            canadav100ws: {type: "aml", subscription-id: "db9fc1d1-b44e-45a8-902d-8c766c255568", resource-group: "canadav100"}

        # storage services
            xtsandboxstorage: {type: "storage", provider: "azure-blob-21", key: "$vault"}
            filestorage: {type: "storage", provider: "store-file", path: "c:\\file_store"}

        # mongo services
           xt-sandbox-cosmos: {type: "mongo", mongo-connection-string: "$vault"}
    
        # vault services
            sandbox-vault: {type: "vault", url: "https://xtsandboxvault.vault.azure.net/"}
    
        # registry services
            xtsandboxregistry: {type: "registry", login-server: "xtsandboxregistry.azurecr.io", username: "xtsandboxregistry", password: "$vault", login: "true"}
            xtcontainerregistry: {type: "registry", login-server: "xtcontainerregistry.azurecr.io", username: "xtcontainerregistry", password: "$vault", login: "true"}

.. only:: internal

  .. code-block::

    external-services:
        # compute services
            xtsandboxbatch: {type: "batch", key: "$vault", url: "https://xtsandboxbatch.eastus.batch.azure.com"}
            aml-sandbox-ws: {type: "aml", subscription-id: "43de1a51-d0f9-4494-8c57-bcc6ba4202e4", resource-group: "xt-sandbox"}
            canadav100ws: {type: "aml", subscription-id: "db9fc1d1-b44e-45a8-902d-8c766c255568", resource-group: "canadav100"}

        # storage services
            xtsandboxstorage: {type: "storage", provider: "azure-blob-21", key: "$vault"}
            filestorage: {type: "storage", provider: "store-file", path: "c:\\file_store"}

        # mongo services
           xt-sandbox-cosmos: {type: "mongo", mongo-connection-string: "$vault"}
    
        # vault services
            sandbox-vault: {type: "vault", url: "https://xtsandboxvault.vault.azure.net/"}
    
        # registry services
            xtsandboxregistry: {type: "registry", login-server: "xtsandboxregistry.azurecr.io", username: "xtsandboxregistry", password: "$vault", login: "true"}
            xtcontainerregistry: {type: "registry", login-server: "xtcontainerregistry.azurecr.io", username: "xtcontainerregistry", password: "$vault", login: "true"}
            philly-registry: {type: "registry", login-server: "phillyregistry.azurecr.io", login: "false"}
            philly: {type: "philly"}

.. _xt_config_xt_services:

********************************
Config File Section: XT Services
********************************

The **xt-services** section identifies the external service XT uses for each of the following: 

    - XT uses the **storage** service for storage of all workspace, experiment, and run related files, include source code, log files, and output files.
    - XT uses the **mongo** service as the database (with a MongoDB interface) for fast access to job stats and metrics.
    - XT uses the **target** service as the default compute target for running jobs. Target services are defined in the **Compute Targets** section of the XT config file.

The **xt-services** section from the default xt_config file:

.. code-block::

    xt-services:
        storage: "xtsandboxstorage"        # storage for all services 
        mongo: "xt-sandbox-cosmos"         # database used for all runs across services
        vault: "sandbox-vault"             # where to keep sensitive data (service credentials)

Replace the values (in double quotemarks) for each with the names of your cloud service instances that are active in Azure.

.. _xt_config_compute:

******************************************
Config File Section: Compute Targets
******************************************

.. note:: You can use your local system as a compute target in either Basic or Advanced mode. You specify it as --target="local".

The **compute-targets** section defines the available configured compute services that XT will use for running your machine learning (ML) apps.  

You can define several types of Compute targets.

+-------------------------------+------------------------------------+
| **Batch**                     | Refers to the Azure Batch service  |
|                               | listed in the **external-services**|
|                               | section.                           |
+-------------------------------+------------------------------------+
| **AML**                       | Refers to the Azure ML service     |
|                               | listed in the **external-services**|
|                               | section.                           |
+-------------------------------+------------------------------------+
| **Pool**                      | Refers to a set of named VMs       |
+-------------------------------+------------------------------------+
| **Local**                     | Using your local computer for      |
|                               | running the ML XT app              |
+-------------------------------+------------------------------------+

The syntax for a compute target is:

  .. code-block::

    name: {service: "servicename", prop: "value" }

Where 
    - **servicename** is the name of a service defined in the **external-services** section
    - **prop** and **value** represent configuration properties specific to each service type

Configuration properties by service type:

.. only:: not internal

    Batch:
        - **vm-size**: the Azure name that defines the virtual machine hardware to be used (e.g., Standard_NC6)
        - **azure-image**: the name of an image defined in the **azure-images** section (defines the OS to run on)
        - **nodes**: the number of machines to run on 
        - **low-pri**: if True. job should be run on a pre-emptible set of machines 
        - **box-class**: the name of an entry in the **script-launch-prefix** section, used to run scripts on the batch VMs
        - **docker**: the name of a docker environment (defined in the **dockers** section of this file) that will be used to run the job
    AML:       
        - **compute**: the name of a predefined Azure Compute object that should be used for running jobs (defines a configuration of VMs)
        - **vm-size**: the Azure name that defines the machine hardware to be used (e.g., Standard_NC6)
        - **nodes**: the number of machines to run on 
        - **low-pri**: if True. job should be run on a preemptible set of machines 
        - **docker**: the name of a docker environment (defined in the **dockers** section) that will be used to run the job
    pool:
        - **boxes** (a list of box names (defined in the **boxes** section) that will be used to run the job
        - **docker**: the name of a docker environment (defined in the **dockers** section of your local xt_config file) that will be used to run the job

.. only:: internal

    Batch:
        - **vm-size**: the Azure name that defines the virtual machine hardware to be used (e.g., Standard_NC6)
        - **azure-image**: the name of an image defined in the **azure-images** section (defines the OS to run on)
        - **nodes**: the number of machines to run on 
        - **low-pri**: if True. job should be run on a pre-emptible set of machines 
        - **box-class**: the name of an entry in the **script-launch-prefix** section, used to run scripts on the batch VMs
        - **docker**: the name of a docker environment (defined in the **dockers** section of this file) that will be used to run the job
    AML:       
        - **compute**: the name of a predefined Azure Compute object that should be used for running jobs (defines a configuration of VMs)
        - **vm-size**: the Azure name that defines the machine hardware to be used (e.g., Standard_NC6)
        - **nodes**: the number of machines to run on 
        - **low-pri**: if True. job should be run on a preemptible set of machines 
        - **docker**: the name of a docker environment (defined in the **dockers** section) that will be used to run the job
    Pool:
        - **boxes** (a list of box names (defined in the **boxes** section) that will be used to run the job
        - **docker**: the name of a docker environment (defined in the **dockers** section of your local xt_config file) that will be used to run the job
    Philly:
        - **cluster**: the name of the Philly cluster to run on
        - **vc**: the name of the Philly virtual cluster to run on
        - **sku**: the type of machine to run on (G1=single GPU, G4=4 GPUs, G8=8 GPUs, G16=16 GPUs)
        - **nodes**: the number of machines to run on 
        - **low-pri**: if True. job should be run on a preemptible set of machines 
        - **docker**: the name of a docker environment (defined in the **dockers** section) that will be used to run the job

Example: to specify an Azure Batch compute target:

.. code-block::

    compute-targets:
        batch: {service: "xtsandboxbatch", vm-size: "Standard_NC6", azure-image: "dsvm", nodes: 1, low-pri: true,  box-class: "dsvm", environment: "none"}

If you specify no **compute-targets** in your configuration, XT defaults to the local system. An example:

.. code-block::

    local: {service: "pool", boxes: ["localhost"], setup: "local"}

.. _xt_config_dockers:

****************************
Config File Section: Dockers
****************************

The **Dockers** section lets users define named Docker images environments, that can be used in compute target definitions.

 A Docker environment should be defined as follows:

  .. code-block::

    name: {registry: "registryservice", image: "imagename" }

Where:
    - **name** is the user-defined friendly name for the environment
    - **registryservice** is the name of a registry service defined in the **external-services** section
    - **imagename** is the name of a Docker image defined in the registry service.

Example: to specify a docker image that is registered in the **registry** service:

.. only:: not internal

  .. code-block::

    Dockers:
        pytorch-xtlib: {registry: "xtsandboxregistry", image: "pytorch-xtlib:latest"}
        pytorch-xtlib-local: {registry: "", image: "pytorch-xtlib:latest"}

.. only:: internal

  .. code-block::

    Dockers:
        pytorch-xtlib: {registry: "xtsandboxregistry", image: "pytorch-xtlib:latest"}
        pytorch-xtlib-local: {registry: "", image: "pytorch-xtlib:latest"}
        philly-pytorch: {registry: "philly-registry", image: "microsoft_pytorch:v1.2.0_gpu_cuda9.0_py36_release_gpuenv_hvd0.16.2"}

.. _xt_config_general:

*******************************
Config File Section: General
*******************************

The **general** section defines the set of general XT properties and their values. 

General properties include the following:

+-------------------------------+--------------------------------------------------+
| **Advanced-mode**             | Set to 'False' (Basic mode) by default. Set to   |
|                               | 'True' if you want to run XT in Advanced mode.   |
+-------------------------------+--------------------------------------------------+
| **Username**                  | Set to the variable "$username", which defaults  |
|                               | to the corporate login name of the user.         |
|                               | Used for logging for new runs/jobs.              |
+-------------------------------+--------------------------------------------------+
| **Workspace**                 | Specifies the name of the default XT workspace   |
|                               | to use for various XT commands.                  |
+-------------------------------+--------------------------------------------------+
| **Experiment**                | Specifies the name of the default XT experiment  |
|                               | to use for various XT commands.                  |
+-------------------------------+--------------------------------------------------+
| **Attach**                    | When True, the user's console is automatically   |
|                               | attached to the first run output when you submit |
|                               | a job using the "run" or "rerun" command.        |
+-------------------------------+--------------------------------------------------+
| **Feedback**                  | When True, user receives percentage feedback for |
|                               | upload and download commands.                    |
+-------------------------------+--------------------------------------------------+
| **Run-cache-dir**             | Specifies the local directory that XT will use to|
|                               | cache run information for certain commands.      |
+-------------------------------+--------------------------------------------------+
| **Direct-run**                | Normally, runs under XT are launched and         |
|                               | controlled by the XT controller app, running on  |
|                               | the same compute node (box) as the run.  When    |
|                               | you specify **direct-run**, the XT controller is |
|                               | not used, and the runs are launched and          |
|                               | controlled directly by the underlying service    |
|                               | controller. The **pool** service ignores this    | 
|                               | property, because it always uses the XT          |
|                               | controller.                                      |
+-------------------------------+--------------------------------------------------+
| **Quick-start**               | When True, the XT start-up time for each command |
|                               | is reduced.  This is an experimental property    |
|                               | that may eventually be removed.                  |
+-------------------------------+--------------------------------------------------+
| **Primary-metric**            | Set this property to the name of the primary     |
|                               | metric reported by your ML app. This metric is   |
|                               | used to guide hyperparameter searches and        |
|                               | early stopping algorithms.                       |
+-------------------------------+--------------------------------------------------+
| **Maximize-metric**           | when set to True, the **primary-metric** is      |
|                               | treated as a metric that the hyperparmeter search|
|                               | should maximize (e.g., accuracy). When set to    |
|                               | False, it is treated as a metric that should be  |
|                               | minimized (like loss).                           |
+-------------------------------+--------------------------------------------------+
| **conda-packages**            | A list of packages that should be installed by   |
|                               | **conda** on the target nodes (boxes). Some      |
|                               | services, like Azure ML, use this information to |
|                               | automatically build (or select a previously      |
|                               | built) docker image on behalf of the user.       |
+-------------------------------+--------------------------------------------------+
| **env-vars**                  | These are environment variable name/value pairs, |
|                               | in the form of a dictionary, that should be set  |
|                               | on the target node/box before the user's runs    |
|                               | begin executing.                                 |
+-------------------------------+--------------------------------------------------+

An example of a general section definition:

.. code-block::

    **General**:
        username: "$username"                  # use our Microsoft login
        workspace: "ws1"                       # create new runs in this workspace
        experiment: "exper1"                   # associate new runs with this experiment
        attach: false                          # do not auto-attach to runs
        feedback: true                         # show detailed feedback for upload/download
        run-cache-dir: "~/.xt/runs-cache"      # where we cache run information (SUMMARY and ALLRUNS)
        distributed: false                     # normal run
        direct-run: false                      # use the XT controller
        quick-start: false                     # don't use this feature
        primary-metric: "test-acc"             # the accuracy of our validation data
        maximize-metric: true                  # we want to maximize the test-acc
        conda-packages: []                     # no packages for conda to install

.. only:: not internal 

  .. code-block::

      env-vars: {"is_test_run": False}       # set the environment variable "is_test_run" to False before starting the run

.. _xt_config_code:

***************************
Config File Section: Code
***************************

The **code** section defines the set of XT properties that control the creation of code snapshots (collecting and copying the code from the local machine to the storage service as part of the run submission process).  

**Code** properties include the following:

    **code-dirs**
        A list of directories that define the source code used by the ML app. The first directory specified is considered the root of the code directory, and any other specified directories are copied to storage as children of the root directory. 
        
        You can use a special symbol (usually for the first directory), **$scriptdir**.  If found, it is replaced by the directory that contains the run script or app specfied by the **run** command.  For any specified directory, a wildcard name can be used as the last node of the directory. You can use the special wildcard **\*\*** to specify that the directory should be captured recursively (processing all subdirectories of all subdirectories).

    **code-upload**
        Normally set to True, meaning that the contents of the **code-dirs** should be captured and uploaded to the XT storage associated with the submitted job. If set to False, no code files will be captured/copied.  

    **code-zip**
        Specifies if the code files should be zipped before uploading, and if so, what type of compression should be used. Depending on your local machine computing speed, the number and size of your code files, and your upload speed, you can increase the speed of your code capture/upload process by trying different values for this property. Supported values are:
        
        - **none** (do not create a .zip file)
        - **fast** (create a .zip file, but don't compress the files);
        - **compress** (create a .zip file and compress the files added to it).

    **code-omit**
        A list of directory or file names, optionally containing wildcard characters. When capturing the code files, any files or directories matching names specified in **code-omit** will not be included.

    **xtlib-upload**
        When set to True, the source code files from XTLib (the XT package) will be included as a child directory of the root code directory. It allows the XT controller and your ML app to run against the same version of XTLib that you are using on your desktop. It is primarily designed as an internal feature for use by XT developers.

Here is an example of the **code** section:

.. code-block::

    code:
        xtlib-upload: true                 # upload XTLIB sources files for each run for use by controller and ML app
        code-zip: "compress"               # none/fast/compress ("fast" means zip w/o compression)
        code-omit: [".git", "__pycache__", "logs", "data"]      # directories and files to omit when capturing before/after files

.. _xt_config_after-files:

********************************
Config File Section: After Files
********************************

The **after-files** section defines the set of XT properties that control the uploading of run-related files after the run has completed.

The **after-files** properties include:

    **after-dirs**
        A list of directories that define the files to be captured and uploader after a run has completed. the directories are specified relative to the working directory of the run (which is set by the XT controller). Any directory can optionally include a wildcard name as its last node, to match files in the specified directory.  You can use the special wildcard **\*\*** to specify that the directory should be captured recursively (processing all subdirectories of all subdirectories).

    **after-upload**
        Normally set to True, meaning that the contents of the **after-files** should be captured and uploaded to the XT storage associated with the asociated run. If set to False, no files will be captured/copied.

An example of the **after-files** section:

.. code-block::

    after-files:
        after-dirs: ["*", "output/*"]         # specifies output files (for capture from compute node to STORE)
        after-upload: true                    # should after files be uploaded at end of run?
        after-omit: [".git", "__pycache__"]    # directories and files to omit when capturing after files

.. _config_file_data:

***************************
Config File Section: Data
***************************

The **data** section defines the set of XT properties controlling the actions XT takes on run-related data files.  These actions are:
    - uploading of data files to XT storage when a run is submitted
    - downloading data files to the compute node when a run is about to be started
    - mounting of a local drive to the data files in XT storage

**Data** properties include:

    **data-local**
        The directory on the local machine where the data can be found. It's used when the **data-upload** property is set to True.

    **data-upload**
        Normally set to False.  When set to True, the data file specified by the **data-local** directory will be uploaded to XT storage each time a job is submitted.

    **data-share-path**
        The directory path on the XT data share where the data files should reside.

    **data-action**
        The action that XT should take on the compute node before beginning the run. The property value must be one of the following: 
        
        - **none** (do nothing related to data files)
        - **download** (download the files from the **data-share-path**);
        - **mount** (mount the **data-share-path** to a local folder name). 
        
        If **download** or **mount** is specified, the ML app can retrieve the associated local folder by querying the value of the environment variable **XT_DATA_DIR**.

    **data-omit**
        A list of directory or file names, optionally containing wildcard characters. When capturing and uploading data files, files or directories matching any names in **data-omit** will not be included.

    **data-writable**
        When set to True and when **data-action** is set to **mount**, the mounted directory will be writable (files can be added or updated).

An example of the **data** section:

.. code-block::

    data:
        data-local: ""                         # local directory of data for app
        data-upload: false                     # should data automatically be uploaded
        data-share-path: ""                    # path in data share for current app's data
        data-action: "none"                    # data action at start of run: none, download, mount
        data-omit: []                          # directories and files to omit when capturing before/after files
        data-writable: false                   # when true, mounted data is writable
        
.. _config_file_model:

***************************
Config File Section: Model
***************************

The **model** section defines the set of XT properties that control the actions taken by XT related to the run-related model files. 

These actions are:
    - downloading model files to the compute node when a run is about to be started
    - mounting of a local drive to the model files in XT storage

The **model** properties include:

    **model-share-path**
        The directory path on the XT model share where the model files should reside.

    **model-action**
        Specifies the action that XT should take on the compute node before beginning the run. The property must be one of the following:

        - **none** (do nothing related to model files);
        - **download** (download the files from the **model-share-path**);
        - **mount** (mount the **model-share-path** to a local folder name).

    .. note::

        if **download** or **mount** is specified, the ML app can retreive the associated local folder by querying the value of the environment variable **XT_MODEL_DIR**.

    **model-writable**
        When set to True and when **model-action** is set to **mount**, the mounted directory will be writable (files can be added or updated).

An example of the **model** section:

.. code-block::

    model:
        model-share-path: ""                   # path in model share for current app's model
        model-action: "none"                   # model action at start of run: none, download, mount
        model-writable: false                  # when true, mounted model is writable

.. _xt_config_logging_sec:

*****************************
Config File Section: Logging
*****************************

The **logging** section controls the logging of run-related events and the mirroring of run-related files to XT storage.  Note that the implementation of the XT **view tensorboard** command  depends on mirroring of the Tensorboard log files.

The **logging** properties include the following:

    **log**
        The normal value is True, which means experiment run events are logged to XT storage.  when set to False, these events are not logged.

    **notes**
        Controls if and when a user is prompted for a description of the job being submitted. The property must be one of the following: 

        - **none** (no prompting is done);
        - **before** (user is prompted at the beginning of the submission);
        - **after** (user is prompted at the end of the submission).

    **mirror-files**
        A list of directories that define the files that should be tracked and uploaded to XT storage associated with the run. The directories are specified relative to the working directory of the run (which is set by the XT controller). Any directory can optionally include a wildcard name as its last node, to match files in the specified directory. You can use the special wildcard **\*\* to specify that the directory should be captured recursively (processing all subdirectories of all subdirectories).  One of the uses for mirroring run files is the support of XT **view tensorboard** command.

    **mirror-dest**
        Controls if files are mirrored and if so, where they are copied to. The property must be one of the following: 
    
        - **none** (no file watching or mirroring is done);
        - **storage** (files specified by **mirror-files** are watched and copied to the XT storage associated with the run).

An example of the **logging** section:

.. code-block::

    logging:
        log: true                              # specifies if experiments are logged to STORE
        notes: "none"                          # control when user is prompted for notes (none, before, after, all)
        mirror-files: "logs/**"                # default wildcard path for log files to mirror
        mirror-dest: "storage"                 # one of: none, storage

.. _xt_config_internal_sec:

*****************************
Config File Section: Internal
*****************************

The **internal** section controls operations in XT designed for internal XT developers, but may also be of value to other XT users.

**Internal** properties include the following:

    **console**
        Controls the XT console output. The property must be one of the following:

        - **none** (suppresses all XT output);
        - **normal** (high level command progress and results show on the console);
        - **diagnostics** (command timing and high level trace information show on the console);
        - **detail** (command timing and detailed trace information show on the console).
          
    **stack-trace**
        When set to True and exceptions are raised, the associated stack traces appear on the console. When set to False, the stack traces are omitted.

    **auto-start**
        When set to True, the XT controller is automatically started for "view status" commands (mainly for use when running on the local machine or on a specified pool of boxes). The default is that the XT controller continues to run after the submitted job is completed.

An example of the **internal** section:

.. code-block::

    internal:
        console: "normal"                      # controls the level of console output (none, normal, diagnostics, detail)
        stack-trace: false                     # show stack trace for errors  
        auto-start: false                      # when true, the controller is automatically started on 'status' cmd

.. _xt_config_aml_options:

********************************
Config File Section: AML Options
********************************

The **aml-options** section contains properties specific to the Azure ML service, including GPU capabilities. These properties are:

    **use-gpu**
        If set to True and a GPU exists, it will be made available to your app.  If False, no GPU will be made available.  

    **use-docker**
        If set to True, XT defines a docker image based on the specified **framework**, **conda-packages**, and **pip-packages**. If an matching image already exists, that will be used for the run. Otherwise, a custom docker image will be built and used. the image will then be saved by Azure ML for subsequent runs.

    **framework**
        The base framework that will be used for the run. Supported values are: **pytorch**, **tensorflow**, **chainer**, and **estimator**.

    **fw-version**
        Specifies the version string of the **framework** to be used.

    **user-managed**
        If set to True, Azure ML assumes the environment has already been correctly configured by the user.  This property should be set to False for normal runs.

    **distributed-training**
        Specifies the name of the distributed backend to use for distributed training. The value must be one of the following: **mpi**, **gloo**, or **nccl**.

    **max-seconds**
        Specifies the time limit for the ML run. If the running time exceeds this limit, a timeout error will occur.

.. note::

        Set the max-seconds property to -1 to specify the maximized run time.

An example of the **aml-options** section:

.. code-block::

    aml-options:
        use-gpu: true                          # use GPU(s) 
        use-docker: true                       # by default, build a docker image for pip/conda dependencies (faster startup, once built)
        framework: "pytorch"                   # currently, we support pytorch, tensorflow, or chainer
        fw-version: "1.2"                      # version of framework (string)
        user-managed: false                    # when true, AML assumes we have correct prepared environment (for local runs)
        distributed-training: "mpi"            # one of: mpi, gloo, or nccl
        max-seconds: -1                        # max secs for run before timeout (-1 for none)

.. _xt_config_early_stop:

***********************************
Config File Section: Early Stopping
***********************************

The **early-stopping** section specifies properties that are used by the Azure ML early stopping algorithms (currently only available when running on an AML service). Early stopping algorithms look at the training progress and status of an ML app and decide if the training should be stopped before it reaches the specified number of steps or epochs.

The properties in the **early-stopping** section include:

    **early-policy**
        Specifies the early stopping algorithm hat Azure ML will use. The value must be one of the following: 

        - **none** (AML does no early stopping);
        - **bandit** (use the AML Bandit ES algorithm);
        - **median** (use the AML Median ES algorithm);
        - **truncation** (use the AML Truncation ES algorithm).

    **delay-evaluation**
        The # of metric reportings to wait before the first application of the early stopping policy.

    **evaluation-interval**
        The frequency (# of metric reportings) to wait before reapplying the early stopping policy.

    **slack-factor**
        *For the Bandit ES only*: specified as a ratio, the delta between the current evaluation and the best performing evaluation.
          
    **stack-amount**
        *For the Bandit ES only*: specified as an amount, the delta between the current evaluation and the best performing evaluation.

    **truncation-percentage**
        *For the Truncation ES only*: percentage of runs to cancel after each early stopping evaluation

An example of the **early-stopping** section:

.. code-block::

    early-stopping:
        early-policy: "none"           # bandit, median, truncation, none
        delay-evaluation: 10           # number of evals (metric loggings) to delay before the first policy application
        evaluation-interval: 1         # the frequency (# of metric logs) for testing the policy
        slack-factor: 0                # (bandit only) specified as a ratio, the delta between this eval and the best performing eval
        slack-amount: 0                # (bandit only) specified as an amount, the delta between this eval and the best performing eval
        truncation-percentage: 5       # (truncation only) percent of runs to cancel at each eval interval

.. _xt_config_hps_sec:

*********************************************
Config File Section: Hyperparameter Search
*********************************************

The **hyperparameter-search** section controls how XT uses hyperparameter searching.  

In XT, hyperparameter searching starts from a set of named hyperparameters and their associated value distributions. These are normally specified in a hyperparameter config file (.txt), or they can be specified in the run command, as special arguments to your ML app. Before each search run starts, the values for each hyperparameter are sampled from their distributes, according to the hyperparameter search algorithm being used. Once a set of values for the hyperparameters is determined, the values can be passed to the ML app through an *app config file* (.txt), or by passing command line arguments to the ML app.

The **hyperparameter-search** section properties are:

    **option-prefix**
        If this value is an empty string or the value "none", command line arguments are not generated for each search run. Otherwise, the value of **option-prefix** is used in front of each hyperparameter name to form command line arguments to the ML app. 
        
        For example, if **option-prefix** is set to "--", and the hyperparameter **lr** is being set to .05 by the hyperparameter search algorithm, then the command argument "--lr=.05" would be passed to your ML app on its command line when it is run.

    **aggregate-dest**
        This is where XT aggregates results for the hyperparameter search. This aggregation enables faster access to the log files for the runs in the search. The value of this property must be one of the following: 

        - **none** (no aggregation is done)
        - **job** (results are aggregated to the storage area associated with the job)
        - **experiment** (results are aggregated to the storage area associated with the experiment).

    **search-type**
        Specifies the type of search algorithm. The value of this property must be one of the following: 

        - **none** (for no searching);
        - **grid** (for a exhaustive rollout of all combinations of discrete hyperparameter values);
        - **random** (for random sampling of the hyperparameter values)
        - **bayesian** (for a search guided by bayesian learning)
        - **dgd** (the distributed grid descent algorithm, a search guided by nearest neighbors of best searches).

    **max-minutes**
        Specifies the maximum time in minutes for a hyperparameter search run.  If set to -1, no maximum time is enforced. Currently only supported for Azure ML service.

    **max-concurrent-runs**
        Specifies the maximum concurrent runs over all nodes. The setting is currently only supported for Azure ML service.

    **hp-config**
        Defines is the name of the file containing the hyperparameters and their associated values or value distributions.

    **fn-generated-config**
        The name of the app config file to be generated in the run directory before each run. The ML app uses the file to load its hyperparameter values for the current run. If set to an empty string, no file will be generated.

An example of a **hyperparameter-search** section:

.. code-block::

    hyperparameter-search:
        option-prefix: "--"            # prefix for hp search generated cmdline args (set to None to disable cmd args from HP's)
        aggregate-dest: "job"          # set to "job", "experiment", or "none"
        search-type: "random"          # random, grid, bayesian, or dgd
        max-minutes: -1                # -1=no maximum
        max-concurrent-runs: 100       # max concurrent runs over all nodes
        hp-config: ""                  # the name of the text file containing the hyperparameter ranges to be searched
        fn-generated-config: "config.txt"  # name of HP search generated config file

.. _xt_config_hpe_sec:

*********************************************
Config File Section: Hyperparameter Explorer
*********************************************

The **hyperparameter-explorer** section specifies hyperparameter and metric names, and other properties used by the Hyperparameter Explorer (HX). HX is a GUI interface for exploring the effect of different hyperparameter settings on the performance of your ML trained model.

The properties for the **hyperparameter-explorer** section are:

+-------------------------------+--------------------------------------------------+
| **hx-cache-dir**              | The name of a directory that HX uses to download |
|                               | all of the run logs for an experiment or job.    |
+-------------------------------+--------------------------------------------------+
| **steps-name**                | The name of the hyperparameter that your ML app  |
|                               | uses to specify the total number of training     |
|                               | steps.                                           |
+-------------------------------+--------------------------------------------------+
| **log-interval-name**         | The name of the hyperparameter that your ML app  |
|                               | uses to set the number of steps between          |
|                               | logging metrics.                                 |
+-------------------------------+--------------------------------------------------+
| **step-name**                 | The name of the metric your ML app uses to       |
|                               | represent the number of training steps processed |
|                               | to-date.                                         |
+-------------------------------+--------------------------------------------------+
| **time-name**                 | The name of the metric your ML app uses to       |
|                               | represent the elapsed time of training.          |
+-------------------------------+--------------------------------------------------+
| **sample-efficiency-name**    | The name of the metric your ML app uses to       |
|                               | represent the sample efficiency of the training. |
+-------------------------------+--------------------------------------------------+
| **success-rate-name**         | The name of the metric your ML app uses to       |
|                               | represent the success rate of training to-date.  |
+-------------------------------+--------------------------------------------------+

An example of a **hyperparameter-explorer** section:

.. code-block::

    hyperparameter-explorer:
        hx-cache-dir: "~/.xt/hx_cache"     # directory hx uses for caching experiment runs 
        steps-name: "steps"                # usually "epochs" or "steps" (hyperparameter - total # of steps to be run)
        log-interval-name: "LOG_INTERVAL"  # name of hyperparameter that specifies how often to log metrics
        step-name: "step"                  # usually "epoch" or "step" (metrics - current step of training/testing)
        time-name: "sec"                   # usually "epoch" or "sec
        sample-efficiency-name: "SE"       # sample efficiency name 
        success-rate-name: "RSR"           # success rate name 

.. _xt_config_rr_sec:

*********************************
Config File Section: Run Reports
*********************************

The **run-reports** section controls how the **list runs** command formats its reports. The primary control revolves around the run columns, drawn from:

    - Standard run properties (such as **target** or **status**);
    - ML app logged hyperparameters (name must be prefixed by "hparams.");
    - ML app logged metrics (name must be prefixed by "metrics.");
    - User assigned run tags (name must be prefixed by "tags.");

The properties of the **run-reports** section are:

+-------------------------------+--------------------------------------------------+
| **sort**                      | Specifies the run column used for sorting the    |
|                               | runs. If not used, defaults to "run".            |
+-------------------------------+--------------------------------------------------+
| **reverse**                   | If set to True, XT performs a reverse sort (runs |
|                               | are arranged in descending order of their sort   |
|                               | column).                                         |
+-------------------------------+--------------------------------------------------+
| **max-width**                 | The maximum width of a column in the report (in  |
|                               | text characters)                                 |
+-------------------------------+--------------------------------------------------+
| **uppercase-hdr**             | If True, the header names on the top and bottom  |
|                               | of the report are uppercased.                    |
+-------------------------------+--------------------------------------------------+
| **right-align-numeric**       | If True, number values are right-aligned in their|
|                               | columns.                                         |
+-------------------------------+--------------------------------------------------+
| **truncate-with-ellipses**    | If True, column values that exceed the maximum   |
|                               | column width are truncated with ellipses.        |
+-------------------------------+--------------------------------------------------+
| **status**                    | If specified, this value is used to match records|
|                               | by their status value (filters out non-matching|||
|                               | records).                                        |
+-------------------------------+--------------------------------------------------+
| **record-rollup**             | If true, the reporting record with the best      |
|                               | primary metric selects the metrics to display.   |
|                               | If False, the last reported set of metric will   |
|                               | be displayed.                                    |
+-------------------------------+--------------------------------------------------+
| **columns**                   | A list of column specifications to define        |
|                               | the columns and their formatting for the report. |
|                               | A column specification can be as simple as the   |
|                               | name of a column, but it can also include some   |
|                               | customization.  See `Columns in XT <columns>`    |
|                               | topic for more information.                      |
+-------------------------------+--------------------------------------------------+

An example of the **run-reports** section:

.. code-block::

    run-reports:
        sort: "name"                   # default column sort for experiment list (name, value, status, duration)
        reverse: false                 # if experiment sort should be reversed in order    
        max-width: 30                  # max width of any column
        uppercase-hdr: true            # show column names in uppercase letters
        right-align-numeric: true      # right align columns that contain int/float values
        truncate-with-ellipses: true   # if true, "..." added at end of truncated column headers/values
        status: ""                     # the status values to match for 'list runs' cmd
        report-rollup: false           # if primary metric is used to select run metrics to report (vs. last set of metrics)

        columns: ["run", "created:$do", "experiment", "queued", "job", "target", "repeat", "search", "status", 
            "tags.priority", "tags.description",
            "hparams.lr", "hparams.momentum", "hparams.optimizer", "hparams.steps", "hparams.epochs",
            "metrics.step", "metrics.epoch", "metrics.train-loss", "metrics.train-acc", 
            "metrics.dev-loss", "metrics.dev-acc", "metrics.dev-em", "metrics.dev-f1", "metrics.test-loss", "metrics.test-acc", 
            "duration", 
            ]

.. _xt_config_jr_sec:

********************************
Config File Section: Job Reports
********************************

The **job-reports** section controls how the **list jobs** command formats its reports. The primary control revolves around the job columns, drawn from:

    - Standard job properties (like **target** or **created**)
    - User assigned job tags (name must be prefixed by "tags.")

The properties of the **job-reports** section are:

+-------------------------------+--------------------------------------------------+
| **sort**                      | Specifies the run column used for sorting the    |
|                               | runs. If not used, defaults to "run".            |
+-------------------------------+--------------------------------------------------+
| **reverse**                   | If set to True, XT performs a reverse sort (runs |
|                               | are arranged in descending order of their sort   |
|                               | column).                                         |
+-------------------------------+--------------------------------------------------+
| **max-width**                 | The maximum width of a column in the report (in  |
|                               | text characters)                                 |
+-------------------------------+--------------------------------------------------+
| **uppercase-hdr**             | If True, the header names on the top and bottom  |
|                               | of the report are uppercased.                    |
+-------------------------------+--------------------------------------------------+
| **right-align-numeric**       | If True, number values are right-aligned in their|
|                               | columns.                                         |
+-------------------------------+--------------------------------------------------+
| **truncate-with-ellipses**    | If True, column values that exceed the maximum   |
|                               | column width are truncated with ellipses.        |
+-------------------------------+--------------------------------------------------+
| **columns**                   | A list of column specifications to define        |
|                               | the columns and their formatting for the report. |
|                               | A column specification can be as simple as the   |
|                               | name of a column, but it can also include some   |
|                               | customization.  See `Columns in XT <columns>`    |
|                               | topic for more information.                      |
+-------------------------------+--------------------------------------------------+

An example of the **job-reports** section::

    job-reports:
        sort: "name"                   # default column sort for experiment list (name, value, status, duration)
        reverse: false                 # if experiment sort should be reversed in order    
        max-width: 30                  # max width of any column
        uppercase-hdr  : true          # show column names in uppercase letters
        right-align-numeric: true      # right align columns that contain int/float values
        truncate-with-ellipses: true   # if true, "..." added at end of truncated column headers/values

        columns: ["job", "created", "started", "workspace", "experiment", "target", "nodes", "repeat", "tags.description", "tags.urgent", "tags.sad=SADD", "tags.funny", "low_pri", 
            "vm_size", "azure_image", "service", "vc", "cluster", "queue", "service_type", "search", 
            "job_status:$bz", "running_nodes:$bz", "running_runs:$bz", "error_runs:$bz", "completed_runs:$bz"]

.. _xt_config_tensorboard:

*********************************
Config File Section: Tensorboard
*********************************

The **tensorboard** section controls how the **view tensorboard** command operates in XT. The properties
for the **tensorboard** section include the following:

    **template**
        The **template** property is a string that specifies how to name the Tensorboard log files from multiple runs.  It can include run column names (standard, hparams.*, metrics.*, tags.*) in curly braces along with normal characters outside thoses braces, to build up log file names that enable easier filtering of runs within Tensorboard.

A sample **tensorboard** section::

    tensorboard::
        template: "{workspace}_{run_name}_{logdir}"

.. _xt_config_sl_prefix_sec:

*****************************************
Config File Section: Script Launch Prefix
*****************************************

The **script-launch-prefix** section specifies the shell command and arguments to run XT-generated scripts on compute nodes. The nodes are specified by their **box-class** property associated with each compute node.

The general format for a property of the **script-launch-prefix** section is::

    boxclass: commandstring

.. only:: internal

    where:
        - **boxclass** is the class of the box (specified as a compute target property, a box property, or hardcoded as **linux**, **aml** or **philly** services)

        - **commandstring** is a shell command and optional arguments used to run the scripts.  An example of a **commandstring** would be "bash --login" for linux systems.

.. only:: not internal

    where:
        - **boxclass** is the class of the box (specified as a compute target property, a box property, or hardcoded as **linux** or **aml** services)

        - **commandstring** is a shell command and optional arguments used to run the scripts.  An example of a **commandstring** would be "bash --login" for linux systems.

An example of a **script-launch-prefix** section:

.. only:: not internal

  .. code-block:: none

    script-launch-prefix:
        # list cmds used to launch scripts (controller, run, parent), by box-class
        windows: ""
        linux: "bash --login"
        dsvm: "bash --login"
        azureml: "bash"

.. only:: internal

  .. code-block:: none

    script-launch-prefix:
        # list cmds used to launch scripts (controller, run, parent), by box-class
        windows: ""
        linux: "bash --login"
        dsvm: "bash --login"
        azureml: "bash"
        philly: "bash --login"  

.. _xt_config_batch_img_sec:

***************************************
Config File Section: Azure Batch Images
***************************************

The **azure-batch-images** section defines OS images for defining **batch** type compute targets. The general format for an entry in this xt_config section is::

    imagename: {offer: "offername", publisher: "publishername", sku: "skuname", node-agent-sku-id: "skuid", version: "versionname"}

Azure Batch Images properties include:

+-------------------------------+--------------------------------------------------+
| **imagename**                 | A user-defined name for the image.               |
+-------------------------------+--------------------------------------------------+
| offer: **offername**          | The Offer type of the Azure Virtual Machines     |
|                               | Marketplace Image. For example, UbuntuServer     |
|                               | or WindowsServer.                                |
+-------------------------------+--------------------------------------------------+
| publisher: **publishername**  | The publisher of the Azure Virtual Machines      |
|                               | Marketplace Image. For example, Canonical        |
|                               | or MicrosoftWindowsServer.                       |
+-------------------------------+--------------------------------------------------+
| sku: **skuname**              | The SKU of the Azure Virtual Machines Marketplace|
|                               | Image. For example, 18.04-LTS or 2019-Datacenter.|
+-------------------------------+--------------------------------------------------+
| node-agent-sku-id: **skuid**  | The SKU of the Batch Compute Node agent to       |
|                               | provision on Compute Nodes in the Pool.          |
+-------------------------------+--------------------------------------------------+
| version: **versionname**      | The version of the Azure Virtual Machines        |
|                               | Marketplace Image. Specify a value of 'latest'   |
|                               | to select the latest version of an Image.        |
+-------------------------------+--------------------------------------------------+
    
More info about these properties is available in the `Azure Batch docs <https://docs.microsoft.com/en-us/python/api/azure-batch/azure.batch.models.imagereference?view=azure-python>`_, and also `here <https://docs.microsoft.com/en-us/python/api/azure-batch/azure.batch.models.virtualmachineconfiguration?view=azure-python>`_.

An example of an **azure-batch-images** section::

    azure-batch-images:
        # these are OS images that you can use with your azure batch compute targets (see [compute-targets] section above)
        dsvm: {offer: "linux-data-science-vm-ubuntu", publisher: "microsoft-dsvm", sku: "linuxdsvmubuntu", node-agent-sku-id: "batch.node.ubuntu 16.04", version: "latest"}
        ubuntu18: {publisher: "Canonical", offer: "UbuntuServer", sku: "18.04-LTS", node-agent-sku-id: "batch.node.ubuntu 18.04", version: "latest"}

***************************
Config File Section: Boxes
***************************

The **boxes** section defines a list of remote computers or Azure VMs that can be used as compute targets with XT.  The named boxes can also be used directly by name in various XT utility commands.  

Requirements: each defined box needs to have ports 22 and port 18861 open for incoming messages, for configuration the box, and for communicating with the XT controller.

The general format for a box is:

    **boxname**: {address: **boxaddress**, os: **osname**, box-class: **boxclassname**, max-runs: **maxrunsvalue**, actions: **actionlist**}
    
Boxes section properties include:

+-------------------------------+--------------------------------------------------+
| **boxname**                   | A user-defined name for the box.                 |
+-------------------------------+--------------------------------------------------+
| address: **boxaddress**       | The Offer type of the Azure Virtual Machines     |
|                               | Marketplace Image. For example, UbuntuServer     |
|                               | or WindowsServer.                                |
+-------------------------------+--------------------------------------------------+
| os: **osname**                | One of: **linux** or **windows**, representing   |
|                               | the OS the box is running on.                    |
+-------------------------------+--------------------------------------------------+
| Boxclass: **boxclassname**    | The user-defined name of a box-class, used in the|
|                               | **script-launch-prefixes** section.  This name   |
|                               | is used to establish the script prefix to use    |
|                               | when running scripts on the box.                 |
+-------------------------------+--------------------------------------------------+
| max-runs: **maxrunsvalue**    | Maximum number of simultaneous XT runs allowed on|
|                               | the box. The XT controller uses this value to    |
|                               | schedule runs on the box.                        |
+-------------------------------+--------------------------------------------------+
| actions: **actionlist**       | A list of actions (one of: **data**,  **model**) |
|                               | that XT will perform on the box, according to the|
|                               | properties of the **data** and **model** sections|
|                               | defined in the config file.                      |
+-------------------------------+--------------------------------------------------+

An example of a **boxes** section::

    boxes:
        local: {address: "localhost", os: "windows", box-class: "windows", max-runs: 1, actions: []}
        vm1: {address: "$username@52.170.38.14", os: "linux", box-class: "linux", max-runs: 1, actions: []}
        vm10: {address: "$username@52.224.239.149", os: "linux", box-class: "linux", max-runs: 1, actions: []}

.. _xt_config_providers_sec:

*******************************
Config File Section: Providers
*******************************

The **providers** section defines the set of code providers active in XT, listed by their provider type.  

The current provider types in XT are:
    - command       (defines the set of commands available in XT)
    - compute       (defines the set of backend compute services available in XT)
    - hp-search     (defines the set of hyperparameter search algorithms available in XT)
    - storage       (defines the set of storage providers available in XT)

For each provider type, you specify a dictionary of name/value pairs.  
    - The *name* is a user-defined name that may appear elsewhere in the XT config file or command line options.  
    - The *value* is a provider **code path**.

An example of a **providers** section:

.. only:: not internal

  .. code-block:: none

    providers:
        command: {
            "compute": "xtlib.impl_compute.ImplCompute", 
            "storage": "xtlib.impl_storage.ImplStorage", 
            "help": "xtlib.impl_help.ImplHelp", 
            "utility": "xtlib.impl_utilities.ImplUtilities"
        }

        compute: {
            "pool": "xtlib.backend_pool.PoolBackend", 
            "batch": "xtlib.backend_batch.AzureBatch",
            "aml": "xtlib.backend_aml.AzureML"
        }

        hp-search: {
            "dgd": "xtlib.search_dgd.DGDSearch",
            "bayesian": "xtlib.search_bayesian.BayesianSearch",
            "random": "xtlib.search_random.RandomSearch"
        }

        storage: {
            "azure-blob-21": "xtlib.store_azure_blob21.AzureBlobStore21",
            "azure-blob-210": "xtlib.store_azure_blob210.AzureBlobStore210",
            "store-file": "xtlib.store_file.FileStore",
        }

.. only:: internal

  .. code-block:: none

    providers:
        command: {
            "compute": "xtlib.impl_compute.ImplCompute", 
            "storage": "xtlib.impl_storage.ImplStorage", 
            "help": "xtlib.impl_help.ImplHelp", 
            "utility": "xtlib.impl_utilities.ImplUtilities"
        }

        compute: {
            "pool": "xtlib.backend_pool.PoolBackend", 
            "batch": "xtlib.backend_batch.AzureBatch",
            "philly": "xtlib.backend_philly.Philly",
            "aml": "xtlib.backend_aml.AzureML"
        }

        hp-search: {
            "dgd": "xtlib.search_dgd.DGDSearch",
            "bayesian": "xtlib.search_bayesian.BayesianSearch",
            "random": "xtlib.search_random.RandomSearch"
        }

        storage: {
            "azure-blob-21": "xtlib.store_azure_blob21.AzureBlobStore21",
            "azure-blob-210": "xtlib.store_azure_blob210.AzureBlobStore210",
            "store-file": "xtlib.store_file.FileStore",
        }

.. seealso:: 

    - :ref:`xt config command <config>` 
    - :ref:`Defining Code Changes for your XT Installation <prepare_new_project>` 
    - :ref:`Hyperparameter Searching in XT <hyperparameter_search>` 
    - :ref:`Extensibility in XT <extensibility>` 

