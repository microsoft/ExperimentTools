class TestBase(object):

    def assert_keys(self, dictionary, keys):
        for key in keys:
            assert(key in dictionary)
