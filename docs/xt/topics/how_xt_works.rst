.. _how_xt_works:

=======================================
How XT Works
=======================================

XT operates through a series of four basic stages: your initial configuration, its associated Azure cloud services, login and authentication, and the sets of default and local XT Config settings and the XT commands you run for your ML job submissions.

Basic XT configuration:
    1. Enter your Azure service information in the **external-services** section of your config file;
    2. Create entries in the **compute-targets** section for 1 or more COMPUTE targets to use for running experiments;
    3. Add the storage, compute, and vault services to be used by XT in the **xt-services** section;
    4. For each compute target, specify the **setup** property with the name of an entry in the **setup** section
    5. **setups** entries allow you to specify:
        - an environment activation command (conda, venv, etc.)
        - a list of conda packages your app needs installed on the associated compute target
        - a list of pip packages your app needs installed on the associated compute target
    6. [optional] Enter the computers that you have available to run with in the **boxes** section.

Services:
    1. XT uses a set of Azure cloud services to run jobs on cloud computers, log stats, and store experiment artifacts;
    2. After installing XT, run the **xt create team** command to create a template for the services;
    3. Run the new services template in the Azure Portal to create the cloud services for your installation. You can use the Azure services alone or share them with a team.

Authentication:
    1. Azure Active Directory authenticates the user;
    2. The user's service credentials are stored in Azure Key Vault;
    3. XT caches service credentials, which stay active for the current OS session. When you run XT in a new OS session, you will be authenticated again

Configuration Settings:
    1. XT maintains a set of default settings for all commands and services 
    2. Any subset of these settings can be overridden by a local XT config file (a file in the working directory)
    3. In addition, XT's command line options can override/supplement the config file settings relevant to the associated command

    - :ref:`Creating XT Services <creating_xt_services>`
    - :ref:`Prepare a new Project <prepare_new_project>`
    - :ref:`Job Submission <job_submission>`
