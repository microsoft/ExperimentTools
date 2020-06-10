#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# hyperex.py: multi-pane matplotlib-based GUI for exploring runs thru their hyperparameter settings

import time
import numpy as np

# on-demand import of matplotlib
plt = None
Rectangle = None
Button = None
RadioButtons = None

from xtlib.console import console
from xtlib import errors

RUN_COUNT_THRESHOLD = 0.

STD_DEV = 0
STD_ERR = 1
SEPARATE = 2
PLOT_STYLE_LABELS = ['Standard deviation', 'Standard error', 'Separate runs']

LEGEND_SIZE = 16
LEGEND_POSITION = 'lower left'

NUM_HIST_BINS = 64

MAX_NUM_RUNS = 0  # For throttling while debugging.


class PerformanceChart(object):
    def __init__(self, explorer, fig, plot_num_points, plot_min_x, plot_x_inc, ws_name,
                 run_group_type, run_group_name, plot_x_metric_name, plot_y_metric_name):
        self.explorer = explorer
        self.fig = fig
        self.plot_num_points = plot_num_points
        self.perf_axes = fig.add_axes([0.54, 0.05, 0.44, 0.92])
        self.prev_curve = None
        self.x_vals = np.zeros(plot_num_points)
        for i in range(plot_num_points):
            self.x_vals[i] = plot_min_x + i * plot_x_inc
        self.ws_name = ws_name
        self.run_group_type = run_group_type
        self.run_group_name = run_group_name
        self.plot_x_metric_name = plot_x_metric_name
        self.plot_y_metric_name = plot_y_metric_name
        self.plot_from_runs()

    def plot_from_runs(self):
        self.perf_axes.clear()
        self.perf_axes.set_title("Workspace={}  {}={}".format(self.ws_name, self.run_group_name.capitalize(), self.run_group_type), fontsize=16)
        self.perf_axes.set_xlabel("{}".format(self.plot_x_metric_name), fontsize=16)
        self.perf_axes.set_ylabel("{}".format(self.plot_y_metric_name), fontsize=16)
        self.perf_axes.set_xlim(self.explorer.plot_min_x, self.explorer.plot_max_x)
        self.perf_axes.set_ylim(self.explorer.plot_min_y, self.explorer.plot_max_y)

        # Gather the currently included runs into a list.
        included_runs = []
        for run in self.explorer.runs:
            if run.include:
                run.i_report = 0
                included_runs.append(run)
        num_runs = len(included_runs)

        if (self.explorer.plot_style == STD_DEV) or (self.explorer.plot_style == STD_ERR):
            # Display means with error bars.
            means = np.zeros(self.plot_num_points)
            error_bars = np.zeros(self.plot_num_points)
            if self.explorer.plot_style == STD_DEV:
                normalizer = 1.
            elif self.explorer.plot_style == STD_ERR:
                normalizer = num_runs

            # Use interpolation to handle missing values.
            for i in range(self.plot_num_points):
                total = 0.
                total2 = 0.
                num = 0
                for run in included_runs:
                    y = run.get_y_at_x(self.x_vals[i])
                    if y is not None:
                        total += y
                        total2 += y*y
                        num += 1
                mean = total / num
                mean2 = total2 / num
                var = mean2 - mean * mean
                means[i] = mean
                error_bars[i] = np.sqrt(var / normalizer)

            # Plot the curves.
            ymin = means - error_bars
            ymax = means + error_bars
            curve = PerfCurve(self.x_vals, means, ymin, ymax, num_runs)
            self.plot_error(curve, 'blue')
            self.plot_curve(curve, 'blue', label='Current set', alpha=1.)
            if self.prev_curve:
                self.plot_error(self.prev_curve, 'red')
                self.plot_curve(self.prev_curve, 'red', alpha=1., label='Previous set')
            self.perf_axes.legend(loc=LEGEND_POSITION, prop={'size': LEGEND_SIZE})
            self.prev_curve = curve
        else:
            # Display the runs separately.
            for run in included_runs:
                num_vals = len(run.metric_reports)
                x_vals = np.zeros(num_vals)
                y_vals = np.zeros(num_vals)
                for i in range(num_vals):
                    x_vals[i] = run.metric_reports[i].x
                    y_vals[i] = run.metric_reports[i].y
                curve = PerfCurve(x_vals, y_vals, 0, 0, 1)
                self.plot_curve(curve, 'blue', alpha=0.1, label='')

    def plot_error(self, curve, color):
        self.perf_axes.fill_between(curve.x_vals, curve.ymax, curve.ymin, color=color, alpha=0.2)

    def plot_curve(self, curve, color, alpha, label, include_runs=True):
        if include_runs:
            label += "  ({} runs)"
        self.perf_axes.plot(curve.x_vals, curve.y_means, label=(label.format(curve.num_runs)), color=color, alpha=alpha, linewidth=3)


