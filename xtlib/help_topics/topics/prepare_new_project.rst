.. _prepare_new_project:

========================================
Integrating XT Into your Training Code
========================================

This page describes how to finish setting up your XT project for machine learning (ML) experiments. We discuss using the XTlib library to add support for logging metrics and hyperparameters, and other monitoring capabilities for maintaining and managing your projects.

You should already have configured XT for a set of cloud services (storage, compute, etc.), done either by you or your team adminstrator. If this step hasn't been done yet, refer to :ref:`Creating Azure Cloud Services for XT <creating_xt_services>` and :ref:`Understanding the XT Config file <xt_config_file>` for more information.

Preparing a new project for XT consists of 3 overall steps:
    - Defining Code Changes in your XT Installation. Consists of adding code to your ML app for XT logging, checkpointing, and data/model loading;
    - Uploading your dataset and model to your shared cloud storage for XT;
    - Creating a new local XT config file for your project and deciding on a number of key settings therein.

Each of these steps involves a number of important data points to consider when you are preparing your XT machine learning project.

----------------------------------------------
Defining Code Changes for your XT Installation
----------------------------------------------

The following subsections starting with "Code:" in the title describe code changes to consider making for your ML experiment. 

You can run your ML scripts under XT without changing any of the code, but by adding a small set of code statements, you can realize several benefits:

    - uniform access to local and cloud-resident datasets and models 
    - easy model checkpointing
    - centralized logging for hyperparameters and metrics 
    - hyperparameter searches
    - run and job reports that reflect your project's hyperparameters and metrics
    - ad-hoc plots with your project's metrics

**************************************
Code: Creating an XT Run Object
**************************************

The first step is to create an XT Run object.  Using an XT Run object, your ML app can log hyperparameter settings, train and test metrics, and upload or download needed files.  The recommended statement for creating an XT
run object is::

    from xtlib.run import Run
    xt_run = Run(tb_path="logs")

It creates a Run instance enabled for XT and Tensorboard logging.  To do your own Tensorboard logging, omit the **tb_path** argument.

**************************************
Code: Hyperparameter Logging 
**************************************

.. note:: If your ML app is not doing training, you can skip hyperparameter logging.

To log the value of your hyperparameters, you can pass a dictionary of hyperparameter names and their values. If you use command line arguments for your hyperparameters and parse them with the **argsparse** library, we recommend the following statement::

        # log hyperparameters to XT
        if xt_run:
            xt_run.log_hparams( argv.__dict__ )

If you don't already have a hyperparameter dictionary, use a code block like the following, using your app's hyperparameter names and values::

        # log hyperparameters to XT
        if xt_run:
            hp_dict = {"seed": seed, "batch-size": batch_size, "epochs": epochs, "lr": lr, 
                "momentum": momentum, "channels1": channels1, "channels2": channels2, "kernel_size": kernel_size, 
                    "mlp-units": mlp_units, "weight-decay": weight_decay, "optimizer": optimizer, 
                    "mid-conv": mid_conv, "gpu": gpu, "log-interval": log_interval}

            xt_run.log_hparams(hp_dict)

Place your hyperparameter logging statement after the creation of the xt_run object, but before your ML app starts its training operation. 

************************
Code: Metrics Logging
************************

For metrics logging during training, use the following code statement. You'll need to edit it to reflect your app's actual metric names and values ("epoch", "loss", and so on)::

        if xt_run:
            # log TRAINING stats to XT
            xt_run.log_metrics({"epoch": epoch, "loss": train_loss, "acc": train_acc}, step_name="epoch", stage="train")

In the above, if you use **step** or another name for each interval of training,  replace the 3 instances of "epoch" with your interval name.  

An example of logging metrics during evaluation::

        if xt_run:
            # log EVAL stats to XT
            xt_run.log_metrics({"epoch": epoch, "loss": eval_loss, "acc": eval_acc}, step_name="epoch", stage="eval")

You'll also need to edit this for your app.

.. note:: Since these logging calls access the cloud database, limit the logging frequency to once every 30 seconds or longer.  

