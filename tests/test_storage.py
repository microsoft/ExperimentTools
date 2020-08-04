import os
import time
import shutil

from xtlib import utils
from xtlib import constants
from xtlib import file_utils
import xtlib.xt_cmds as xt_cmds
from xtlib import console
import xtlib.xt_run as xt_run
import test_base


def generate(count, ext, subdir):
    texts = ["", "this is a test", "how about that?\nthis is a 2nd line\nthis is 3rd", "huh"]

    for i in range(count):
        fn = subdir + "test" + str(i) + ext
        file_utils.ensure_dir_exists(file=fn)

        with open(fn, "wt") as outfile:
            text = texts[i % 4]
            outfile.write(text)


class TestUpload(test_base.TestBase):

    def setup_class(cls):
        """
        Setup once for all tests
        """
        cls.started = time.time()
        cls.upload_testing_dir = "upload_testing"
        cls.download_testing_dir = "download_testing"

        if os.environ.get("PHILLY_TESTS") == "true":
            cls.share_name = "sharetestphilly"
        else:
            cls.share_name = "sharetest"

        file_utils.ensure_dir_clean(cls.upload_testing_dir)
        file_utils.ensure_dir_clean(cls.download_testing_dir)

        # generate some files
        generate(3, ".py", f"{cls.upload_testing_dir}/")
        generate(2, ".txt", f"{cls.upload_testing_dir}/")
        generate(3, ".py", f"{cls.upload_testing_dir}/myapps/")
        generate(2, ".txt", f"{cls.upload_testing_dir}/myapps/")
        console.set_capture(True)
        xt_run.main("xt list shares")
        result = console.set_capture(False)
        matching = list(filter(lambda entry: entry.find(cls.share_name) != -1, result))
        if matching:
            xt_run.main(f"xt delete share {cls.share_name} --response={cls.share_name}")
            time.sleep(5)

        xt_run.main(f"xt create share {cls.share_name}")

    def teardown_class(cls):
        """
        Teardown once after all tests
        """
        xt_run.main(f"xt delete share {cls.share_name} --response {cls.share_name}")
        elapsed = time.time() - cls.started
        print("\nend of uploadTests, elapsed={:.0f} secs".format(elapsed))

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

    def dir_blobs(self):
        # PASS: blob, no name, subdir=0, --work, no path
        xt_cmds.main("xt list blobs")

        # PASS: blob, name, subdir=0, --work, rel path
        xt_cmds.main("xt list blobs myapps")

        # PASS: blob, wildcard, subdir=0, --work, rel-path
        xt_cmds.main("xt list blobs myapps/test*.py")

        # PASS: blob, no name, subdir=0, --work, global-path
        xt_cmds.main("xt list blobs /quick-test")

        # PASS blob, no name, subdir=0, --work, root-path
        xt_cmds.main("xt list blobs /")

        # PASS: blob, no name, subdir=0, --work, parent-path
        xt_cmds.main("xt list blobs ../")
        xt_cmds.main("xt list blobs ../runs")
        xt_cmds.main("xt list blobs ../../../../")

        # PASS: blob, no name, subdir=*, --work, no path
        xt_cmds.main("xt list blobs /quick-test --subdir=0")
        xt_cmds.main("xt list blobs /quick-test --subdir=1")
        xt_cmds.main("xt list blobs /quick-test --subdir=-1")

        # PASS: blob, no name, subdir=*, --work/--run/--job/--exper, no path
        xt_cmds.main("xt list blobs --work=quick-test")
        xt_cmds.main("xt list blobs --exper=default-exper")
        xt_cmds.main("xt list blobs --run=run2.1")
        xt_cmds.main("xt list blobs --job=job1000")

    def download_single_blob(self):
        #test_cmd("xt list blobs")

        # blob, single, optional, enabled, found
        xt_cmds.main(f"xt download test1.py")

        # blob, single, optional, enabled, not found
        #xt_cmds.main("xt download test1.pyxx")

        # blob, single, optional, disabled, found
        xt_cmds.main(f"xt download test1.py --feedback=false")

        # blob, single, specified, enabled, found
        xt_cmds.main(f"xt download test1.py {self.download_testing_dir}/foo.py")

        # PASS: parent path into current dir
        xt_cmds.main(f"xt download ../__ws__/test1.py {self.download_testing_dir}/foo2.py")
        
        # PASS: parent path into specified dir
        xt_cmds.main(f"xt download ../__ws__/test1.py myfiles/foo2.py")

        # PASS: global path into current dir
        xt_cmds.main(f"xt download /{constants.INFO_CONTAINER}/__info__/next_job_number.control")

    def download_multiple_blobs(self):
        # blob, multi, not specifed, enabled, found
        xt_cmds.main(f"xt download *.py")

        # blob, multi, specifed, enabled, found
        #xt_cmds.main("xt download blobs *.py myapps")

        # PASS: reg path
        xt_cmds.main(f"xt download myapps")

        # PASS: parent path into current dir
        xt_cmds.main(f"xt download ../__ws__/maindir")
        
        # PASS: parent path into specified dir
        xt_cmds.main(f"xt download ../__ws__/maindir myfiles")

        # PASS: global path into current dir
        xt_cmds.main(f"xt download /{constants.INFO_CONTAINER}/__info__/*")
        
        # PASS: recursive into local unnamed relative dir
        xt_cmds.main(f"xt download maindir/**")
        
        # PASS: recursive into local named relative dir
        xt_cmds.main(f"xt download myapps/** {self.download_testing_dir}/foo")
            
        # PASS: recursive into local absolute path
        xt_cmds.main(f"xt download maindir/** {self.download_testing_dir}/xxx")
        file_utils.zap_dir(f"{self.download_testing_dir}/xxx")

    def test_single_blob(self):

        # blob, single, optional, enabled, found
        xt_cmds.main(f"xt upload {self.upload_testing_dir}/test1.py --share={self.share_name}")

        # blob, single, optional, enabled, not found
        #xt_cmds.main("xt upload test1.pyxx")

        # blob, single, optional, disabled, found
        xt_cmds.main(f"xt upload {self.upload_testing_dir}/test1.py --share={self.share_name} --feedback=false")

        # blob, single, specified, enabled, found
        xt_cmds.main(f"xt upload {self.upload_testing_dir}/test1.py foo.py --share={self.share_name}")

        # PASS: dest=DOUBLE path
        xt_cmds.main(f"xt upload {self.upload_testing_dir}/test1.py maindir/subdir/test1.py --share={self.share_name}")

        # PASS: dest=PARENT path
        xt_cmds.main(f"xt upload {self.upload_testing_dir}/test1.py __ws__/parent.txt --share={self.share_name}")
        
        # PASS: dest=GLOBAL
        xt_cmds.main(f"xt upload {self.upload_testing_dir}/test1.py /{constants.INFO_CONTAINER}/jobs/job1000/global_single.txt --share={self.share_name}")

        self.dir_blobs()
        self.download_single_blob()
        

    # ---- MULTIPLE BLOBS ----
    def test_multiple_blobs(self):
        # blob, multi, not specifed, enabled, found
        xt_cmds.main(f"xt upload {self.upload_testing_dir}/*.py --share={self.share_name}")

        # blob, multi, specifed, enabled, found
        xt_cmds.main(f"xt upload {self.upload_testing_dir}/*.py mypy --share={self.share_name}")

        # PASS: dest=DOUBLE path
        xt_cmds.main(f"xt upload {self.upload_testing_dir}/myapps maindir/subdir --share={self.share_name}")

        # PASS: dest=PARENT path
        xt_cmds.main(f"xt upload {self.upload_testing_dir}/*.py __ws__ --share={self.share_name}")
        
        # PASS: source=named, dest=PARENT 
        xt_cmds.main(f"xt upload {self.upload_testing_dir}/myapps __ws__ --share={self.share_name}")

        # PASS: dest=GLOBAL
        xt_cmds.main(f"xt upload {self.upload_testing_dir}/*.txt /{constants.INFO_CONTAINER}/jobs/job1000 --share={self.share_name}")
        
        # PASS: source=RECURSIVE, dest=named
        xt_cmds.main(f"xt upload {self.upload_testing_dir}/myapps/** foo --share={self.share_name}")

        self.dir_blobs()
        self.download_multiple_blobs()