class PerfCurve(object):
    def __init__(self, x_vals, y_means, ymin, ymax, num_runs):
        self.x_vals = x_vals
        self.y_means = y_means
        self.ymin = ymin
        self.ymax = ymax
        self.num_runs = num_runs


class HorizontalBar(object):
    def __init__(self, y, label, color, min_x, max_x):
        self.y = y
        self.label = label
        self.color = color
        self.plot_min_x = min_x
        self.plot_max_x = max_x
        self.plot_min_y = y
        self.plot_max_y = y

    def plot(self, perf_chart):
        d = np.zeros(2)
        d[0] = self.y
        d[1] = self.y

        x_vals = np.zeros(2)
        x_vals[0] = self.plot_min_x
        x_vals[1] = self.plot_max_x

        curve = PerfCurve(x_vals, d, d, d, 1)
        perf_chart.plot_curve(curve, self.color, alpha=1., label=self.label, include_runs=False)
        if (perf_chart.explorer.plot_style == STD_DEV) or (perf_chart.explorer.plot_style == STD_ERR):
            perf_chart.perf_axes.legend(loc=LEGEND_POSITION, prop={'size': LEGEND_SIZE})


class Histogram(object):
    def __init__(self, explorer, fig, id, num_ids, hist_x_metric_name):
        self.explorer = explorer
        self.fig = fig
        self.id = id
        self.num_ids = num_ids
        self.hist_x_metric_name = hist_x_metric_name
        self.axes = None
        self.values = []
        self.y_button_height = 0.018
        self.setting = None  # Always None for global hist. Changes for setting hists.
        self.visible = False

    def add_axes(self, axes_to_share):
        bottom_client_margin = 0.02  # So there's room at the bottom for a histogram title.
        top_hist_margin = 0.04  # To separate the histograms a bit.
        self.width = 0.23
        self.height = 1. / self.num_ids
        self.left_bound = 0.26
        self.bottom = bottom_client_margin + (self.num_ids - self.id - 1) * self.height
        self.height -= top_hist_margin
        if axes_to_share:
            self.axes = self.fig.add_axes([self.left_bound, self.bottom, self.width, self.height], sharex=axes_to_share)
        else:
            self.axes = self.fig.add_axes([self.left_bound, self.bottom, self.width, self.height])
        if self.id > 0:
            self.axes.get_xaxis().set_visible(False)
            self.axes.spines["right"].set_visible(False)
            self.axes.spines["top"].set_visible(False)
            self.init_button()
            self.set_visible(False)
        return self.axes

    def init_button(self):
        x_left_bound = self.left_bound
        x_width = self.width
        y_top = self.bottom
        self.button_axes = plt.axes([x_left_bound, y_top - self.y_button_height, x_width, self.y_button_height])
        self.button = Button(self.button_axes, "some text")
        self.button.label.set_fontsize(12)
        self.button.on_clicked(self.on_click)

    def set_visible(self, visible):
        self.axes.get_yaxis().set_visible(visible)
        self.axes.spines["left"].set_visible(visible)
        self.axes.spines["bottom"].set_visible(visible)
        self.button_axes.set_visible(visible)
        self.visible = visible

    def update(self):
        self.axes.clear()
        self.values = []

        if self.id == 0:
            # The global histogram.
            for run in self.explorer.runs:
                if run.include:
                    self.values.append(run.summary_val)
        else:
            # A per-setting histogram.
            hparam = self.explorer.current_hparam
            if hparam != None:
                num_settings = len(hparam.settings)
                if self.id <= num_settings:
                    self.setting = hparam.settings[self.id - 1]
                    self.set_visible(True)
                    if self.setting.include:
                        for run in self.explorer.runs:
                            if run.include:
                                if run.hparam_name_value_pairs[self.setting.hparam.name] == self.setting.value:
                                    self.values.append(run.summary_val)
                        self.button.label.set_text("{}  ({} runs)".format(self.setting.value, len(self.values)))
                        self.axes.set_facecolor('1.0')  # White
                        self.axes.get_yaxis().set_visible(True)
                    else:
                        # This setting is excluded. Show any runs that would be included if this setting were toggled.
                        for run in self.explorer.runs:
                            if run.num_settings_that_exclude_this == 1:
                                if run.hparam_name_value_pairs[self.setting.hparam.name] == self.setting.value:
                                    self.values.append(run.summary_val)
                        self.button.label.set_text("{}  ({} runs, excluded)".format(self.setting.value, len(self.values)))
                        self.axes.set_facecolor('0.9')  # Gray
                        self.axes.get_yaxis().set_visible(False)
                else:
                    # This histogram is not currently mapped to a setting.
                    self.axes.set_facecolor('1.0')
                    self.set_visible(False)
        if self.id == 0:
            color = 'b'
            self.axes.set_xlabel("{}".format(self.hist_x_metric_name), fontsize=14)
            self.axes.set_ylabel("Runs in set", fontsize=14)
        else:
            color = (0., 0.7, 0.)
        edgecolor = 'white' if self.values else None

        # Plot the histogram bins.
        self.axes.hist(self.values, bins=NUM_HIST_BINS, range=(self.explorer.hist_min_x, self.explorer.hist_max_x),
                       facecolor=color, edgecolor=edgecolor, zorder=2)

        if self.visible and (self.id > 0):
            if len(self.values) > 0:
                y = 0
                h = self.axes.viewLim.y1
                x = self.explorer.hist_min_x

                # Average
                tot = 0.
                for v in self.values:
                    tot += v
                mean_val = tot / len(self.values)
                w = mean_val - x

                # Plot the aggregate per-setting metric.
                if self.setting.include:
                    color = 'orange'
                else:
                    color = (0.9, 0.8, 0.6)
                rect = Rectangle((x,y), w, h,linewidth=1,edgecolor=color,facecolor=color, zorder=1)
                self.axes.add_patch(rect)

            # Plot the best runsets as small square marks.
            self.plot_best_runsets()

    def plot_best_runsets(self):
        canvas_x0 = self.axes._position.x0
        canvas_x1 = self.axes._position.x1
        canvas_y0 = self.axes._position.y0
        canvas_y1 = self.axes._position.y1

        x0_units = self.axes.viewLim.x0
        x1_units = self.axes.viewLim.x1
        y0_units = self.axes.viewLim.y0
        y1_units = self.axes.viewLim.y1

        x_units_per_pixel = (x1_units - x0_units) / (self.fig.bbox.bounds[2] * (canvas_x1 - canvas_x0))
        y_units_per_pixel = (y1_units - y0_units) / (self.fig.bbox.bounds[3] * (canvas_y1 - canvas_y0))

        count_y1 = self.explorer.max_runs_per_runset + 1
        count_y0 = RUN_COUNT_THRESHOLD
        count_scale = (y1_units - y0_units) / (count_y1 - count_y0)

        mark_size = 5.  # pixels
        mark_dx = mark_size * x_units_per_pixel
        mark_dy = mark_size * y_units_per_pixel
        metric_offset = mark_size * x_units_per_pixel / 2.
        count_offset = mark_size * y_units_per_pixel / 2.

        hparam = self.explorer.current_hparam
        if hparam != None:
            num_settings = len(hparam.settings)
            if self.id <= num_settings:
                self.setting = hparam.settings[self.id - 1]
                for runset in self.explorer.configstring_runset_dict.values():
                    if runset.runs[0].hparam_name_value_pairs[self.setting.hparam.name] == self.setting.value:
                        if runset.count > count_y0:
                            # if runset.count > y1_units:
                            #     assert runset.count <= y1_units
                            if runset.metric > x1_units:
                                assert runset.metric <= x1_units
                            count_norm = (runset.count - count_y0) * count_scale - y0_units
                            rect = Rectangle((runset.metric - metric_offset, count_norm - count_offset), mark_dx, mark_dy,
                                              linewidth=1, edgecolor='black', facecolor='black', zorder=3)
                            self.axes.add_patch(rect)

    def on_click(self, event):
        self.setting.include = not self.setting.include
        self.explorer.update_runs()