************************
Code: XT_DATA_DIR
************************

When your job begins its run on a compute node, XT can optionally map a local path to the cloud data share path of your project's dataset. It can also download your dataset to a local path. The **data** section of your XT config file controls both actions.  

To enable your ML app to access mapped or downloaded data, XT sets the environment variable **XT_DATA_DIR** to the local data path. Use the following code statement to get the path to your dataset::

    data_dir = os.getenv("XT_DATA_DIR", args.data)

The above statement will use the **XT_DATA_DIR** as the data directory if XT has set it, otherwise, it will use the parsed command line argument for **data** (in this example). Edit **args.data** above to be the location of your dataset on your local machine, as needed.

************************
Code: XT_MODEL_DIR
************************

.. note:: This section applies to the use case where you want to upload a model to a model share (cloud storage) and then direct your ML app to use that model (for evaluation or model analysis, for example).  For checkpointing model loading, refer to the **Code: Checkpointing** section below.

When your job starts to run on a compute node, XT can map a local path to the model share path of your project's model file(s). It can also download your model to a local path. The **model** section of your XT config file controls both actions.  

To enable your ML app to access the mapped model or the downloaded model, XT sets the environment variable **XT_MODEL_DIR** to the local path of the model.  We recommend the following code statement to get the path to your model::

    model_dir = os.getenv("XT_MODEL_DIR", args.model)

The above statement uses **XT_MODEL_DIR** as the model directory if XT has set it. Otherwise, it uses the parsed command line argument for **model**.  Change **args.model** above to the location of the model on your local machine, as needed.

************************
Code: XT_OUTPUT_DIR
************************

When your job starts to run on a compute node (backend service or a Linux VM), XT will map your run's storage location in the cloud to a local path and set the environment variable **XT_OUTPUT_DIR** to that value. You can use this path to write your output logs and anything else you would like to be written to the cloud before your run completes. 

.. note:: A separate mechanism applies for capturing selected files when your job completes (the **after-files** section of the XT config file controls this).

The recommended statement for getting the **XT_OUTPUT_DIR** value is::

    output_dir = os.getenv("XT_OUTPUT_DIR", "output")

The above statement uses **XT_OUTPUT_DIR** as the output directory if XT has set it, otherwise, it uses the directory **output** (in this example). Change **output** above to be the location on your local machine that you use for output files, as needed.

If you are doing your own Tensorboard logging to the **XT_OUTPUT_DIR**, you will need an additional code statement to have it work as expected. See :ref:`Using Tensorboard with XT <tensorboard>`  for more details.

************************
Code: Checkpointing
************************

Checkpointing your model is an ML best practice, and a must if you are running on preemptable nodes, where your job can get interrupted and restarted at any time.

To check for the existence of a model at the beginning of your run, use your output directory from **XT_OUTPUT_DIR**. If it's found, you can safely assume your run has been restarted and load the model to continue your training. 

Recommended statement to load a PyTorch model from your output directory::

    fn_model = os.path.join(output_dir, "model.pt")
    if os.path.exists(fn_model):
        model.load_state_dict(torch.load(fn_checkpoint))

Make sure to periodically save your model to your output directory (for example, every 30 minutes), so that you have a recent model to restart from.

Recommended statement to save a PyTorch model to your output directory::

    fn_model = os.path.join(output_dir, "model.pt")
    torch.save(model.state_dict(), fn_model)

************************
Code: Run Script
************************

You normally specify your run's environment and its dataset dependencies in :ref:`Understanding the XT Config file <xt_config_file>`. You can specify your app's main python script when you invoke the **xt run** command.

Instead, you can specify a Shell script (or Windows .bat file) when you invoke **xt run**. Doing so, you can run any code needed to initialize the compute node for your app (generate datasets, installing dependencies, etc). You can also do custom post-processing after your python script completes.

A shell script example::

    conda activate py37_torch
    pip install -r requirements.txt
    python myscript.py  --epochs=125  --lr=.02

.. note:: Using a run script is optional; :ref:`Understanding the XT Config file <xt_config_file>` provides settings to handle pre- and post- dependencies for most jobs.

