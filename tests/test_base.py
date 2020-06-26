from xtlib import console
import xtlib.xt_run as xt_run

class TestBase(object):

    def xt(self, cmd, capture_output=True):
        if capture_output:
            console.set_capture(True)
            xt_run.main(cmd)
            output = console.set_capture(False)
        else:
            xt_run.main(cmd)
            output = None

        return output

    def assertTrue(self, value):
        assert(value)

    def assert_keys(self, dictionary, keys):
        for key in keys:
            assert(key in dictionary)

    def assert_no_error_runs(self):
        text = self.xt("xt list runs --status=error", capture_output=True)        
        assert("no matching runs found" in text[0])
