.. _create_services_template:  

========================================
create services template command
========================================

Usage::

    xt create services template [OPTIONS]

Description::

    Once you have run this command to generate a team template, follow these instructions to complete the process:

    1. browse to the Azure Portal Custom Template Deployment page: https://ms.portal.azure.com/#create/Microsoft.Template
    2. select 'Build your own template in the editor'
    3. copy/paste the contents of the generated file into the template editor
    4. click 'Save'
    5. select the billing subscription for the resources
    6. for resource group, choose 'Create new' and enter a simple, short, unique team name (no special characters)
    7. check the 'I Agree' checkbox and click on 'Purchase'
    8. if you receive a 'Preflight validation error', you may need to choose another (unique) team name
    9. after 5-15 minutes, you should receive a 'Deployment succeeded' message in the Azure Portal


Options::

  --all      flag    generate a template to create all XT services
  --aml      flag    generate a template to create XT base services with Azure Machine Learning
  --base     flag    generate a template to create XT base services
  --batch    flag    generate a template to create XT base services with Azure Batch

Examples:

  create a template for a new XT team::

  > xt create services template

