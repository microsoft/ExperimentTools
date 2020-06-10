.. _computenodereqs:

==============================
XT Compute Node Requirements 
==============================

When you run XT experiments on :ref:`pooled <pool>` compute nodes, these are typically Linux systems. Specific requirements apply to those systems when you use them with XT:

    - Python 3.x (required by XT's Pool Service Manager);
    - Install the **psutil** Python library;
    - Port 22 open for SSH on each local or pooled system;
    - The user must have a login account on each box;
    - User needs an XT-locatable key-pair for login without using a password;
    - Pre-installation of Blobfuse on any Linux host (does not apply to Windows machines). Check the :ref:`Requirements for Blobfuse on Linux <blobfuse>` below for more information on this requirement.

.. _blobfuse:

-------------------------------------------------
Requirements for Blobfuse on Linux Compute Nodes
-------------------------------------------------

XT on Linux allows the use of the Blobfuse file system driver, `for Azure Blob storage <https://docs.microsoft.com/en-us/azure/storage/blobs/storage-how-to-mount-container-linux>`_, without superuser permissions (Sudo). You will need to use the Sudo command line directive to establish this feature. After finishing this procedure, sudo command permission will not be necessary for experiments that use Blobfuse. The process described here only needs to be run once for your XT installation.

1. In your command shell, enter:

.. code-block::

    wget https://packages.microsoft.com/config/ubuntu/18.04/packages-microsoft-prod.deb

2. Then, enter the following sequence of commands at the prompt:

.. code-block::

    sudo dpkg -i packages-microsoft-prod.deb
    sudo apt-get update
    sudo apt-get install blobfuse

3. Add a configuration line with the "user_allow_other" statement to the file /etc/fuse.conf. Example: 

.. code-block::

    # /etc/fuse.conf - Configuration file for Filesystem in Userspace (FUSE)

    # Set the maximum number of FUSE file system mounts allowed to non-root users.
    # The default is 1000.
    # mount_max = 1000

    # Allow non-root users to specify the allow_other or allow_root mount options.
    **user_allow_other**

After saving your work, you'll be able to use Blobfuse on linux compute nodes for your experiments.

