class TestBase(object):

    def assertTrue(self, value):
        assert(value)

    def assert_keys(self, dictionary, keys):
        for key in keys:
            assert(key in dictionary)
