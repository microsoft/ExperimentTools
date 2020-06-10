.. _xt_and_docker:

========================================
Running Docker images with XT 
========================================

XT supports ML apps that run in Docker containers.  

==> TODO: this doc needs to be updated with latest XT config file support for environments

The suggested steps for development with XT are as follows:

    1. for these steps:
        - let MY-REGISTRY-NAME be the name of your Azure Container Registry
        - let MY-IMAGE-NAME be the name of the Docker image you are developing
        - MAIN-SCRIPT is the name of the python script in your current directory that you want to run
        - this example assumes the model where your main script runs "on top of" your Docker image

    2. create an Azure Container Registry service via the Azure Portal 

    3. add the server, username, password of your registry to your XT config file

    4. develop your app + docker image on your local machine (without XT)

    5. create a batch file (see below) to tag and push your docker image to your registry
    
    6. PUSH.BAT:
        call xt docker login
        set registry=MY-REGISTRY-NAME.azurecr.io

        call docker tag MYIMAGE-NAME %registry%/MYIMAGE-NAME
        call docker push %registry%/MYIMAGE-NAME

    7. run "PUSH.BAT" to push your image to your registry

    8. test the app + docker image on your LOCAL MACHINE with XT:

        > xt docker run --rm -v %cd%:/usr/src MY-REGISTRY-NAME.azurecr.io/MY-IMAGE-NAME python /usr/src/MAIN-SCRIPT.py

    9. test the app + docker image on AZURE BATCH with XT:

        > xt --pool=azure-batch docker run --rm -v $(pwd):/usr/src MY-REGISTRY-NAME.azurecr.io/MY-IMAGE-NAME python /usr/src/main_script.py

----------------------------------------
"Permission Denied" Docker Errors
----------------------------------------

If you are getting the "permisson denied" error trying to run basic docker commands on a Linux system, the following steps may help:

    1. from shell: sudo usermod -a -G docker $USER
    2. restart your shell session
    3. from shell: docker info

The **docker info** command should now run without errors.  



The above co
----------------------------------------

Problems mounting local drive on Windows
----------------------------------------

If you see the error "docker: Error response from daemon: error while creating mount source path '<path...>' mkdir <path...>: permission denied", 
you can workaround by:

    - create a local machine user account
    - go to docker settings, shared drive, reset credentials, and then share your drive uses the local machine account

