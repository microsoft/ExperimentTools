.. _remote_control:

===============================
Secure Remote Control of Jobs
===============================

The XT client can communicate with XT jobs running on remote machines (provided that are running
with the XT controller enabled, i.e., not in direct mode).  

This remote control enables several services:
    - streaming console output
    - querying the status of the controller and its runs
    - terminating selected runs
    - starting and stopping related services (Tensorboard, Jupyter Notebook, Mirroring of files, etc.)

--------------------------------------
Communication Support, by Event
--------------------------------------

XT client and controller work together at various stages, to build a secure commication channel:

    - when we create a service group for an XT team:
        - we also create a pair of self-signed certs in the vault (one for client, one for controller)

    - when the XT client authenticates with Azure Active Directory:
        - it gets various keys and the pair of certs from the vault
        - it gets the token associated with the authentication
        - it uses the token to read UserPrincipleName from the Microsoft Graph entry for the user
        - it caches all of this info in memory (XT cache server)
        
    - when a user submits a job thru the XT client:
        - it retrieves the controller cert and the UserPrincipleName from the cache
        - it sets the following environment variables for the controller:
            - XT_SERVER_CERT
            - XT_USER_PRINCIPLE_NAME

    - when the XT controller runs on the compute node:
        - it uses the value of the XT_SERVER env var and creates a cert .pem file
        - it uses the .pem file to initiate an SSL communication session (rpyc server)
        - when the XT controller app finally exits, it deletes the cert file (cannot delete any earlier since file is loaded on each rpyc connection)

    - when the XT client wants to communicate with the server:
        - it retrieves the client cert and the user’s token from the cache 
        - it writes the client cert to a local .pem file
        - it creates an SLL-based rpyc client connection with the XT controller (using the .pem file)
        - it deletes the local .pem file (here it can be immediately deleted)
        - it sends a request with the token to the XT controller

    - when the XT controller receives a request:
        - it uses the required token argument to read the UserPrincipleName from the Microsoft Graph
        - if the UserPrincipleName doesn’t match the value of the XT_USER_PRINCIPLE_NAME env var, an ACCESS DENIED exception is raised

