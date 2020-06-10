#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# tagTests.py: test out tag-related commands

import os
import time

from test_base import TestBase

class TagTests(TestBase):
    def __init__(self):
        return super(TagTests, self).__init__("TagTests")

    def set_tags_test(self, names):

        for name in names:
            self.test_cmd('''xt set tags {} urgent, priority=5, description="'test effect of 8 hidden layers'" '''.format(name))
            self.test_cmd('xt set tags {} funny, sad'.format(name))

    def clear_tags_test(self, names):
        for name in names:
            self.test_cmd('xt clear tags {} funny'.format(name))
            #self.test_cmd('xt clear tags run1428-run1429 sad')

    def list_tags_test(self, names):
        for name in names:
            #self.test_cmd('xt list tags job2740')

            output = self.test_cmd('xt list tags {}'.format(name))
            self.assert_names(output, ["description", "priority", "sad", "urgent"], "happy")
            
            #self.test_cmd('xt list tags run1428-run1429')

    def list_columns_test(self):
        self.test_cmd('xt list jobs job2741-job2751')


    def filter_tag_test(self):
        # NOTE: in these tests, job2748 is not defined and will be missing for
        # all list jobs commands

        # test basic PROPERTY FILTERS

        output = self.test_cmd('xt list jobs job2741-job2751 --filter={nodes==5}')
        # expected: job2742
        self.assert_names(output, "job2742", "job2471")

        output = self.test_cmd('xt list jobs job2741-job2751 --filter={nodes > 5}')
        # expected: job2741, job2743
        self.assert_names(output, ["job2741", "job2743"], "job2742")

        output = self.test_cmd('xt list jobs job2741-job2751 --filter={nodes != 5}')
        # expected: job2741-job2751 EXCEPT for job2742
        self.assert_names(output, ["job2741", "job2751"], "job2742")

        # test TAG FILTERS

        output = self.test_cmd('xt list jobs job2741-job2751 --filter={tags.urgent=$exists}')
        # expected: job2747
        self.assert_names(output, "job2747", "job2471")

        output = self.test_cmd('xt list jobs job2741-job2751 --filter={tags.urgent!=$exists}')
        # expected: job2741-job2751 EXCEPT for job2747
        # BUG: the above command mistakenly returns ALL 11 jobs (MongoDB or XT?)
        #self.assert_names(output, ["job2741", "job2751"], "job2747")

        # :regex: (regular expressions)
        output = self.test_cmd('xt list jobs job2741-job2751 --filter={tags.description:regex:.*hidden.*}')
        # expected: job2747
        self.assert_names(output, "job2747", "job2471")

        output = self.test_cmd('xt list jobs job2741-job2751 --filter={tags.description:regex:.*hiDxDen.*}')
        # expected: <no matching jobs>
        self.assert_names(output, "no matching jobs")

        output = self.test_cmd('xt list jobs job2741-job2751 --filter={tags.description:regex:^(.*hidden.*}')
        # expected: <no matching jobs>
        self.assert_names(output, "no matching jobs")

        # this is busted on Azure Mongodb
        output = self.test_cmd('xt list jobs job2741-job2751 --filter={tags.description:regex:/.*hiDDen.*/i}')
        # expected: job2747
        # BUG: the above command mistakenly returns ALL 11 jobs (MongoDB or XT?)
        #self.assert_names(output, "job2747", "job2471")

        # :exists: (test for property existence)
        output = self.test_cmd('xt list jobs job2741-job2751 --filter={tags.urgent:exists:true}')
        # expected: job2747
        self.assert_names(output, "job2747", "job2471")

        output = self.test_cmd('xt list jobs job2741-job2751 --filter={tags.urgent:exists:false}')
        # expected: job2741-job2751 EXCEPT for job2747
        self.assert_names(output, ["job2741", "job2751"], "job2747")

        output = self.test_cmd('xt list jobs job2741-job2751 --tags-all={urgent, nodes}')
        # expected: <no matching jobs>
        self.assert_names(output, "no matching jobs")

        output = self.test_cmd('xt list jobs job2741-job2751 --tags-any={urgent, nodes}')
        # expected: job2747
        # BUG: the above command mistakenly <no matching jobs> (MongoDB or XT?)
        #self.assert_names(output, "job2747", "job2471")

        # :mongo: (specify any mongo filter expression)
        
        # NOTE: turn these off for now since they rely on {} and back quote chars
        # self.test_cmd('xt list jobs job2741-job2751 --filter="nodes:mongo:{`$gt`:5}"')
        # self.test_cmd('xt list jobs job2741-job2751 --filter="tags.urgent:mongo:{`$exists`:false}"')
        # self.test_cmd('xt list jobs job1-job2751 --filter="foo:mongo:{`$regex`:`.*foo.*`}"')

    def run_tests(self, names):
        self.set_tags_test(names)
        self.clear_tags_test(names)
        self.list_tags_test(names)
        
        # list_columns_test()
        self.filter_tag_test()

        print("tag tests completed: cmds executed={}, asserts tested={}".format(self.cmd_count, self.assert_count))
        return self.cmd_count + self.assert_count

def main(philly=True):
    job  = "job2747"
    run = "run2"
    names = [job, run]

    tt = TagTests()
    count = tt.run_tests(names)

    return count

if __name__ == "__main__":
    main()
