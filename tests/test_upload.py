import os
import time
import shutil

from xtlib import utils
from xtlib import constants
from xtlib import file_utils
import xtlib.xt_cmds as xt_cmds
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
        cls.testing_dir = "upload_testing"

        file_utils.ensure_dir_clean(cls.testing_dir)

        # generate some files
        generate(3, ".py", f"{cls.testing_dir}/")
        generate(2, ".txt", f"{cls.testing_dir}/")
        generate(3, ".py", f"{cls.testing_dir}/myapps/")
        generate(2, ".txt", f"{cls.testing_dir}/myapps/")
        xt_cmds.main("xt create share sharetest")

    def teardown_class(cls):
        """
        Teardown once after all tests
        """
        xt_cmds.main("xt delete share sharetest --response sharetest")
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

    def test_single_blob(self):

        # blob, single, optional, enabled, found
        xt_cmds.main(f"xt upload {self.testing_dir}/test1.py --share=sharetest")

        # blob, single, optional, enabled, not found
        #xt_cmds.main("xt upload test1.pyxx")

        # blob, single, optional, disabled, found
        xt_cmds.main(f"xt upload {self.testing_dir}/test1.py --share=sharetest --feedback=false")

        # blob, single, specified, enabled, found
        xt_cmds.main(f"xt upload {self.testing_dir}/test1.py foo.py --share=sharetest")

        # PASS: dest=DOUBLE path
        xt_cmds.main(f"xt upload {self.testing_dir}/test1.py maindir/subdir/test1.py --share=sharetest")

        # PASS: dest=PARENT path
        xt_cmds.main(f"xt upload {self.testing_dir}/test1.py __ws__/parent.txt --share=sharetest")
        
        # PASS: dest=GLOBAL
        xt_cmds.main(f"xt upload {self.testing_dir}/test1.py /{constants.INFO_CONTAINER}/jobs/job1000/global_single.txt --share=sharetest")
        

    # ---- MULTIPLE BLOBS ----
    def test_multiple_blobs(self):
        # blob, multi, not specifed, enabled, found
        xt_cmds.main(f"xt upload {self.testing_dir}/*.py --share=sharetest")

        # blob, multi, specifed, enabled, found
        xt_cmds.main(f"xt upload {self.testing_dir}/*.py mypy --share=sharetest")

        # PASS: dest=DOUBLE path
        xt_cmds.main(f"xt upload {self.testing_dir}/myapps maindir/subdir --share=sharetest")

        # PASS: dest=PARENT path
        xt_cmds.main(f"xt upload {self.testing_dir}/*.py __ws__ --share=sharetest")
        
        # PASS: source=named, dest=PARENT 
        xt_cmds.main(f"xt upload {self.testing_dir}/myapps __ws__ --share=sharetest")

        # PASS: dest=GLOBAL
        xt_cmds.main(f"xt upload {self.testing_dir}/*.txt /{constants.INFO_CONTAINER}/jobs/job1000 --share=sharetest")
        
        # PASS: source=RECURSIVE, dest=named
        xt_cmds.main(f"xt upload {self.testing_dir}/myapps/** foo --share=sharetest")
