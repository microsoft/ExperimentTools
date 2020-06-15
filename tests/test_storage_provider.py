import os
import shutil
import datetime

import test_base
from xtlib import utils
from xtlib import errors
from xtlib import file_utils
from xtlib.helpers import xt_config
from xtlib.helpers.dir_change import DirChange




class TestStorageProviderSandboxStorage(test_base.TestBase):

    def setup_class(cls):
        """
        Setup once for all tests
        """
        cls.TEST_DIR = "tests/storageProviderTests"
        cls.TEST_FILE = f"{cls.TEST_DIR}/test.txt"

        cls.QT_CONTAINER = "storage-provider-test"
        cls.TEST_CONTAINER = "storage-test-container"

        cls.TEST_BLOB = "__storage_test_blob__"
        cls.TEST_BLOB2 = "__storage_test_blob2__"
        cls.TEST_BLOB3 = "__storage_test_blob3__"
        cls.NEST_BLOB = "foo/blob1.txt"
        cls.NEST_BLOB2 = "foo/blob2.txt"
        cls.NEST3_BLOB = "foo/bar/ski/blob1.txt"
        cls.APPEND_BLOB = "__storage_test_append_blob__"

        cls.BLOB_TEXT = "this is the test blob!"
        cls.APPEND_TEXT = "this is the append text\n"

        cls.RETRY = 10

        cls.config = xt_config.get_merged_config()
        file_utils.ensure_dir_exists(cls.TEST_DIR)

        # get info about storage_name
        cls.storage_creds = cls.config.get_service("xtsandboxstorage")
        cls.provider_name = cls.storage_creds["provider"]

        # create the provider class
        cls.impl_ctr = cls.config.get_provider_class_ctr("storage", cls.provider_name)
        cls.impl = cls.impl_ctr(cls.storage_creds)

        if cls.impl.does_container_exist(cls.QT_CONTAINER):
            cls.impl.delete_container(cls.QT_CONTAINER)

        cls.impl.create_container(cls.QT_CONTAINER)

    def teardown_class(cls):
        """
        Teardown once after all tests
        """
        cls.impl.delete_container(cls.QT_CONTAINER)
        shutil.rmtree(cls.TEST_DIR)

    def setup(self):
        """
        Setup per test
        """
        pass

    def teardown(self):
        """
        Teardown per test
        """
        pass

    def test_service(self):

        # set RETRY
        retry_func = utils.make_retry_func(self.RETRY)
        self.impl.set_retry(retry_func)

        # get RETRY
        returned_func = self.impl.get_retry()

        self.assertTrue(retry_func == returned_func)

    def test_container(self):
        '''
        tests out basic interface of storage provider. 

        Note: running this test multiple times can result in normal Azure retries due to
        the delay it imposes in creating a container after it has been deleted.
        '''

        # EXISTS
        exists = self.impl.does_container_exist(self.QT_CONTAINER)
        self.assertTrue(exists)

        # LIST CONTAINERS
        containers = self.impl.list_containers()
        self.assertTrue(self.QT_CONTAINER in containers)

        # CONTAINER EXISTS
        exists = self.impl.does_container_exist("no-such-container")
        self.assertTrue(not exists)

        exists = self.impl.does_container_exist(self.QT_CONTAINER)
        self.assertTrue(exists)

        # CREATE CONTAINER
        if self.impl.does_container_exist(self.TEST_CONTAINER):
            self.impl.delete_container(self.TEST_CONTAINER)

        self.impl.create_container(self.TEST_CONTAINER)
        containers = self.impl.list_containers()
        self.assertTrue(self.TEST_CONTAINER in containers)

        # DELETE CONTAINER
        self.impl.delete_container(self.TEST_CONTAINER)
        containers = self.impl.list_containers()
        self.assertTrue(not (self.TEST_CONTAINER in containers))

        # GET CONTAINER PROPS (Note: these will be specific to the provider)
        result = self.impl.get_container_properties(self.QT_CONTAINER)
        self.assertTrue(result)

        md = self.impl.get_container_metadata(self.QT_CONTAINER)
        self.assertTrue(isinstance(md, dict))

    def test_blob(self):
        # LIST BLOBS
        blobs = self.impl.list_blobs(self.QT_CONTAINER)
        self.assertTrue(isinstance(blobs, list))

        # BLOB EXISTS
        exists = self.impl.does_blob_exist(self.QT_CONTAINER, "__no_such_blob__")
        self.assertTrue(not exists)

        # CREATE BLOB
        self.impl.create_blob(self.QT_CONTAINER, self.TEST_BLOB, self.BLOB_TEXT)
        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.TEST_BLOB)
        self.assertTrue(exists)

        blobs = self.impl.list_blobs(self.QT_CONTAINER)
        self.assertTrue(self.TEST_BLOB in blobs)

        # CREATE BLOB - FAIL IF EXISTS
        got_failure = False

        # set retries to 0 
        retry_func = utils.make_retry_func(0)
        self.impl.set_retry(retry_func)

        try:
            self.impl.create_blob(self.QT_CONTAINER, self.TEST_BLOB, Bself.LOB_TEXT, fail_if_exists=True)
        except BaseException:
            got_failure = True

        self.assertTrue(got_failure)

        # CREATE BLOB - OK IF EXISTS
        self.impl.create_blob(self.QT_CONTAINER, self.TEST_BLOB, self.BLOB_TEXT, fail_if_exists=False)
        self.assertTrue(self.TEST_BLOB in blobs)

        # CREATE NESTED PATH BLOBS
        self.impl.create_blob(self.QT_CONTAINER, self.NEST_BLOB, self.BLOB_TEXT)
        self.impl.create_blob(self.QT_CONTAINER, self.NEST_BLOB2, self.BLOB_TEXT)
        self.impl.create_blob(self.QT_CONTAINER, self.NEST3_BLOB, self.BLOB_TEXT)

        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.NEST_BLOB)
        self.assertTrue(exists)

        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.NEST_BLOB2)
        self.assertTrue(exists)

        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.NEST3_BLOB)
        self.assertTrue(exists)

        # LIST BLOBS NESTED PATH
        blobs = self.impl.list_blobs(self.QT_CONTAINER, "foo/bar/ski")
        self.assertTrue(len(blobs) == 1)
        self.assertTrue(self.NEST3_BLOB in blobs)

        # LIST BLOBS RECURSIVE
        blobs = self.impl.list_blobs(self.QT_CONTAINER, "foo")
        self.assertTrue(len(blobs) == 3)
        self.assertTrue(not "foo/bar/" in blobs)
        self.assertTrue(self.NEST3_BLOB in blobs)

        # LIST BLOBS NON-RECURSIVE
        blobs = self.impl.list_blobs(self.QT_CONTAINER, "foo", recursive=False)
        self.assertTrue(len(blobs) == 3)
        self.assertTrue("foo/bar/" in blobs)
        self.assertTrue(self.NEST_BLOB in blobs)

        # LIST BLOBS RECURSIVE w/ PROPS
        blobs = self.impl.list_blobs(self.QT_CONTAINER, "foo", return_names=False)
        self.assertTrue(len(blobs) == 3)
        blob_names = [blob.name for blob in blobs]

        self.assertTrue(self.NEST3_BLOB in blob_names)
        self.assertTrue(self.NEST_BLOB in blob_names)
        props = blobs[0].properties

        self.assertTrue(props.content_length == len(self.BLOB_TEXT))
        self.assertTrue(isinstance(props.last_modified, datetime.datetime))

        # GET BLOB TEXT
        text = self.impl.get_blob_text(self.QT_CONTAINER, self.TEST_BLOB)
        self.assertTrue(text == self.BLOB_TEXT)

        # GET BLOB TO PATH
        self.impl.get_blob_to_path(self.QT_CONTAINER, self.TEST_BLOB, self.TEST_FILE)
        self.assertTrue(os.path.exists(self.TEST_FILE))

        # CREATE FROM PATH
        self.impl.create_blob_from_path(self.QT_CONTAINER, self.TEST_BLOB2, self.TEST_FILE)
        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.TEST_BLOB2)
        self.assertTrue(exists)

        # SNAPSHOT BLOB
        props = self.impl.snapshot_blob(self.QT_CONTAINER, self.TEST_BLOB2)
        self.assertTrue(hasattr(props, "snapshot"))
        
        # APPEND BLOB
        self.impl.append_blob(self.QT_CONTAINER, self.APPEND_BLOB, self.APPEND_TEXT)
        self.impl.append_blob(self.QT_CONTAINER, self.APPEND_BLOB, self.APPEND_TEXT)
        text = self.impl.get_blob_text(self.QT_CONTAINER, self.APPEND_BLOB)
        lines = text.split("\n")
        self.assertTrue(len(lines) >= 2)

        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.APPEND_BLOB)
        self.assertTrue(exists)

        blobs = self.impl.list_blobs(self.QT_CONTAINER)
        self.assertTrue(self.APPEND_BLOB in blobs)

        # GET BLOB PROPS
        result = self.impl.get_blob_properties(self.QT_CONTAINER, self.TEST_BLOB)
        self.assertTrue(result.properties.content_length == len(self.BLOB_TEXT))
        self.assertTrue(result.name == self.TEST_BLOB)

        # GET/SET BLOB METADATA
        md = self.impl.get_blob_metadata(self.QT_CONTAINER, self.TEST_BLOB)
        self.assertTrue(isinstance(md, dict))

        # COPY BLOB
        self.impl.copy_blob(self.QT_CONTAINER, self.TEST_BLOB, self.QT_CONTAINER, self.TEST_BLOB3)
        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.TEST_BLOB3)
        self.assertTrue(exists)

        # DELETE BLOB
        self.impl.delete_blob(self.QT_CONTAINER, self.TEST_BLOB)
        self.impl.delete_blob(self.QT_CONTAINER, self.APPEND_BLOB)
        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.TEST_BLOB)
        self.assertTrue(not exists)

        blobs = self.impl.list_blobs(self.QT_CONTAINER)
        self.assertTrue(not (self.TEST_BLOB in blobs))


