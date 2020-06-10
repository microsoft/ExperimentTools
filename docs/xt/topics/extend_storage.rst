.. _extend_storage:

======================================
Adding storage providers
======================================

XT's built-in set of supported storage systems can be extended by the user.

The general idea is to write a python class that implements the XT **StorageInterface**.

The XT **StorageInterface** is defined as follows::

    from interface import implements, Interface

    class StoreInterface(Interface):
        #def __init__(self, storage_creds_dict):
        #    ''' the constructor must accept a provider-specific storage_creds_dict argument '''
        #    pass

        # ---- MISC part of interface ----
        def get_retry(self):
            ''' return the error return count'''
            pass

        def set_retry(self, value):
            ''' set the error return count'''
            pass

        # ---- CONTAINER interface ----

        def does_container_exist(self, container):
            pass

        def create_container(self, container):
            pass

        def list_containers(self):
            pass

        def delete_container(self, container):
            pass

        def get_container_properties(self, container):
            pass

        def get_container_metadata(self, container):
            pass

        # ---- BLOB interface ----

        def does_blob_exist(self, container, blob_path):
            pass

        def create_blob(self, container, blob_path, text, fail_if_exists=False):
            pass

        def create_blob_from_path(self, container, blob_path, source_fn, progress_callback=None):
            pass

        def append_blob(self, container, blob_path, text, append_with_rewrite=False):
            pass

        def list_blobs(self, container, path=None, return_names=True, recursive=True):
            '''
            NOTE: the semantics here are a bit tricky

            if recursive:
                - return a flat list of all full path names of all files (no directory entries)
            else: 
                - return a flat list of all files and all directory names (add "/" to end of directory names)

            if return_names:
                - return list of names
            else:
                - return a list of objects with following properties:
                    .name     (file pathname)
                    .properties
                        .content_length   (number)
                        .modified_ns      (time in ns)

            '''
            pass

        def delete_blob(self, container, blob_path, snapshot=None):
            pass

        def get_blob_text(self, container, blob_path):
            pass

        def get_blob_to_path(self, container, blob_path, dest_fn, snapshot=None, progress_callback=None):
            pass

        def get_blob_properties(self, container, blob_path):
            pass

        def get_blob_metadata(self, container, blob_path):
            pass

        def copy_blob(self, source_container, source_blob_path, dest_container, dest_blob_path):
            pass

        def snapshot_blob(self, container, blob_path):
            pass

An implementation of a storage provider could begin as follows::

        from interface import implements, Interface

        class MyCloudStorage(implements(MyInterface)):

            def __init__(self, storage_creds_dict):
                ''' the constructor must accept a provider-specific storage_creds_dict argument '''
                self.storage_creds_dict = storage_creds_dict

        # implment rest of **StorageInterface** methods here...


The steps for adding a new storage provider to XT are:
    - create a python class with that implements each method of the XT **StorageInterface**
    - add a provider name and its **code path**  as a key/value pair to the **storage** provider dictionary in your local XT config file
    - add a storage service under **external-services** that uses the store provider (in your local XT config file)
    - set the **storage** property for **xt-services** to your newly added storage service (in your local XT config file)
    - ensure your provider package is available to XT (in the Python path, or a direct subdirectory of your app's working directory), so that 
      XT can load it when needed (which could be on the XT client machine and/or the compute node)

For example, to add our storage provider class to XT, we include the following YAML section to our local XT config file::

    external-services:
        # storage services
        mycloudstorage: {type: "storage", provider: "store-mycloud", account: "https://johnsmith@mycoudstorage.com/myservice"}

    xt-services:
        storage: "mycloudstorage"        # storage for all XT services 
    
    providers:
        storage: {
            "store-mycloud": "extensions.my_cloud_storage.MyCloudStorage" 
        }

Where **extensions** is the parent directory of the **my_cloud_storage.py** file)

.. seealso:: 

    - :ref:`XT Config file <xt_config_file>`
    - :ref:`Extensibility in XT <extensibility>`
