#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# plotTests.py: test various argument/option combinations for the plot command
import os
import datetime
import numpy as np

from xtlib import utils
from xtlib import errors
from xtlib import file_utils
from xtlib.helpers import xt_config
import xtlib.xt_cmds as xt_cmds

class PlotTests():
    def __init__(self, config, seed):
        self.config = config
        self.cmd_count = 0
        self._assert_count = 0
        self.random = np.random.RandomState(seed)

    def test_cmd(self, cmd):
        print("-----------------------")
        print("plotTests: testing ({}/{}): {}".format(1+self.cmd_count, self.count, cmd))

        xt_cmds.main(cmd)
        self.cmd_count += 1  

    def _assert(self, value):
        assert value
        self._assert_count  += 1

    def get_runs(self):
        # run names, run ranges, run wildcards, job names, job ranges, exper names
        values = ["run4385.1", "run4385.1, run4385.2, run4385.3", "run4385.1-run4385.5", "job6957", "mini21"]

        runs = self.random.choice(values)
        return runs

    def get_cols(self):
        values = ["", "train-acc", "train-acc, test-acc", "train-loss, train-acc, test-loss, test-acc"]

        cols = self.random.choice(values)
        return cols

    def get_layout(self):
        values = ["", "1x", "2x", "3x", "x1", "x2", "x3", "4x6"]

        layout = self.random.choice(values)
        if layout:
            layout = " --layout=" + layout

        return layout

    def get_break_on(self):
        values = ["", "run", "group", "col", "run, col", "group, col", "col, group", "col, run"]

        break_on = self.random.choice(values)
        if break_on:
            break_on = " --break-on=" + break_on

        return break_on

    def get_agg(self):
        values = ["", "", "mean", "min", "max", "std", "var", "sem"]

        agg = self.random.choice(values)
        if agg:
            agg = " --aggregate=" + agg

        return agg

    def get_group(self):
        values = ["", "", "exper", "job", "node", "run"]

        group = self.random.choice(values)
        if group:
            group = " --group-by=" + group

        return group

    def get_error_bars(self):
        values = ["", "none", "std", "var", "sem"]

        eb = self.random.choice(values)
        if eb != "":
            eb = " --error-bars=" + str(eb)

        return eb

    def get_title(self):
        values = ["", "x", "'this is a much longer title that you thought, huh?'"]

        title = self.random.choice(values)
        if title:
            title = " --title=" + title

        return title

    def get_smooth(self):
        values = ["", 0, .1, .95, .99, 1]

        smooth = self.random.choice(values)
        if smooth != "":
            smooth = " --smoothing-factor=" + str(smooth)

        return smooth

    def test_all(self, count):
        self.count = count

        for i in range(count):
            runs = self.get_runs()
            cols = self.get_cols()
            layout = self.get_layout()
            break_on = self.get_break_on()
            agg = self.get_agg()
            group = self.get_group()
            error_bars = self.get_error_bars()
            title = self.get_title()
            smooth = self.get_smooth()

            # x, range-type, plot-type

            cmd = "xt plot {} {}{}{}{}{}{}{}{}  --max-runs=9 --workspace=ws1 --show-plot=False ".format(runs, cols, layout, break_on, agg, group, 
                error_bars, title, smooth)

            self.test_cmd(cmd)

def main():
    # init environment
    seed = 24
    count = 20

    config = xt_config.get_merged_config()

    tester = PlotTests(config, seed)
    tester.test_all(count)

    return tester._assert_count

# MAIN
if __name__ == "__main__":
    main()
