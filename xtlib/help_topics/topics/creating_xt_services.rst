.. _creating_xt_services:

=========================================
Creating Azure Cloud Services for XT
=========================================

XT uses a set of Azure cloud services to run jobs on cloud computers, log statistics, and to store experiment artifacts. 

By default, XT does not provide the set of Azure cloud services for XT use. To create a new set of Azure cloud services to support and run your XT machine learning experiments, follow the instructions in this topic.

.. note:: If you already have a set of Azure cloud services that you want to use with XT, see :ref:`Understanding the XT Config file <xt_config_file>`.

After you install XT, run the **xt create services template** command to create the template for the new cloud services you'll use with XT. 

Using the **xt create services template** command, setup should take the following times:
    - Create the Azure services for your XT deployment (20 mins);
    - Add the service secure keys and XT certificate to the key value (15 mins);
    - Edit the local XT config file with your important values (25 mins).

------------------------------
Solo and Team Setups
------------------------------

Multiple XT users can share a set of XT services.

If you're in a development team that wants to share a set of Azure services, choose a team member to be the XT admin. The XT admin manages creation of the XT services and maintains a list of your service users.

If you are setting up XT for your own use, you create the XT services as the solo user.

.. only:: internal 

    .. note:: Your organization may have a set of sandbox cloud services on Azure, which are designed for trying out and learning how to use XT. When you are ready to do work, you will want to create the complete set of services for your team.

--------------------------
The Azure Services for XT
--------------------------

.. note:: This section assumes you are running XT in Advanced mode.

Every XT installation uses up to 6 Azure services. You can use more, but this set of 6 is what most deployments operate with. Out of those 6, three services are required for core applications with XT:

    - **Storage**            Provides cloud storage for your experiments. (**Required**)
    - **MongoDB**            Database for statistics and metrics of your experiments. (**Required**)
    - **Key Vault**          Secure credential storage for Azure services. (**Required**)
    - **Azure Batch**        A general compute service for on-demand Virtual Machine deployment. (Optional, but you must use this or local compute node(s) for running your jobs)
    - **Azure ML**           Compute services designed for Machine Learning on VMs. (Optional)
    - **Container Registry** Storage for Docker images. (Optional)

.. only:: internal

    Other cloud services you can use include the following:

        - Azure Virtual Machine / Virtual Machine Scale Set (Optional)
        - Generic Remote Server (Optional)
        - Philly (Optional)

.. only:: not internal

    Other cloud services you can use include the following:

        - Azure Virtual Machine / Virtual Machine Scale Set (Optional)
        - Generic Remote Server (Optional)

.. note:: Azure ML (AML) is an optional Advanced application for XT usage.