---------------------------------------
Uploading Data Files to Cloud Storage
---------------------------------------

Subsections in this category of actions describe data files to consider uploading to your XT cloud storage or other data share. 

************************
Upload: Dataset 
************************

If your job accesses a dataset during its run, it's recommended to upload the dataset to your XT data share. The following command shows an example::

    xt upload data/MNIST/** MNIST --share=data

The above commands uploads the files found in the local directory **data/MNIST** to the MNIST path on your XT data share.  

After the command completes, invoke the following to verify that your data is in the data share::

    xt list blobs MNIST --share=data --subdir=-1 

************************
Upload: Model
************************

If your job accesses a model during its run (for evaluation or analysis), you can upload the model to your XT models share.  Invoke the following command to upload your model::

    xt upload models/MNIST/** MNIST --share=models

The above commands uploads the model file(s) found in the local directory **models/MNIST** to the MNIST path on your XT models share. Of course, your directory settings and path may differ.

After the command completes, invoke the following to verify your model is in the models share::

    xt list blobs MNIST --share=models --subdir=-1 

--------------------------------------
Important local xt_config settings 
--------------------------------------

This section describes a number of changes to consider making to a local copy of your XT config file, beyond just editing the **advanced-mode** setting. You can also consider this a more in-depth introduction to the xt_config file, which is also described in further detail in :ref:`Understanding the XT Config file <xt_config_file>`.

***************************************
Config: Copying to your new project
***************************************

For this step, decide on the working directory of your new project. This is the project directory where you start a training or eval run.

Next, copy your **xt_config.yaml** file from one of your previous XT projects to your new project's working directory.  

If this is your first project, copy the **xt_config.yaml** file that was created during the creation of your XT services (see :ref:`Creating your Azure Cloud Services for XT <creating_xt_services>` for more information. 

If you are using a set of pre-configured Sandbox services, start with a empty **xt_config.yaml** file.  

For editing your XT config file in the following steps, use your preferred editor or the **xt config** command.

***************************************
Config: target.docker property 
***************************************

Docker is a tool that captures all of the software dependencies of a complex application and reassembles them on the same or a different computer. The application runs as it would in a normal istallation, in a portable format called a *docker image*. 

If your ML app will run in a docker container image, you will need to ensure that the **docker** property of the **compute-target** you will be using is set to the an entry in the **dockers** section that describes your docker image.  See :ref:`refer to XT and Docker <xt_and_docker>` for more information.

***************************************
Config: target.setup property 
***************************************

The **setup** property of a **compute-target** specifies an entry in the **setups** section. These **setup** entries define how to configure a compute node to be able run your ML app.

Ensure that the **setup** referred to by the **compute-target** setting that your project will use correctly specifies the steps needed to configure a node of the **compute-target**.

Refer to :ref:`Understanding the XT Config file <xt_config_file>` for more details on the **setups** section.

***************************************
Config: general.workspace property 
***************************************

For your new project and for tasks such as , you should change the name of your default workspace. A workspace stores your XT runs and experiments for current and future use. 

Workspace names are limited by the rules of Azure storage container names.

    - A blob container name must be between 3 and 63 characters in length; 
    - Container names start with a letter or number; and contain only letters, numbers, and the hyphen. All letters used in blob container names must be lowercase.

Refer to :ref:`Understanding the XT Config file <xt_config_file>` for more details on the **general** section.

**************************************
Config: general.experiment property 
**************************************

An XT experiment name is a string that you can associate with XT jobs when you submit them (with the **run** command).  If you don't specify an experiment name on the command line, it uses the value of the general.experiment property in the XT config file.

For your new project, you may want to change the experment name.

Refer to :ref:`Understanding the XT Config file <xt_config_file>` for more details on the **general** section.

***************************************
Config: general.primary-metric property 
***************************************

If the job run will perform XT hyperparameter searches, set the **primary-metric** property to the name of the metric to be used by the hyperparameter search algorithm to select more promising hyperparameter sets on each search.  

Refer to :ref:`Understanding the XT Config file <xt_config_file>` for more details on the **general** section.

*****************************************
Config: general.maximize-metric property 
*****************************************

If the job run will perform XT hyperparameter searches, set the **maximize-metric** property, in the XT config file's **General** section, to **true** if higher values of the **primary-metric** are desired (for example **accuracy**) and otherwise to **false** otherwise (for example, **loss**).

Refer to :ref:`Understanding the XT Config file <xt_config_file>` for more details on the **sgeneral** section.

*****************************************
Config: code section
*****************************************

The **code** section defines which files should be uploaded to each compute node for the ML run to proceed.  The primary settings here are a list of directories or file wildcards to upload, and a list of wildcard names to omit from uploading.

Review the **code** settings and ensure they are correct for your new project.

See :ref:`Understanding the XT Config file <xt_config_file>` for more details on the **code** section.

*****************************************
Config: after-files section
*****************************************

The **after-files** section defines which files should be uploaded from each compute node when your ML app completes. The primary settings here are a list of directories or file wildcards for upload, and a list of wildcard names to omit from uploading.

Review the **after-files** settings and ensure they are correct for your new project.

See :ref:`Understanding the XT Config file <xt_config_file>` for more details on the **after-files** section.

*****************************************
Config: data section
*****************************************

If your app needs access to an uploaded dataset, set the **data-share-path** property (in the **data** section of the XT config file) to the path on the data share containing the dataset. Set **data-action** to either **mount** (if you want to access the data thru a mapped drive) or **download** (if you want to access the data as actual local files). 

If you need to open your dataset files multiple times during a run, use the **download** value.

See :ref:`Understanding the XT Config file <xt_config_file>` for more details on the **data** section.

*****************************************
Config: model section
*****************************************

If your app needs access to an uploaded model, set the **model-share-path** property (in the **model** section) to the path on the models share containing the model. Set **model-action** to either **mount** (if you want to access the model thru a mapped drive) or **download** (if you want to access the model as actual local files). 

If you need to open your model files multiple times during a run, use the **download** value. Refer to :ref:`Understanding the XT Config file <xt_config_file>` for more information on the **model** section.

*****************************************
Config: run-reports section
*****************************************

Use the **columns** property (in the **run-reports** section of the XT config file) to specify the job's hyperparameters and metrics that will appear as columns in the **list runs** command. 

Be sure to prefix hyperparameter names by **hparams.** and metric names by **metrics.**.

You can also use these strings to specify column aliases and column formatting. Refer to :ref:`Understanding the XT Config file <xt_config_file>` for more information on the **run-reports** section.

*****************************************
Config: tensorboard section
*****************************************

Use the **template** property in XT config file's **tensorboard** section to specify the standard run columns, hyperparameter values, and literal strings that you want to appear in tensorboard for each log file. This helps you associate logs with the runs they represent, and can also be used to filter the logs by hyperparameter values and other properties.

For more information, refer to :ref:`Understanding the XT Config file <xt_config_file>`.

*****************************************
Config: aml-options section
*****************************************

If your new project will be using Azure Machine Learning, you need to specify your ML **framework**, the **fw-version**, and **distributed-training** properties in the **aml-options** XT Config File section.

See :ref:`Understanding the XT Config file <xt_config_file>` for more information on the **aml-options** section.

*****************************************
Config: early-stopping section
*****************************************

If your new project uses Azure Machine Learning and AML hyperparameter searches, you may want to specify properties in the **early-stopping** XT Config File section to control how unpromising runs can be detected and terminated early in their training sequence.

Refer to :ref:`Understanding the XT Config file <xt_config_file>` for more information on the **early-stopping** section.

.. seealso:: 

    - :ref:`Creating your Azure Cloud Services for XT <creating_xt_services>` 
    - `Azure VM Sizes <https://docs.microsoft.com/en-us/azure/virtual-machines/linux/sizes/>`_
    - :ref:`Understanding the XT Config file <xt_config_file>` 
    - :ref:`xt config command <config>` 
    - :ref:`Using Tensorboard with XT <tensorboard>` 
    - :ref:`XT and Docker <xt_and_docker>` 
