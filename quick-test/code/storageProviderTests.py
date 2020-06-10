#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# storageProviderTests.py: test out storage interface (lowest level) of selected storage providers
import os
import datetime

from xtlib import utils
from xtlib import errors
from xtlib import file_utils
from xtlib.helpers import xt_config
from xtlib.helpers.dir_change import DirChange

TEST_DIR = "storageProviderTests"
TEST_FILE = "test.txt"

QT_CONTAINER = "storage-provider-test"
TEST_CONTAINER = "storage-test-container"

TEST_BLOB = "__storage_test_blob__"
TEST_BLOB2 = "__storage_test_blob2__"
TEST_BLOB3 = "__storage_test_blob3__"
NEST_BLOB = "foo/blob1.txt"
NEST_BLOB2 = "foo/blob2.txt"
NEST3_BLOB = "foo/bar/ski/blob1.txt"
APPEND_BLOB = "__storage_test_append_blob__"

BLOB_TEXT = "this is the test blob!"
APPEND_TEXT = "this is the append text\n"

RETRY = 10

class StorageProviderTests():
    def __init__(self):
        self.reset_count()

    def setup(self, impl):
        if impl.does_container_exist(QT_CONTAINER):
            impl.delete_container(QT_CONTAINER)

        impl.create_container(QT_CONTAINER)

    def teardown(self, impl):
        impl.delete_container(QT_CONTAINER)


    def reset_count(self):
        self._assert_count = 0

    def _assert(self, value):
        assert value
        self._assert_count  += 1

    def service_tests(self, impl):

        # set RETRY
        retry_func = utils.make_retry_func(RETRY)
        impl.set_retry(retry_func)

        # get RETRY
        returned_func = impl.get_retry()

        self._assert( retry_func == returned_func )

    def container_tests(self, impl):
        '''
        tests out basic interface of storage provider. 

        Note: running this test multiple times can result in normal Azure retries due to
        the delay it imposes in creating a container after it has been deleted.
        '''
        print("  starting CONTAINER tests")

        # EXISTS
        exists = impl.does_container_exist(QT_CONTAINER)
        self._assert( exists == True )

        # LIST CONTAINERS
        containers = impl.list_containers()
        self._assert( QT_CONTAINER in containers )

        # CONTAINER EXISTS
        exists = impl.does_container_exist("no-such-container")
        self._assert( exists == False )

        exists = impl.does_container_exist(QT_CONTAINER)
        self._assert( exists == True )

        # CREATE CONTAINER
        if impl.does_container_exist(TEST_CONTAINER):
            impl.delete_container(TEST_CONTAINER)

        impl.create_container(TEST_CONTAINER)
        containers = impl.list_containers()
        self._assert( TEST_CONTAINER in containers )

        # DELETE CONTAINER
        impl.delete_container(TEST_CONTAINER)
        containers = impl.list_containers()
        self._assert( not TEST_CONTAINER in containers )

        # GET CONTAINER PROPS (Note: these will be specific to the provider)
        result = impl.get_container_properties(QT_CONTAINER)
        self._assert( result )

        md = impl.get_container_metadata(QT_CONTAINER)
        assert isinstance(md, dict)

        print("  completed CONTAINER tests")

    def blob_tests(self, impl):
        print("  starting BLOB tests")

        # LIST BLOBS
        blobs = impl.list_blobs(QT_CONTAINER)
        self._assert( isinstance(blobs, list) )

        # BLOB EXISTS
        exists = impl.does_blob_exist(QT_CONTAINER, "__no_such_blob__")
        self._assert( exists == False )

        # CREATE BLOB
        impl.create_blob(QT_CONTAINER, TEST_BLOB, BLOB_TEXT)
        exists = impl.does_blob_exist(QT_CONTAINER, TEST_BLOB)
        self._assert( exists == True )

        blobs = impl.list_blobs(QT_CONTAINER)
        self._assert( TEST_BLOB in blobs )

        # CREATE BLOB - FAIL IF EXISTS
        got_failure = False

        # set retries to 0 
        retry_func = utils.make_retry_func(0)
        impl.set_retry(retry_func)

        try:
            impl.create_blob(QT_CONTAINER, TEST_BLOB, BLOB_TEXT, fail_if_exists=True)
        except BaseException:
            got_failure = True

        self._assert( got_failure )

        # CREATE BLOB - OK IF EXISTS
        impl.create_blob(QT_CONTAINER, TEST_BLOB, BLOB_TEXT, fail_if_exists=False)
        self._assert( TEST_BLOB in blobs )

        # CREATE NESTED PATH BLOBS
        impl.create_blob(QT_CONTAINER, NEST_BLOB, BLOB_TEXT)
        impl.create_blob(QT_CONTAINER, NEST_BLOB2, BLOB_TEXT)
        impl.create_blob(QT_CONTAINER, NEST3_BLOB, BLOB_TEXT)

        exists = impl.does_blob_exist(QT_CONTAINER, NEST_BLOB)
        self._assert( exists == True )

        exists = impl.does_blob_exist(QT_CONTAINER, NEST_BLOB2)
        self._assert( exists == True )

        exists = impl.does_blob_exist(QT_CONTAINER, NEST3_BLOB)
        self._assert( exists == True )

        # LIST BLOBS NESTED PATH
        blobs = impl.list_blobs(QT_CONTAINER, "foo/bar/ski")
        self._assert( len(blobs) == 1 )
        self._assert( NEST3_BLOB in blobs )

        # LIST BLOBS RECURSIVE
        blobs = impl.list_blobs(QT_CONTAINER, "foo")
        self._assert( len(blobs) == 3 )
        self._assert( not "foo/bar/" in blobs )
        self._assert( NEST3_BLOB in blobs )

        # LIST BLOBS NON-RECURSIVE
        blobs = impl.list_blobs(QT_CONTAINER, "foo", recursive=False)
        self._assert( len(blobs) == 3 )
        self._assert( "foo/bar/" in blobs )
        self._assert( NEST_BLOB in blobs )

        # LIST BLOBS RECURSIVE w/ PROPS
        blobs = impl.list_blobs(QT_CONTAINER, "foo", return_names=False)
        self._assert( len(blobs) == 3 )
        blob_names = [blob.name for blob in blobs]

        self._assert( NEST3_BLOB in blob_names )
        self._assert( NEST_BLOB in blob_names )
        props = blobs[0].properties

        self._assert( props.content_length == len(BLOB_TEXT) )
        self._assert( isinstance(props.last_modified, datetime.datetime ) )

        # GET BLOB TEXT
        text = impl.get_blob_text(QT_CONTAINER, TEST_BLOB)
        self._assert( text == BLOB_TEXT )

        # GET BLOB TO PATH
        impl.get_blob_to_path(QT_CONTAINER, TEST_BLOB, TEST_FILE)
        self._assert( os.path.exists(TEST_FILE) )

        # CREATE FROM PATH
        impl.create_blob_from_path(QT_CONTAINER, TEST_BLOB2, TEST_FILE)
        exists = impl.does_blob_exist(QT_CONTAINER, TEST_BLOB2)
        self._assert( exists == True )

        # SNAPSHOT BLOB
        props = impl.snapshot_blob(QT_CONTAINER, TEST_BLOB2)
        self._assert( hasattr(props, "snapshot") )
        
        # APPEND BLOB
        impl.append_blob(QT_CONTAINER, APPEND_BLOB, APPEND_TEXT)
        impl.append_blob(QT_CONTAINER, APPEND_BLOB, APPEND_TEXT)
        text = impl.get_blob_text(QT_CONTAINER, APPEND_BLOB)
        lines = text.split("\n")
        self._assert( len(lines) >= 2 )

        exists = impl.does_blob_exist(QT_CONTAINER, APPEND_BLOB)
        self._assert( exists == True )

        blobs = impl.list_blobs(QT_CONTAINER)
        self._assert( APPEND_BLOB in blobs )

        # GET BLOB PROPS
        result = impl.get_blob_properties(QT_CONTAINER, TEST_BLOB)
        self._assert( result.properties.content_length == len(BLOB_TEXT) )
        self._assert( result.name == TEST_BLOB )

        # GET/SET BLOB METADATA
        md = impl.get_blob_metadata(QT_CONTAINER, TEST_BLOB)
        self._assert( isinstance(md, dict) )

        # COPY BLOB
        impl.copy_blob(QT_CONTAINER, TEST_BLOB, QT_CONTAINER, TEST_BLOB3)
        exists = impl.does_blob_exist(QT_CONTAINER, TEST_BLOB3)
        self._assert( exists == True )

        # DELETE BLOB
        impl.delete_blob(QT_CONTAINER, TEST_BLOB)
        impl.delete_blob(QT_CONTAINER, APPEND_BLOB)
        exists = impl.does_blob_exist(QT_CONTAINER, TEST_BLOB)
        self._assert( exists == False )

        blobs = impl.list_blobs(QT_CONTAINER)
        self._assert( not TEST_BLOB in blobs )

        print("  completed BLOB tests")

    def test_impl(self, storage_name):
        print("testing: " + storage_name)

        config = xt_config.get_merged_config()

        # get info about storage_name
        storage_creds = config.get_service(storage_name)
        provider_name = storage_creds["provider"]

        # create the provider class
        impl_ctr = config.get_provider_class_ctr("storage", provider_name)
        impl = impl_ctr(storage_creds)

        # Setup
        self.setup(impl)

        # run test on impl
        self.service_tests(impl)
        self.container_tests(impl)
        self.blob_tests(impl)

        # Teardown
        self.teardown(impl)

def main():
    # init environment
    config = xt_config.get_merged_config()
    file_utils.ensure_dir_exists(TEST_DIR)

    with DirChange(TEST_DIR):
        tester = StorageProviderTests()

        tester.test_impl("xtsandboxstorage")
        tester.test_impl("filestorage")
    
    file_utils.ensure_dir_deleted(TEST_DIR)
    return tester._assert_count

# MAIN
if __name__ == "__main__":
    main()