The following steps illustrate how to create these services from the Azure Portal (https://portal.azure.com). We use default settings for service creation except where noted. 

.. note:: Your service names will differ from those shown below; ensure consistency with your service names, and note them down in case of mistakes. Even a single character being off in a service name entry is enough to keep the process from a successful conclusion. 

--------------------------------
Create services template command
--------------------------------

You start by running the **xt create services template** command. It generates an Azure service template that you upload to the Azure Portal.  

.. code-block:: none

   (xt) C:\ExperimentTools> xt create services template
   template generated: create_xt_service_template.json

To create the resources for your XT team, do the following:

    1. Browse to the `Azure Portal Custom Template Deployment page 
    <https://portal.azure.com/#create/Microsoft.Template>`_.

    2. Select 'Build your own template in the editor'.

    3. Copy/paste the contents of the generated file into the template editor or select Load file from the menu.

    4. Click 'Save'.

    5. Select the billing subscription for the resources.

    6. For a resource group, choose 'Create new' and enter a simple, short, and unique team name (no special characters).

    7. Check the 'I Agree' checkbox and choose 'Purchase'. 

    8. If you receive a 'Preflight validation error', you may need to choose another (unique) team name.

    9. After 5-15 minutes, you should receive a 'Deployment succeeded' message in the Azure Portal.

    10. At this point, you can create a new local XT config file for your team.

The template is a schema file in JSON. By default, the **xt create services template** command places this file in the current directory. 

.. note:: You can copy and paste the contents of the template JSON file, or load it into the custom template page. (After selecting **Build your own template in the editor**, choose **Load file**.) In either case, your Azure tenant ID appears throughout the template. Avoid changing any values in the template file at this phase.

After clicking **Save**, select the Azure billing **Subscription**. 

If you already have a **Resource group**, choose that from its drop-down as well, or choose **Create new** to create a new one. 

After you check the **I Agree** checkbox, choose **Purchase**. Azure goes to work building your resource group and its component resources.

---------------------------------------------------
Creating the Vault Secret
---------------------------------------------------

After you establish the Azure services and your resource group, you will need to install the Key Vault secrets for your Azure services. You do this by creating a single secret that contains the keys for the services described in this procedure, and add it to your vault.  Part of the task involves accessing your newly created Azure services.  

To access services in the Azure Portal, we suggest using the Azure web UI:

    - Log in to your Azure account.
    - Choose **Resource groups** in the left panel. 
    - Choose your team's resource group.
    - Find and choose the desired service (you can ignore the service names with extra text appended to them).

#. Using a code or text editor, paste the following JSON dictionary string into an empty file::

    { 
        "phoenixstorage": "key": 
        "phoenixmongodb": "key",  
        "phoenixbatch": "key", 
        "phoenixregistry": "key"
    }

#. Replace each of the service names in the above with your Azure service names (suggestion: do an editor search & replace "phoenix" to your team name).

#. For each "key" string, replace with the associated service key or connection string values. For this step, go to each service in the Azure Portal, choose the **Access Keys** tab or **Connection string** tab in the left panel, and copy the primary key or connection string value.

   For the **Storage** service:

      #. Navigate to your Azure storage service.
      #. Choose the **Access Keys** tab in the service's left panel.
      #. Select the **Key 1** field's copy-to-clipboard button.
      #. Paste the storage services key into your editor for the Azure Storage Service key.

   For the **MongoDB** service:

      #. Navigate to your MongoDB service.
      #. Choose the **Connection string** tab in the service's left panel.
      #. Click the **PRIMARY CONNECTION STRING** field's copy-to-clipboard button.
      #. Paste the MongoDB key string into your editor for the MongoDB service key.

   For the **Azure Batch** service:

      #. Navigate to your Azure Batch service.
      #. Choose the **Keys** tab in the service's left panel.
      #. Choose the **Primary access key** field's copy-to-clipboard button.
      #. Paste the batch key value into your editor for the Batch service key.

   For the **Container Registry** service: (not required for Basic mode)

      #. Navigate to your registry service.
      #. Choose the **Access Keys** tab in the service's left panel.
      #. Set the Admin User button to **Enable** if it isn't already enabled.
      #. Choose the **Password** field's copy-to-clipboard button.
      #. Paste the copied password value into your editor for the Registry service key. 

   The result should resemble the following::

      { 
          "phoenixstorage": "qfXOrW7bHQwVOSQ20ViTlsh4GRSmn4UwzbdMTkqqGlVt9sqtwHuWVyBR1XRGti3K1lVMIk4k0S1xgOz58eT4ag==",   
          "phoenixmongodb": "mongodb://phoenixmongodb:mBoJtNrGtkAhwnzRzbT664H3wAFZvwz9l3ARygXzlHBUQerwZwv7QpbU5Nw9pnV9YyNA9wUnrmLGbfFLB7WH3g==@phoenixsmongodb.documents.azure.com:10255/?ssl=true&replicaSet=globaldb",  
          "phoenixbatch": "/suVqpCkEoC8n1VA0XRhjR24YNKdisfwIVwoyNtIBsdCsqKgm6QDBoaB6kHxACB7a4sHr0WSbkic59o67WCB7w==", 
          "phoenixregistry": "qHHBRO8okQdwOqBYnp=a9XMIceNUuoDl"
      }

#. From your code/text editor, copy the entire JSON dictionary string that you modified in Step 3 (both service names and keys) into your clipboard.

#. In the Azure Portal, do the following:

   a. Navigate to your team's (or your own) Key Vault service. 
   b. Choose the **Secrets** tab in the left panel.
   c. Choose **+ Generate/Import**.
   d. For **Name**, enter "xt-keys".
   e. For the **Value**, paste in the copied JSON dictionary (Ctrl+v).
   f. Click **Create**.

#. When you're finished, delete any files or open editor instances containing any key information.

*******************************************
Adding the XT certificates to the Key Vault
*******************************************

You also need to separately add your XT certificates to the Azure Portal. Do the following:

#. Navigate to the Key Vault service associated with your Azure tenant. 
#. Choose the "Certificates" tab in the left pane. 
#. Create the CLIENT CERT:

   a. Click **+ Generate/Import**.
   b. For the **Method of Certificate Creation**, select "Generate".
   c. For the **Certificate Name**, enter "xt-clientcert".
   d. For the **Subject**, enter "CN-xtclient.com".
   e. For the **Content Type**, change it to "PEM".
   f. Click **Create**.

#. Create the SERVER CERT:

   a. Click **+ Generate/Import**.
   b. For the **Method of Certificate Creation**, select "Generate".
   c. For the **Certificate Name**, enter "xt-servercert".
   d. For the **Subject**, enter "CN-xtserver.com".
   e. For the **Content Type**, change it to "PEM".
   f. Click **Create**.

-----------------------------------------------------------
Create a Compute Instance for your AML service
-----------------------------------------------------------

#. Navigate to your Azure ML service.
#. Choose the **Compute** tab in the left panel.
#. Click **+ New**.
#. For **Compute Name**, we suggest the team name followed by "compute" (such as phoenixcompute).
#. For **Virtual Machine Size**, select the CPU/GPU configuration for the VMs your service will use. 

   .. note:: You can incur expenses by choosing a VM size that uses substantial resources.

#. Click **Create**.

-----------------------------------------------------------
Editing your local XT config file 
-----------------------------------------------------------

To edit your local XT config file ('xt config' cmd), do the following:

1. Open your local xt_config.yaml file. If you do not have this file in the directory where you run XT, run the following command:

.. code-block:: none

    (xt) C:\ExperimentTools> xt config

A new copy of the local xt_config.yaml file opens in your default text editor. It reads as follows:

.. code-block:: none 

    # local xt_config.yaml
    # uncomment the below lines to start populating your config file

    # general:
        #workspace: 'ws1'
        #experiment: 'exper1'

Before you start editing in earnest, make sure that the local xt_config.yaml file reads as follows (with no commenting hashtag in the 'general' line):

.. code-block:: none 

    # local xt_config.yaml
    # uncomment the below lines to start populating your config file

    general:
        advanced-mode: true
        #workspace: 'contoso1'
        #experiment: 'contoso1'

You will edit this file to use all of your new services' settings.

2. Copy/paste the following sections (or merge them with existing sections of the same name):

.. only:: internal

  .. code-block:: none 

    external-services: 
        phoenixbatch: {type: "batch", key: "$vault", url: "xxx"} 
        phoenixaml: {type: "aml", subscription-id: "xxx", resource-group: "xxx"} 
        phoenixstorage: {type: "storage", provider: "azure-blob-21", key: "$vault"} 
        phoenixmongodb: {type: "mongo", mongo-connection-string: "$vault"} 
        phoenixkeyvault: {type: "vault", url: "xxx"} 
        phoenixregistry: {type: "registry", login-server: "xxx", username: "xxx", password: "$vault", login: "true"} 

    xt-services:
        storage: "phoenixstorage"        # storage for all services 
        mongo: "phoenixmongodb"          # database used for all runs across services 
        vault: "phoenixkeyvault"         # where to keep sensitive data (service credentials) 

    compute-targets:   
        batch: {service: "phoenixbatch", vm-size: "xxx", azure-image: "dsvm", nodes: 1, low-pri: true,  box-class: "dsvm", docker: "none"} 
        philly: {service: "philly", vc: "xxx", cluster: "xxx", sku: "xxx", nodes: 1, low-pri: true} 
        aml: {service: "phoenixaml", compute: "xxx", vm-size: "xxx", nodes: 1, low-pri: false}      
        # Internal users should add their own VC, cluster and SKU values.

    general:
        advanced-mode: true
        workspace: "contoso-ws"
        experiment: "contoso1"
        primary-metric: "test-acc"             # name of metric to optimize in roll-ups, hyperparameter search, and early stopping
        maximize-metric: true                  # how primary metric is aggregated for hp search, hp explorer, early stopping 
        xt-team-name: "phoenix"                

    setups:
        local: {activate: "$call conda activate $current_conda_env", conda-packages: [], pip-packages: ["xtlib==*"]}
        philly: {activate: null, conda-packages: [], pip-packages: ["xtlib==*"]}
        py36: {activate: "$call conda activate py36", conda-packages: [], pip-packages: ["xtlib==*"]}
        aml: {pip-packages: ["torch==1.2.0", "torchvision==0.4.1", "Pillow==6.2.0", "watchdog==0.9.0", "xtlib==*"] }

.. only:: not internal 
  
  .. code-block:: none 

    external-services: 
        phoenixbatch: {type: "batch", key: "$vault", url: "xxx"} 
        phoenixaml: {type: "aml", subscription-id: "xxx", resource-group: "phoenix"} 
        phoenixstorage: {type: "storage", provider: "azure-blob-21", key: "$vault"} 
        phoenixmongodb: {type: "mongo", mongo-connection-string: "$vault"} 
        phoenixkeyvault: {type: "vault", url: "xxx"} 
        phoenixregistry: {type: "registry", login-server: "xxx", username: "xxx", password: "$vault", login: "true"} 

    xt-services:
        storage: "phoenixstorage"        # storage for all services 
        mongo: "phoenixmongodb"          # database used for all runs across services 
        vault: "phoenixkeyvault"         # where to keep sensitive data (service credentials) 
        target: "local"

    compute-targets:   
        batch: {service: "phoenixbatch", vm-size: "xxx", azure-image: "dsvm", nodes: 1, low-pri: true,  box-class: "dsvm", docker: "none"} 
        aml: {service: "phoenixaml", compute: "xxx", vm-size: "xxx", nodes: 1, low-pri: false}      

    general:
        advanced-mode: true
        workspace: "contoso-ws"
        experiment: "contoso1"
        advanced-mode: true
        primary-metric: "test-acc"             # name of metric to optimize in roll-ups, hyperparameter search, and early stopping
        maximize-metric: true                  # how primary metric is aggregated for hp search, hp explorer, early stopping 
        xt-team-name: "phoenix"                

    setups:
        local: {activate: "$call conda activate $current_conda_env", conda-packages: [], pip-packages: ["xtlib==*"]}
        py36: {activate: "$call conda activate py36", conda-packages: [], pip-packages: ["xtlib==*"]}
        aml: {pip-packages: ["torch==1.2.0", "torchvision==0.4.1", "Pillow==6.2.0", "watchdog==0.9.0", "xtlib==*"] }

3. Replace all occurences of "phoenix" with the name of your team.

4. Replace all "xxx" values with the associated property of the specified service, using information from the Azure Portal.

5. For the "compute-targets" and "general" sections, review the settings and edit as needed.  See the :ref:`XT Config File help topic <xt_config_file>` for additional information about these properties.

-----------------------------------------------------------
Test your new XT services
-----------------------------------------------------------

Test your new XT services configuration by running XT in the directory that contains your local XT config file. Try the following commands in the specified order:

    #. Run **xt list workspaces**. This tests that your Key Value and Storage services are configured correctly.
        - If an error occurs, double check the Key Vault service properties and XT configuration file properties for those services.

    #. **xt create workspace ws-test** 
        - Checks to see that your Storage account is writable. 
        - If you see a "Block blobs are not supported" error, you probably selected the wrong version of the storage **kind** property in the Azure storage configuration.  If this is the case, you will need to recreate the storage services.

    #. **xt run <script>**
        - Checks for the correct configuration of the Mongo DB service.
        - If you see a **getaddrinfo failed** error, you may have specified the wrong connection string for mongodb.  if so, update the xt-keys secret in the vault.

    #. xt run --target=batch <script>
        - This will ensure that the Batch service is configured correctly

    #. xt run --target=aml <script>
        - this will ensure that the Batch service is configured correctly

If you need to recreate one or more of the cloud services, do the following:

    #. Delete the old service in the Azure console.
    #. Create the new service using the same name.  Be aware that some services may take 5-10 minutes before the name can be reused.
    #. Get the keys string from the **xt-keys** secret in the Key Vault.
    #. Use an editor to update the keys for any new services.
    #. Create a new version of the **xt-keys** secret with the updated JSON dictionary string.
    #. On your local machine, be sure to run **xt kill cache** before trying further testing.

.. seealso:: 

    After creating your XT services, you need to set up your XT project to do your first job runs. See :ref:`Defining Code Changes for your XT Installation <prepare_new_project>` for more information.
 
