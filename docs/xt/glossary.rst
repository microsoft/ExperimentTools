.. _glossary:

========================================
Glossary
========================================

XT touches on a variety of technical topics in rapdily evolving fields.  The same terms sometimes have different meanings, or
the same meanings use different terms, depending on the topic or field.  This glossary is included to help establish
a consistent definition of terms used within XT:

.. glossary::

    attach
      the ability to stream the console output (or other file) from a run to the user

    Azure
      a large Family of cloud services from Microsoft include AI, storage, and compute

    AML
      see :term:`Azure Machine Learning`

    Azure Batch
			a cloud service offering compute nodes on-demand

    Azure Container Registry
			a cloud service for secure storage of docker containers 

    Azure Cosmos
			a cloud database service with multiple API's (including SQL and MongoDB)

    Azure Key Vault
			a cloud service for securly storing certificates, keys, and other secrets

    Azure Machine Learning
			a cloud computing services designed for maching learning usage

    Azure ML
			see :term:`Azure Machine Learning`

    Azure Storage
			a cloud storage service with different APIs (blobs, files, queues)

    azure image
			refers to an OS specification for Azure Batch service


    batch
			see :term:`Azure Batch`

    bayesian
			a type of hyperparameter search which continually improves its estimates of the best performing HP values

    box
      an in-house computer or service-allocated VM that the user can run jobs on 

    
    CPU
			central processing unit (the compute engine for traditional programs); most nodes have multipe CPUs

    concurrent runs
			in XT, the maximum number of runs allowed to run simultaneously by the XT controller

    conda
			package manager and environment management system (typically for python packages)

    container registry
			see :term:`Azure Container Registry`

    cosmos
			see :term:`Azure Cosmos`

.. _dgd:

    DGD
			Distributed Grid Descent - a hyperparameter search algorithm that uses a neighborhood search strategy to find best values

    data
			the set of training or evauluation samples used by a ML app

    direct run
			a run submitted by XT but launched directly on the node (without using the XT controller)

    distributed training
			a single training run that uses multiple computing nodes to speed up the training

    distributed parallel training
			a single training run that uses multiple nodes (and multiple GPUs/CPUs on each node) to accelerate training

    Docker
			a program that uses OS-level virtualization to provider client programs with their exact set of complex dependencies

    Docker image
			a file that contains a specific runtime environment (libraries and packages) for client programs 

    Docker container
			a instaniated docker image (running on a computer under the control of Docker)

    download
			copying files from XT cloud storage to the local machine or a compute node

    dynamic
			an XT search style that performs a hyperparameter search before launching each new child run

  
    early stopping
      TBD

    environment variables   
			a set of name/value pairs that can be assigned to a process (run), script, or shell session

    experiment 
			a name that can be assigned to a job (and its runs) when the job is submitted 


    feedback   
			output from a process showing progress being made

    framework  
			one of the Deep Learning frameworks (pytorch, tensorflow, keras, etc.)


    GPU  
			Graphics Processing Unit (the compute engine for Deep Learning programs); many nodes have multiple GPUs

    grid 
			a type of hyperparameter search algorithm where all combinations of discrete values of hyperparameters are consistently searched


    hyperparameter (HP)
			a training variable that can be set to 1 of multiple values (where the best vaule is usually unknown)

    hyperparameter search   
			multiple runs with different hyperparameter settings with the goal of finding the best settings


    jupyter notebook        
			a web-based application where the user can create and run vertical bands of code or rich text (with code running on a hosting server)


    key vault  
			see :term:`Azure Key Vault`


    localhost  
			the network name of the current computer 

    local machine           
			the current computer that the user is interacting with

    logging    
			the recording of hyperparameter values and training/evaluation metrics by a ML app (usually to a file, Tensorboard, and/or XT)

    low-pri    
			a computing services where some nodes may be preempted for short time periods (effective restarting the run on return)


    machine learning (ML)
			a type of program processes training data to improve its performance

    metrics    
			a set of programmer-defined standard measurements used to access the quality of a ML model or program (e.g., accuracy or loss)

    mirror     
			the monitoring and copying of files, as they change, from the ML app's node to the run's associated cloud storage

    model
			a file that represents what the program has learned from it's training data

    MongoDB    
			an object-oriented database with JSON-like documents (nested key/value pairs and arrays)

    multi
			an XT search style, where the user provides a generated set of run cmds to use for hyperparameter searching


    node 
			a computing unit, typically a virtual machine (VM)


    parallel training       
			a single training run on a single node that uses multiple GPUs or CPUs to speed up the training
 
.. only:: internal 

    Philly     
      an internal Microsoft computing service 
.. only:: internal or not internal

    pip  
			program for installing python packages 
.. _pool:

    pool 
			a set of boxes that the user can use to run jobs on 

    primary metric          
			the user-specified metric that used by several services (hyperparameter search, early stopping, ...) 

    provider   
			in XT, a python class that provides 1 of 4 types of extensible services: commands, storage, compute, and hyperparameter search


    random     
			a type of hyperparameter search where values for hyperparameters are chosen from a list or distribution at random

    registry   
			see :term:`Azure Container Registry`

    run  
			a single execution of the user's ML app/script


    side-by-side training   
			multiple independent runs on multiple nodes (1 per node), typically used by hyperparameter searching

    single     
			the default search style, where just a single run on a single node is executed

    share
			a named storage container where the user store files and folders

    static     
			a search style where all of the run commands are generated before the job is submitted (used by **random** and **grid** search types)

    storage    
			cloud based storge for runs, jobs, workspaces, and shares


    target     
			the named compute target for a job, or its definition which describes the service, nodes, and environment

    team 
			an XT team is a named set of services that is configured to be used by 1 or more specified persons

.. _tensorbd:

    tensorboard
			a logging format for ML artifacts (data, gradients, weights, images, etc.) and an associated web app visualization tool 


    upload     
			copying files from the local machine or a compute node to XT cloud storage

    user managed            
			refers to boxes that the user has pre-configured such that XT or the backend service don't run any configuration actions for those boxes


    vault
			see :term:`Azure Key Vault`

    VM
      virtual machine

    virtual machine         
			an emulation of a computer (running on a physical computer). The standard way of packaging cloud compute offerings.

    vm-size    
			a name for a specific computer hardware configuration (see: https://docs.microsoft.com/en-us/azure/virtual-machines/windows/sizes)


    workspace  
			an XT unit of storage that contains XT runs.  workspaces are usually aligned with projects or subprojects.


    XT   
			the command line tool for managing, scaling, and reporting of ML experiments

    XTLib
			the pip-installable name for the package containing XT.  Also, the library that XT is written with, with its own API.


Should we include these: gradients, weights, parameters, deep learning, AI

.. seealso:: 


			:ref:`XT config file<xt_config_file>`