class TestStorageProviderFileStorage(test_base.TestBase):

    def setup_class(cls):
        """
        Setup once for all tests
        """
        cls.TEST_DIR = "tests/storageProviderTests"
        cls.TEST_FILE = f"{cls.TEST_DIR}/test.txt"

        cls.QT_CONTAINER = "storage-provider-test"
        cls.TEST_CONTAINER = "storage-test-container"

        cls.TEST_BLOB = "__storage_test_blob__"
        cls.TEST_BLOB2 = "__storage_test_blob2__"
        cls.TEST_BLOB3 = "__storage_test_blob3__"
        cls.NEST_BLOB = "foo/blob1.txt"
        cls.NEST_BLOB2 = "foo/blob2.txt"
        cls.NEST3_BLOB = "foo/bar/ski/blob1.txt"
        cls.APPEND_BLOB = "__storage_test_append_blob__"

        cls.BLOB_TEXT = "this is the test blob!"
        cls.APPEND_TEXT = "this is the append text\n"

        cls.RETRY = 10

        cls.config = xt_config.get_merged_config()
        file_utils.ensure_dir_exists(cls.TEST_DIR)

        # get info about storage_name
        cls.storage_creds = cls.config.get_service("filestorage")
        cls.provider_name = cls.storage_creds["provider"]

        # create the provider class
        cls.impl_ctr = cls.config.get_provider_class_ctr("storage", cls.provider_name)
        cls.impl = cls.impl_ctr(cls.storage_creds)

        if cls.impl.does_container_exist(cls.QT_CONTAINER):
            cls.impl.delete_container(cls.QT_CONTAINER)

        cls.impl.create_container(cls.QT_CONTAINER)

    def teardown_class(cls):
        """
        Teardown once after all tests
        """
        cls.impl.delete_container(cls.QT_CONTAINER)
        shutil.rmtree(cls.TEST_DIR)

    def setup(self):
        """
        Setup per test
        """
        pass

    def teardown(self):
        """
        Teardown per test
        """
        pass

    def test_service(self):

        # set RETRY
        retry_func = utils.make_retry_func(self.RETRY)
        self.impl.set_retry(retry_func)

        # get RETRY
        returned_func = self.impl.get_retry()

        self.assertTrue(retry_func == returned_func)

    def test_container(self):
        '''
        tests out basic interface of storage provider. 

        Note: running this test multiple times can result in normal Azure retries due to
        the delay it imposes in creating a container after it has been deleted.
        '''

        # EXISTS
        exists = self.impl.does_container_exist(self.QT_CONTAINER)
        self.assertTrue(exists)

        # LIST CONTAINERS
        containers = self.impl.list_containers()
        self.assertTrue(self.QT_CONTAINER in containers)

        # CONTAINER EXISTS
        exists = self.impl.does_container_exist("no-such-container")
        self.assertTrue(not exists)

        exists = self.impl.does_container_exist(self.QT_CONTAINER)
        self.assertTrue(exists)

        # CREATE CONTAINER
        if self.impl.does_container_exist(self.TEST_CONTAINER):
            self.impl.delete_container(self.TEST_CONTAINER)

        self.impl.create_container(self.TEST_CONTAINER)
        containers = self.impl.list_containers()
        self.assertTrue(self.TEST_CONTAINER in containers)

        # DELETE CONTAINER
        self.impl.delete_container(self.TEST_CONTAINER)
        containers = self.impl.list_containers()
        self.assertTrue(not (self.TEST_CONTAINER in containers))

        # GET CONTAINER PROPS (Note: these will be specific to the provider)
        result = self.impl.get_container_properties(self.QT_CONTAINER)
        self.assertTrue(result)

        md = self.impl.get_container_metadata(self.QT_CONTAINER)
        self.assertTrue(isinstance(md, dict))

    def test_blob(self):
        # LIST BLOBS
        blobs = self.impl.list_blobs(self.QT_CONTAINER)
        self.assertTrue(isinstance(blobs, list))

        # BLOB EXISTS
        exists = self.impl.does_blob_exist(self.QT_CONTAINER, "__no_such_blob__")
        self.assertTrue(not exists)

        # CREATE BLOB
        self.impl.create_blob(self.QT_CONTAINER, self.TEST_BLOB, self.BLOB_TEXT)
        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.TEST_BLOB)
        self.assertTrue(exists)

        blobs = self.impl.list_blobs(self.QT_CONTAINER)
        self.assertTrue(self.TEST_BLOB in blobs)

        # CREATE BLOB - FAIL IF EXISTS
        got_failure = False

        # set retries to 0 
        retry_func = utils.make_retry_func(0)
        self.impl.set_retry(retry_func)

        try:
            self.impl.create_blob(self.QT_CONTAINER, self.TEST_BLOB, Bself.LOB_TEXT, fail_if_exists=True)
        except BaseException:
            got_failure = True

        self.assertTrue(got_failure)

        # CREATE BLOB - OK IF EXISTS
        self.impl.create_blob(self.QT_CONTAINER, self.TEST_BLOB, self.BLOB_TEXT, fail_if_exists=False)
        self.assertTrue(self.TEST_BLOB in blobs)

        # CREATE NESTED PATH BLOBS
        self.impl.create_blob(self.QT_CONTAINER, self.NEST_BLOB, self.BLOB_TEXT)
        self.impl.create_blob(self.QT_CONTAINER, self.NEST_BLOB2, self.BLOB_TEXT)
        self.impl.create_blob(self.QT_CONTAINER, self.NEST3_BLOB, self.BLOB_TEXT)

        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.NEST_BLOB)
        self.assertTrue(exists)

        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.NEST_BLOB2)
        self.assertTrue(exists)

        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.NEST3_BLOB)
        self.assertTrue(exists)

        # LIST BLOBS NESTED PATH
        blobs = self.impl.list_blobs(self.QT_CONTAINER, "foo/bar/ski")
        self.assertTrue(len(blobs) == 1)
        self.assertTrue(self.NEST3_BLOB in blobs)

        # LIST BLOBS RECURSIVE
        blobs = self.impl.list_blobs(self.QT_CONTAINER, "foo")
        self.assertTrue(len(blobs) == 3)
        self.assertTrue(not "foo/bar/" in blobs)
        self.assertTrue(self.NEST3_BLOB in blobs)

        # LIST BLOBS NON-RECURSIVE
        blobs = self.impl.list_blobs(self.QT_CONTAINER, "foo", recursive=False)
        self.assertTrue(len(blobs) == 3)
        self.assertTrue("foo/bar/" in blobs)
        self.assertTrue(self.NEST_BLOB in blobs)

        # LIST BLOBS RECURSIVE w/ PROPS
        blobs = self.impl.list_blobs(self.QT_CONTAINER, "foo", return_names=False)
        self.assertTrue(len(blobs) == 3)
        blob_names = [blob.name for blob in blobs]

        self.assertTrue(self.NEST3_BLOB in blob_names)
        self.assertTrue(self.NEST_BLOB in blob_names)
        props = blobs[0].properties

        self.assertTrue(props.content_length == len(self.BLOB_TEXT))
        self.assertTrue(isinstance(props.last_modified, datetime.datetime))

        # GET BLOB TEXT
        text = self.impl.get_blob_text(self.QT_CONTAINER, self.TEST_BLOB)
        self.assertTrue(text == self.BLOB_TEXT)

        # GET BLOB TO PATH
        self.impl.get_blob_to_path(self.QT_CONTAINER, self.TEST_BLOB, self.TEST_FILE)
        self.assertTrue(os.path.exists(self.TEST_FILE))

        # CREATE FROM PATH
        self.impl.create_blob_from_path(self.QT_CONTAINER, self.TEST_BLOB2, self.TEST_FILE)
        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.TEST_BLOB2)
        self.assertTrue(exists)

        # SNAPSHOT BLOB
        props = self.impl.snapshot_blob(self.QT_CONTAINER, self.TEST_BLOB2)
        self.assertTrue(hasattr(props, "snapshot"))
        
        # APPEND BLOB
        self.impl.append_blob(self.QT_CONTAINER, self.APPEND_BLOB, self.APPEND_TEXT)
        self.impl.append_blob(self.QT_CONTAINER, self.APPEND_BLOB, self.APPEND_TEXT)
        text = self.impl.get_blob_text(self.QT_CONTAINER, self.APPEND_BLOB)
        lines = text.split("\n")
        self.assertTrue(len(lines) >= 2)

        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.APPEND_BLOB)
        self.assertTrue(exists)

        blobs = self.impl.list_blobs(self.QT_CONTAINER)
        self.assertTrue(self.APPEND_BLOB in blobs)

        # GET BLOB PROPS
        result = self.impl.get_blob_properties(self.QT_CONTAINER, self.TEST_BLOB)
        self.assertTrue(result.properties.content_length == len(self.BLOB_TEXT))
        self.assertTrue(result.name == self.TEST_BLOB)

        # GET/SET BLOB METADATA
        md = self.impl.get_blob_metadata(self.QT_CONTAINER, self.TEST_BLOB)
        self.assertTrue(isinstance(md, dict))

        # COPY BLOB
        self.impl.copy_blob(self.QT_CONTAINER, self.TEST_BLOB, self.QT_CONTAINER, self.TEST_BLOB3)
        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.TEST_BLOB3)
        self.assertTrue(exists)

        # DELETE BLOB
        self.impl.delete_blob(self.QT_CONTAINER, self.TEST_BLOB)
        self.impl.delete_blob(self.QT_CONTAINER, self.APPEND_BLOB)
        exists = self.impl.does_blob_exist(self.QT_CONTAINER, self.TEST_BLOB)
        self.assertTrue(not exists)

        blobs = self.impl.list_blobs(self.QT_CONTAINER)
        self.assertTrue(not (self.TEST_BLOB in blobs))