class MetricReport(object):
    def __init__(self, run_record, plot_x_metric_name, plot_y_metric_name):
        metric_dict = run_record["data"]
        if not plot_x_metric_name in metric_dict:
            errors.combo_error("step name hyperparameter '{}' (named in XT config file) not found in hp search file".format(plot_x_metric_name))
        if not plot_y_metric_name in metric_dict:
            errors.combo_error("primary_metric hyperparameter '{}' (named in XT config file) not found in hp search file".format(plot_y_metric_name))
        self.x = int(metric_dict[plot_x_metric_name])
        self.y = float(metric_dict[plot_y_metric_name])


class RunSet(object):
    def __init__(self, configuration_string):
        self.configuration_string = configuration_string
        self.runs = []
        self.count = None
        self.metric = None


class Run(object):
    def __init__(self, run_record, plot_x_metric_name, plot_y_metric_name, hist_x_metric_name):
        self.hparam_name_value_pairs = {}
        self.settings = []
        self.configuration_string = ''
        self.include = True
        self.num_settings_that_exclude_this = 0
        self.interval = 1  # Index to the metric report at the end of the current interpolation interval.
        self.metric_reports = []
        self.summary_val = 0.
        self.num_values_summarized = 0
        log_records = run_record['log_records']
        for log_record in log_records:
            event = log_record["event"]
            if event == "hparams":
                hparam_dict = log_record["data"]
                for key in hparam_dict:
                    self.hparam_name_value_pairs[key] = hparam_dict[key]
            elif event == "metrics":
                # The following metric names may or may not be identical.
                if plot_y_metric_name in log_record["data"]:
                    # Keep plot_y_metric_name values in metric reports for plotting curves.
                    metric_report = MetricReport(log_record, plot_x_metric_name, plot_y_metric_name)
                    self.metric_reports.append(metric_report)
                if hist_x_metric_name in log_record["data"]:
                    # Average hist_x_metric_name values to produce summary_val.
                    self.summary_val += float(log_record["data"][hist_x_metric_name])
                    self.num_values_summarized += 1
        if self.num_values_summarized > 0:
            self.summary_val /= self.num_values_summarized

    def get_y_at_x(self, x):
        # Interpolate.
        if (x < self.metric_reports[0].x) or (x > self.metric_reports[-1].x):
            return None
        if x == self.metric_reports[0].x:
            return self.metric_reports[0].y
        if self.metric_reports[self.interval-1].x > x:
            self.interval = 1
        i = self.interval
        while self.metric_reports[i].x < x:
            i += 1
        self.interval = i
        a = self.metric_reports[i-1]
        b = self.metric_reports[i]
        return a.y + (b.y - a.y) * (x - a.x) / (b.x - a.x)

    def update_inclusion(self):
        self.include = True
        self.num_settings_that_exclude_this = 0
        for setting in self.settings:
            if not setting.include:
                self.include = False
                self.num_settings_that_exclude_this += 1


class HyperparameterSetting(object):
    def __init__(self, explorer, hparam, id, value, include):
        self.explorer = explorer
        self.hparam = hparam
        self.id = id
        self.value = value
        self.include = include


class Hyperparameter(object):
    def __init__(self, explorer, fig, name):
        self.explorer = explorer
        self.fig = fig
        self.name = name
        self.id = -1
        self.value_setting_dict = {}
        self.settings = []
        self.single_value = None
        self.display = False

    def add_setting(self, setting_value, include):
        if setting_value not in self.value_setting_dict.keys():
            setting = HyperparameterSetting(self.explorer, self, 0, setting_value, include)
            self.value_setting_dict[setting_value] = setting
        setting = self.value_setting_dict[setting_value]
        self.single_value = setting_value
        return setting

    def init_button(self):
        x_left_bound = 0.015
        x_width = 0.2
        y_top_bound = 0.08
        y_spacing = 0.06
        y_button_height = 0.04
        self.button_axes = plt.axes([x_left_bound, 1.0 - y_top_bound - self.id * y_spacing, x_width, y_button_height])
        self.button = Button(self.button_axes, self.name)
        self.button.label.set_fontsize(18)
        self.button.on_clicked(self.on_click)

    def on_click(self, event):
        if self.explorer.current_hparam != self:
            self.explorer.set_current_hparam(self)
            self.explorer.update_histograms()
            self.fig.canvas.draw()


class HyperparameterExplorer(object):
    def __init__(self, store, ws_name, run_group_type, run_group_name,
                 hp_config_cloud_path, hp_config_local_dir, plot_x_metric_name, plot_y_metric_name, hist_x_metric_name):
        # on-demand import (since reference causes fonts to rebuild cache...)
        global plt, Rectangle, Button, RadioButtons
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        from matplotlib.widgets import Button
        from matplotlib.widgets import RadioButtons

        # Initialize the graphics.
        self.fig = plt.figure(figsize=(20,12))
        self.fig.canvas.set_window_title('Hyperparameter Explorer')
        self.left_pane_axes = self.fig.add_axes([0.0, 0.0, 1.0, 1.0])
        self.left_pane_axes.get_xaxis().set_visible(False)
        self.left_pane_axes.get_yaxis().set_visible(False)
        self.left_pane_axes.spines["left"].set_visible(False)
        self.left_pane_axes.spines["right"].set_visible(False)
        self.left_pane_axes.spines["top"].set_visible(False)
        self.left_pane_axes.spines["bottom"].set_visible(False)
        self.plot_style = STD_DEV
        self.radio_buttons_axes = self.fig.add_axes([0.83, 0.07, 0.14, 0.1])
        self.radio_buttons = RadioButtons(self.radio_buttons_axes, (PLOT_STYLE_LABELS[0], PLOT_STYLE_LABELS[1], PLOT_STYLE_LABELS[2]))
        self.radio_buttons_axes.set_zorder(20)
        self.radio_buttons.on_clicked(self.radio_buttons_on_clicked)

        # Get the data.
        local_config_file_path, all_run_records = self.download_runs(store, ws_name, run_group_name, run_group_type, hp_config_cloud_path, hp_config_local_dir)

        # Handle the hyperparameters.
        self.hparams = []
        self.set_current_hparam(None)
        self.define_hyperparameters(local_config_file_path)  # Get the superset of hparam definitions.
        self.load_runs(all_run_records, plot_x_metric_name, plot_y_metric_name, hist_x_metric_name)  # Populate the run objects with some data.
        self.get_plot_bounds_from_runs()
        self.populate_hparams()

        # Assemble runsets.
        self.configstring_runset_dict = {}
        self.group_runs_into_runsets()
        for run in self.runs:
            run.update_inclusion()  # This takes into consideration any non-included settings.

        # Left pane.
        self.assemble_left_pane()
        self.create_hparam_border()

        # Center pane.
        # Create a fixed set of histogram objects to be reused for all settings.
        # The first (top) histogram is the aggregate for all settings (in the focus).
        self.hists = []
        for i in range(self.max_settings_per_hparam + 1):
            self.hists.append(Histogram(self, self.fig, i, self.max_settings_per_hparam + 1, hist_x_metric_name))
        axes_to_share = self.hists[self.max_settings_per_hparam].add_axes(None)
        for i in range(self.max_settings_per_hparam):
            self.hists[self.max_settings_per_hparam - i - 1].add_axes(axes_to_share)
        self.update_histograms()

        # Right pane.
        self.perf = PerformanceChart(self, self.fig, self.plot_num_points, self.plot_min_x, self.plot_x_inc,
                                     ws_name, run_group_type, run_group_name, plot_x_metric_name, plot_y_metric_name)

    def download_runs(self, store, ws_name, run_group_name, run_group_type, hp_config_cloud_path, hp_config_local_dir):
        # Download the all_runs file
        local_cache_path = "{}/{}/{}/".format(hp_config_local_dir, ws_name, run_group_type)
        local_config_file_path = "{}{}".format(local_cache_path, "hp-config.yaml")

        if run_group_name == "experiment":
            console.print("downloading runs for EXPERIMENT={}...".format(run_group_type))
            # files are at EXPERIMENT LEVEL
            # read SWEEPS file
            if not store.does_experiment_file_exist(ws_name, run_group_type, hp_config_cloud_path):
                errors.store_error("missing experiment hp_config file (ws={}, exper={}, fn={})".format(ws_name,
                                                                                                       run_group_type, hp_config_cloud_path))
            store.download_file_from_experiment(ws_name, run_group_type, hp_config_cloud_path, local_config_file_path)

            # read ALLRUNS info aggregated in EXPERIMENT
            allrun_records = store.get_all_runs(run_group_name, ws_name, run_group_type)
        else:
            console.print("downloading runs for JOB={}...".format(run_group_type))
            # files are at JOB LEVEL
            # read SWEEPS file
            if not store.does_job_file_exist(run_group_type, hp_config_cloud_path):
                errors.store_error("missing job hp_config file (job={}, fn={})".format(run_group_type, hp_config_cloud_path))
            store.download_file_from_job(run_group_type, hp_config_cloud_path, local_config_file_path)

            # read ALLRUNS info aggregated in JOB
            allrun_records = store.get_all_runs(run_group_name, ws_name, run_group_type)

        console.diag("after downloading all runs")
        return local_config_file_path, allrun_records

    def radio_buttons_on_clicked(self, label):
        if label == PLOT_STYLE_LABELS[self.plot_style]:
            return
        if label == PLOT_STYLE_LABELS[0]:
            self.plot_style = 0
        elif label == PLOT_STYLE_LABELS[1]:
            self.plot_style = 1
        elif label == PLOT_STYLE_LABELS[2]:
            self.plot_style = 2
        self.perf.prev_curve = None
        self.perf.plot_from_runs()
        self.fig.canvas.draw()

    def draw(self):
        self.hist.draw()

    def create_hparam_border(self):
        if len(self.name_hparam_dict) > 0:
            if len(self.displayed_hparams) > 0:
                rect = self.displayed_hparams[0].button_axes.get_position()
                xm = 0.004
                ym = 0.006
                x = rect.x0 - xm
                y = 2.0
                w = (rect.x1 - rect.x0) + 2*xm
                h = (rect.y1 - rect.y0) + 2*ym
                rectangle = Rectangle((x, y), w, h, linewidth=4, edgecolor='g', facecolor='none')
                self.hparam_border = self.left_pane_axes.add_patch(rectangle)

    def add_hparam(self, hparam):
        self.hparams.append(hparam)

    def set_current_hparam(self, hparam):
        self.current_hparam = hparam
        if hparam != None:
            rect = hparam.button_axes.get_position()
            xm = 0.004
            ym = 0.006
            x = rect.x0 - xm
            y = rect.y0 - ym
            self.hparam_border.set_xy([x, y])

    def run(self, timeout=None):
        if len(self.runs) == 0:
            console.print("error - no valid runs found")
            return

        if timeout:
            # build a thread to close our plot window after specified time
            from threading import Thread

            def set_timer(timeout):
                console.print("set_timer called: timeout=", timeout)
                time.sleep(timeout)
                console.diag("timer triggered!")
                plt.close("all")

            thread = Thread(target=set_timer, args=[timeout])
            thread.daemon = True    # mark as background thread
            thread.start()

        plt.show()

    def define_hyperparameters(self, hp_config_file_path):
        self.name_hparam_dict = {}
        import yaml
        hp_config_yaml = yaml.load(stream=open(hp_config_file_path, 'r'), Loader=yaml.Loader)
        hp_dict = hp_config_yaml["hparams"]
        for name, values in hp_dict.items():
            if not isinstance(values, list):
                continue  # Only lists of values are handled at the moment.
            hparam = Hyperparameter(self, self.fig, name)
            for value in values:
                hparam.add_setting(value, True)
            self.name_hparam_dict[name] = hparam
            self.add_hparam(hparam)

    def load_runs(self, all_run_records, plot_x_metric_name, plot_y_metric_name, hist_x_metric_name):
        self.runs = []
        for record in all_run_records:
            run = Run(record, plot_x_metric_name, plot_y_metric_name, hist_x_metric_name)
            if len(run.metric_reports) == 0:  # Exclude parent runs.
                continue
            self.runs.append(run)
            if MAX_NUM_RUNS > 0:
                if len(self.runs) == MAX_NUM_RUNS:
                    break
        console.print("{} runs downloaded".format(len(self.runs)))

    def get_plot_bounds_from_runs(self):
        self.plot_min_x = np.PINF
        self.plot_max_x = np.NINF
        self.plot_min_y = np.PINF
        self.plot_max_y = np.NINF
        self.hist_min_x = np.PINF
        self.hist_max_x = np.NINF
        max_reports = 0
        for run in self.runs:
            if len(run.metric_reports) > max_reports:
                max_reports = len(run.metric_reports)
            for report in run.metric_reports:
                x = report.x
                if x > self.plot_max_x:
                    self.plot_max_x = x
                if x < self.plot_min_x:
                    self.plot_min_x = x
                y = report.y
                if y > self.plot_max_y:
                    self.plot_max_y = y
                if y < self.plot_min_y:
                    self.plot_min_y = y
            if run.summary_val > self.hist_max_x:
                self.hist_max_x = run.summary_val
            if run.summary_val < self.hist_min_x:
                self.hist_min_x = run.summary_val
        self.plot_num_points = max_reports
        self.plot_x_inc = (self.plot_max_x - self.plot_min_x) / (self.plot_num_points - 1)

    def populate_hparams(self):
        # Connect up the runs and hparams.
        for run in self.runs:
            for hparam_name in run.hparam_name_value_pairs.keys():  # Only hparams that were read by the code,
                if hparam_name in self.name_hparam_dict.keys():  # and were listed in config_overrides.txt.
                    hparam = self.name_hparam_dict[hparam_name]
                    setting_value = run.hparam_name_value_pairs[hparam_name]
                    setting = hparam.add_setting(setting_value, False)
                    run.settings.append(setting)
        # Decide which hparams to display in the left pane.
        for hparam_name, hparam in self.name_hparam_dict.items():
            if len(hparam.value_setting_dict) > 1:
                hparam.display = True
                setting_values = []
                for setting in hparam.value_setting_dict.values():
                    setting_values.append(setting.value)
                # Sort the settings, to determine their display order in the middle pane.
                setting_values.sort()
                for val in setting_values:
                    hparam.settings.append(hparam.value_setting_dict[val])

    def group_runs_into_runsets(self):
        # Create the runsets.
        for run in self.runs:
            for hparam_name in run.hparam_name_value_pairs.keys():  # Only hparams that were read by the code,
                if hparam_name in self.name_hparam_dict.keys():     # and were listed in config_overrides.txt,
                    hparam = self.name_hparam_dict[hparam_name]
                    if hparam.display:                              # and are currently selected for display.
                        run.configuration_string += '{}, '.format(run.hparam_name_value_pairs[hparam_name])
            if run.configuration_string not in self.configstring_runset_dict.keys():
                self.configstring_runset_dict[run.configuration_string] = RunSet(run.configuration_string)
            runset = self.configstring_runset_dict[run.configuration_string]
            runset.runs.append(run)
        self.max_runs_per_runset = 0
        for runset in self.configstring_runset_dict.values():
            num_runs = len(runset.runs)
            if num_runs > self.max_runs_per_runset:
                self.max_runs_per_runset = num_runs

        # Finalize each runset.
        for runset in self.configstring_runset_dict.values():
            runset.count = len(runset.runs)
            # Average
            total = 0.
            for run in runset.runs:
                total += run.summary_val
                runset.metric = total / runset.count

    def assemble_left_pane(self):
        self.max_settings_per_hparam = 0
        id = 0
        self.displayed_hparams = []
        for hparam in self.hparams:
            if hparam.display:
                self.displayed_hparams.append(hparam)
                num_settings = len(hparam.settings)
                if num_settings > self.max_settings_per_hparam:
                    self.max_settings_per_hparam = num_settings
                hparam.id = id
                id += 1
                hparam.init_button()
        self.num_settings_to_display = self.max_settings_per_hparam

    def update_histograms(self):
        for hist in self.hists:
            hist.update()
        self.hists[0].axes.set_xlim(self.hist_min_x, self.hist_max_x)

    def update_runs(self):
        for run in self.runs:
            run.update_inclusion()
        self.update_histograms()
        self.perf.plot_from_runs()
        self.fig.canvas.draw()
