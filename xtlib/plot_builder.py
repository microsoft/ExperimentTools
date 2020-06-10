#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# self.py: functions to help produce plots of metrics from runs
import math
import time
import numpy as np
import pandas as pd

from xtlib import qfe
from xtlib import utils
from xtlib import errors
from xtlib import console
from xtlib import constants
from xtlib import run_helper

PRESMOOTH = "_PRE-SMOOTH_"
ERR = "_ERR_"
MEAN = "_MEAN_"
MIN = "_MIN_"
MAX = "_MAX_"

class PlotBuilder():
    def __init__(self, run_names, col_names, x_col, layout, break_on, title, show_legend, plot_titles,
            legend_titles, smoothing_factor, plot_type, timeout,
            aggregate, shadow_type, shadow_alpha, run_log_records, style, show_toolbar, max_runs, max_traces,
            group_by, error_bars, show_plot, save_to, x_label, colors, color_map, color_steps, legend_args, plot_args):
        
        self.run_names = run_names
        self.col_names = col_names
        self.x_col = x_col
        self.layout = layout
        self.break_on = break_on
        self.title = title
        self.show_legend = show_legend
        self.plot_titles = plot_titles
        self.legend_titles = legend_titles
        self.smoothing_factor = smoothing_factor
        self.plot_type = plot_type
        self.timeout = timeout
        self.aggregate = utils.zap_none(aggregate)
        self.shadow_type = utils.zap_none(shadow_type)
        self.shadow_alpha = shadow_alpha
        self.run_log_records = run_log_records
        self.style = utils.zap_none(style)
        self.show_toolbar = show_toolbar
        self.max_runs = max_runs
        self.max_traces = max_traces
        self.group_by = group_by if group_by else "run"
        self.error_bars = utils.zap_none(error_bars)
        self.show_plot = show_plot
        self.save_to = save_to
        self.x_label = x_label
        self.legend_args = legend_args
        self.plot_args = plot_args

        if colors:
            self.colors = colors
        else:
            if not color_map:
                color_map = "cycle"
            self.colors = self.get_colors(color_map, color_steps)

    def get_colors(self, color_map_name, steps):
        from matplotlib import cm

        if color_map_name == "cycle":
            # matplotlab default colors (V2.0, category10 color palette)

            colors = \
                 ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
                 '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
                 '#bcbd22', '#17becf']
        else:
            color_map = cm.get_cmap(color_map_name)
            colors = color_map( np.linspace(0, 1, steps) )

        return colors

    def build(self):

        data_frames_by_cols = self.build_data_frames()
        if data_frames_by_cols:

            for cols, dfx in data_frames_by_cols.items():
                dfx = self.pre_preprocess_data_frame(dfx)
                data_frames_by_cols[cols] = dfx

            # this check is to enable faster testing
            if self.show_plot or self.save_to:
                self.plot_data(data_frames_by_cols)

    def build_data_frames(self):
        '''
        1. for each run, collect the reported metrics as metric sets (by reported col list)

        2. append to the dataframe for that col list
        '''
        # build "data_frames"
        no_metrics = []
        pp_run_names = []
        used_max = False
        data_frames_by_cols = {}
        got_columns = False

        for i, record in enumerate(self.run_log_records):
            # extract metrics for this run
            run = record["_id"]
            node = utils.node_id(record["node_index"])
            job = record["job_id"]
            experiment = record["exper_name"]
            workspace = record["ws"]
            search_style = utils.safe_value(record, "search_style")
            if search_style and search_style != "single":
                # parent run with children - skip it
                continue

            log_records = record["log_records"]

            metric_sets = run_helper.build_metrics_sets(log_records)
            if not metric_sets:
                no_metrics.append(run)
                continue

            if self.max_runs and len(pp_run_names) >= self.max_runs:
                used_max = True
                break

            if not got_columns:
                # set x and y columns
                explicit = qfe.get_explicit_options()
                if not "x" in explicit:
                    self.x_col = self.get_actual_x_column(metric_sets, self.x_col, self.col_names)

                if not self.col_names:
                    # not specified by user, so build defaults
                    self.col_names = self.get_default_y_columns(metric_sets, self.x_col)

                got_columns = True
                
            # merge metric sets into dfx
            for metric_set in metric_sets:

                # create a pandas DataFrame
                df = pd.DataFrame(metric_set["records"])
                cols = str(list(df.columns))
                
                # ensure this df has our x_col 
                if self.x_col and not self.x_col in cols:
                    continue

                # ensure this df has at least 1 y_col
                found_y = False
                for y in self.col_names:
                    if y in cols:
                        found_y = True
                        break

                if not found_y:
                    continue

                # add run_name column
                df["run"] = [run] * df.shape[0]
                df["node"] = [node] * df.shape[0]
                df["job"] = [job] * df.shape[0]
                df["experiment"] = [experiment] * df.shape[0]
                df["workspace"] = [workspace] * df.shape[0]

                if not cols in data_frames_by_cols:
                    data_frames_by_cols[cols] = df
                else:
                    dfx = data_frames_by_cols[cols]
                    dfx = dfx.append(df)
                    data_frames_by_cols[cols] = dfx

            pp_run_names.append(run)

        if no_metrics:
            console.print("\nnote: following runs were skipped (currently have no logged metrics): \n    {}\n".format(", ".join(no_metrics)))

        if used_max:
            console.print("plotting first {} runs (use --max-runs to override)".format(self.max_runs))
        else:
            console.print("plotting {} runs...".format(len(pp_run_names)))

        # update our list of run_names to proces
        self.run_names = pp_run_names

        return data_frames_by_cols

    def get_agg_df(self, df, agg_op, df_cols):
        agg_dict = {}

        for col in self.col_names:
            if col in df_cols:
                agg_dict[col] = agg_op

        df_out = df.agg(agg_dict)  
        #df3 = df2.fillna(method='ffill')
        df_out = df_out.reset_index()

        return df_out

    def pre_preprocess_data_frame(self, dfx):
        '''
        apply pre-processing operations to specified data frame:
            - data frame most likely will NOT contain all y cols
            - optionally smooth the Y-axis cols
            - optionally create aggregate VALUE Y-axis cols
            - optionally create aggregate SHADOW Y-axi cols
        '''
        if self.smoothing_factor:
            # SMOOTH each column of values

            for col in self.col_names:
                if col in dfx.columns:
                    self.apply_smooth_factor(dfx, col, self.smoothing_factor)

        # get a copy of columns before group-by
        dfx_pre = dfx
        df_cols = list(dfx.columns)

        if self.aggregate:
            # specifying an aggregate hides the the other runs' values (for now)

            if self.group_by:
                # GROUP data 
                group_col = self.group_by
                group_prefix = "node" if self.group_by == "node_index" else ""
                x_col = self.x_col

                dfx = dfx.groupby([group_col, x_col])
            
            # AGGREGATE data
            df_agg_from = dfx
            dfx = self.get_agg_df(df_agg_from, self.aggregate, df_cols)

            # ERROR BARS data
            if self.error_bars:
                dfx = self.build_agg_stat(df_agg_from, self.error_bars, df_cols, dfx)

            # SHADOW TYPE BARS data
            if self.shadow_type == "min-max":
                dfx = self.build_agg_stat(df_agg_from, "min", df_cols, dfx)
                dfx = self.build_agg_stat(df_agg_from, "max", df_cols, dfx)
            elif self.shadow_type and self.shadow_type != "pre-smooth":
                dfx = self.build_agg_stat(df_agg_from, "mean", df_cols, dfx)
                dfx = self.build_agg_stat(df_agg_from, self.shadow_type, df_cols, dfx)

            # if self.shadow_type:
            #     self.run_names.append(self.shadow_type)

            #     min_values, max_values = self.range_runs(runs_dict, self.shadow_type)
            #     runs_dict[self.shadow_type] = (min_values, max_values)

        return dfx

    def build_agg_stat(self, df_agg_from, stat, df_cols, dfx):
        df_stat = self.get_agg_df(df_agg_from, stat, df_cols)
        stat_name = "_{}_".format(stat.upper())

        for col in self.col_names:
            if col in df_stat.columns:
                # extract stat data for col
                stat_data = df_stat[col]

                # add col data as new name to dfx
                dfx[col + stat_name] = stat_data

        return dfx

    def apply_smooth_factor(self, data_frame, col, weight):

        presmooth_values = list(data_frame[col])
        smooth_values = self.apply_smooth_factor_core(presmooth_values, weight)

        data_frame[col] = smooth_values
        data_frame[col + PRESMOOTH] = presmooth_values

    def apply_smooth_factor_core(self, values, weight):
        smooth_values = []

        if values:
            prev = values[0] 
            for value in values:
                smooth = weight*prev + (1-weight)*value
                smooth_values.append(smooth)                       
                prev = smooth                                 

        return smooth_values

    def calc_actual_layout(self, count, layout):
        if not "x" in layout:
            errors.syntax_error("layout string must be of form RxC (R=# rows, C=# cols)")

        r,c = layout.split("x", 1)

        if r:
            r = int(r)
            c = int(c) if c else math.ceil(count / r)
        elif c:
            c = int(c)
            r = int(r) if r else math.ceil(count / c)

        full_count = r*c
        if full_count < count:
            errors.combo_error("too many plots ({}) for layout cells ({})".format(count, full_count))

        return r, c

    def get_xy_values(self, data_frames_by_cols, group_name, x_col, y_col, stat_col):

        x_values = None
        y_values = None
        stat_values = None

        '''
        Note: a specific y_col could exist in different data_frames, depending
        on the other columns logged with in during each run.  So, don't stop
        searching on the first match with y_col - keep going until we get a 
        matching set of group_name records also.
        '''
        for cols, df in data_frames_by_cols.items():
            if y_col in df.columns:
                # filter values for specified run name
                df = df[ df[self.group_by]==group_name ]
                record_count = len(df.index)

                if record_count:
                    y_values = df[ y_col ].to_numpy(dtype=float)

                    if x_col and x_col in df.columns:
                        x_values = df[ x_col ].to_numpy(dtype=float)

                    if stat_col and stat_col in df.columns:
                        stat_values = df[ stat_col ].to_numpy(dtype=float)
                    break

        return x_values, y_values, stat_values

    def plot_data(self, data_frames_by_cols):
        console.diag("starting to plot data")

        # on-demand import for faster XT loading
        import seaborn as sns
        import matplotlib.pyplot as plt
        import matplotlib as mpl
        import pylab

        if not self.show_toolbar:
            # hide the ugly toolbar at bottom left of plot window
            mpl.rcParams['toolbar'] = 'None' 

        # apply seaborn styling
        if self.style:
            sns.set_style(self.style)

        # decide how layout, titles, etc. will be set
        group_names = set()

        # gather group names (usually all are in the first dataset, but not always)
        for dfx in data_frames_by_cols.values():
            name_list = dfx[self.group_by].unique()
            group_names.update(set(name_list))
        
        group_names = list(group_names)

        # this will sort the group names in a number-smart way 
        group_names.sort(key=utils.natural_keys)

        group_count = len(group_names)
        col_count = len(self.col_names)

        break_on_groups = self.break_on and ("run" in self.break_on or "group" in self.break_on)
        break_on_cols = self.break_on and "col" in self.break_on

        if break_on_groups and break_on_cols:
            plot_count = group_count*col_count
        elif break_on_groups:
            plot_count = group_count
        elif break_on_cols:
            plot_count = col_count
        else:
            plot_count = 1

        # calc true layout 
        if self.layout:
            plot_rows, plot_cols = self.calc_actual_layout(plot_count, self.layout) 
        else:
            plot_cols = plot_count
            plot_rows = 1

        runs_per_plot = 1 if break_on_groups else group_count
        cols_per_plot = 1 if break_on_cols else col_count
        
        if runs_per_plot == 1:
            plot_title = "$run"
            legend_text = "$col"
        elif cols_per_plot == 1:
            plot_title = "$col"
            legend_text = "$run"
        else:
            plot_title = None
            legend_text = "$col ($run)"

        if not self.plot_titles and plot_title:
            self.plot_titles = [plot_title]

        if not self.legend_titles:
            self.legend_titles = [legend_text]

        # configure matplotlib for our subplots
        sharex = True
        sharey = True

        #plt.close()
        window_size = (14, 6)

        fig, plots = plt.subplots(plot_rows, plot_cols, figsize=window_size, sharex=sharex, sharey=sharey, constrained_layout=True)
        if not isinstance(plots, np.ndarray):
            # make it consistent with plot_count > 1 plots
            plots = [plots]
        elif plot_rows > 1:
            plots = plots.flatten()

        fig.suptitle(self.title, fontsize=16)

        if self.timeout:
            # build a thread to close our plot window after specified time
            from threading import Thread

            def set_timer(timeout):
                console.print("set_timer called: timeout=", self.timeout)
                time.sleep(self.timeout)
                console.diag("timer triggered!")

                plt.close("all")
                print("closed all plots and the fig")

            thread = Thread(target=set_timer, args=[self.timeout])
            thread.daemon = True    # mark as background thread
            thread.start()

        line_index = 0
        plot_index = 0
        trace_count = 0
        x_label = self.x_label if self.x_label else self.x_col
            
        if self.aggregate == "none":
            self.aggregate = None

        if (self.aggregate and (break_on_cols and not break_on_groups)) \
            or ((not self.aggregate) and break_on_cols):
            # columns needs to be the outer loop
            for c, col in enumerate(self.col_names):

                if trace_count >= self.max_traces:
                    break

                if c and break_on_cols:
                    plot_index += 1
                    line_index = 0

                for r, group_name in enumerate(group_names):

                    if trace_count >= self.max_traces:
                        break

                    if r and break_on_groups:
                        plot_index += 1
                        line_index = 0

                    # PLOT MIDDLE
                    ax = plots[plot_index] # .gca()
                    self.plot_middle(data_frames_by_cols, ax, group_name, col, self.x_col, x_label, line_index)
                    line_index += 1
                    trace_count += 1
        else:
            # run will work as the outer loop
            for r, group_name in enumerate(group_names):

                if trace_count >= self.max_traces:
                    break

                if r and break_on_groups:
                    plot_index += 1
                    line_index = 0

                for c, col in enumerate(self.col_names):

                    if trace_count >= self.max_traces:
                        break

                    if c and break_on_cols:
                        plot_index += 1
                        line_index = 0

                    # PLOT MIDDLE
                    ax = plots[plot_index] #.gca()
                    self.plot_middle(data_frames_by_cols, ax, group_name, col, self.x_col, x_label, line_index)
                    line_index += 1
                    trace_count += 1

        if self.save_to:
            plt.savefig(self.save_to)

        if self.show_plot:
            pylab.show()

    def get_seaborn_color_map(self, name, n_colors=5):
        '''
        name: muted, xxx
        '''
        import seaborn as sns
        from matplotlib.colors import ListedColormap

        # Construct the colormap
        current_palette = sns.color_palette(name, n_colors=n_colors)
        cmap = ListedColormap(sns.color_palette(current_palette).as_hex())
        return cmap

    def plot_middle(self, data_frames_by_cols, ax, group_name, col, x_col, x_label, line_index):
        
        color_index = line_index % len(self.colors)
        color = self.colors[color_index]

        if self.shadow_type == "pre-smooth":
            # draw PRESMOOTH SHADOW
            x, y, _ = self.get_xy_values(data_frames_by_cols, group_name, self.x_col, col + PRESMOOTH, None)

            self.plot_inner(ax, group_name, col, self.x_col, x_label, line_index, x_values=x, y_values=y,
                color=color, alpha=self.shadow_alpha, use_y_label=False)
        elif self.shadow_type:

            if self.shadow_type == "min-max":
                x, y, _ = self.get_xy_values(data_frames_by_cols, group_name, self.x_col, col + MIN, None)
                x2, y2, _ = self.get_xy_values(data_frames_by_cols, group_name, self.x_col, col + MAX, None)
            else:
                # draw RANGE SHADOW
                stat_name = "_{}_".format(self.shadow_type.upper())
                x, y_mean, _ = self.get_xy_values(data_frames_by_cols, group_name, self.x_col, col + MEAN, None)
                x, y_stat, _ = self.get_xy_values(data_frames_by_cols, group_name, self.x_col, col + stat_name, None)

                y = y_mean - y_stat
                y2 = y_mean + y_stat

            self.plot_inner(ax, group_name, col, self.x_col, x_label, line_index, x_values=x, y_values=y, 
                color=color, alpha=self.shadow_alpha, use_y_label=False, y2_values=y2)

        # DRAW NORMAL LINE
        err_col = col + "_{}_".format(self.error_bars.upper()) if self.error_bars else None
        x, y, err = self.get_xy_values(data_frames_by_cols, group_name, self.x_col, col, err_col)

        self.plot_inner(ax, group_name, col, self.x_col, x_label, line_index, x_values=x, y_values=y, 
            color=color, alpha=1, use_y_label=True, err_values=err)

    def plot_inner(self, ax, run_name, col, x_col, x_label, line_index, x_values, y_values, 
        color, alpha, use_y_label, y2_values=None, err_values=None):

        import seaborn as sns
        from matplotlib.ticker import MaxNLocator

        if x_values is None:        
            x_values = range(len(y_values))
        else:
            ax.set_xlabel(x_label)

        console.detail("x_values=", x_values)
        console.detail("y_values=", y_values)
        console.detail("y2_values=", y2_values)

        num_y_ticks = 10
        ax.get_yaxis().set_major_locator(MaxNLocator(num_y_ticks))
        #color = self.colors[line_index % len(self.colors)]

        if use_y_label:
            line_title = self.legend_titles[line_index % len(self.legend_titles)]
            line_title = self.fixup_text(line_title, run_name, col)
        else:
            line_title = None

        cap_size = 5
        is_range_plot = bool(y2_values is not None)

        # our default attributes
        kwargs = {"label": line_title, "color": color, "alpha": alpha}
        
        if not is_range_plot:
            kwargs["capsize"] = cap_size

        # let user override
        if self.plot_args and not is_range_plot:

            for name, value in self.plot_args.items():
                value = utils.make_numeric_if_possible(value)
                kwargs[name] = value

        #cmap = self.get_seaborn_color_map("muted")
        if self.plot_type == "line":

            if is_range_plot:

                # RANGE plot
                ax.fill_between(x_values, y_values, y2_values, **kwargs)

            elif x_values is not None:

                # X/Y LINE plot
                 trace = ax.errorbar(x_values, y_values, yerr=err_values, **kwargs)  
            else:

                # LINE plot
                ax.errorbar(y_values, '-', label=line_title, yerr=err_values, **kwargs)

        else:
            # for now, we can get lots of milage out of line plot (errorbars, scatter, scatter+line)
            # so keep things simple and just support 1 type well 
            errors.syntax_error("unknown plot type={}".format(self.plot_type))

        if self.plot_titles:
            plot_title = self.plot_titles[line_index % len(self.plot_titles)]
            plot_title = self.fixup_text(plot_title, run_name, col)

            ax.set_title(plot_title)

        if self.show_legend:
            ax.legend()

            if self.legend_args:
                # pass legend args to legend object
                ax.legend(**self.legend_args)

    def fixup_text(self, text, run_name, col):
        text = text.replace("$run", run_name)
        text = text.replace("$col", col)
        return text

    def get_actual_x_column(self, metric_sets, default_x_col, y_cols):
        '''
        x col search order:
            - specified in cmd line (explict_options, checked by caller)
            - specified as 'step_name" in logged metrics (matching y_cols)
            - specified as 'step_name" in first logged metrics (if no y_cols specified)
            - config file step_name property
            - guess from a list of commonly used named
        '''
        x_col = None
        first_y = y_cols[0] if y_cols else None

        for ms in metric_sets:
            keys = ms["keys"]
            if first_y and not first_y in keys:
                continue

            if constants.STEP_NAME in keys:
                records = ms["records"]
                x_col = records[0][constants.STEP_NAME]
            elif default_x_col:
                x_col = default_x_col
            else:
                # try guessing from common names (and __index__, sometimes added by XT)
                x_names = ["epoch", "step", "iter", "epochs", "steps", "iters", constants.INDEX]
                for xn in x_names:
                    if xn in keys:
                        x_col = xn
                    break

            # only look in first metric set 
            break

        return x_col

    def get_default_y_columns(self, metric_sets, x_col):
        y_cols = []

        for ms in metric_sets:
            keys = ms["keys"]
            omits = [x_col, constants.STEP_NAME, constants.TIME]

            for key in keys:
                if not key in omits:
                    y_cols.append(key)

            # only look in first metric set 
            break

        return y_cols

    def range_runs(self, runs_dict, range):
        runs = list(runs_dict.values())

        if range == "min-max":
            min_values = np.min(runs, axis=0)
            max_values = np.max(runs, axis=0)
        elif range == "std":
            means = np.mean(runs, axis=0)
            max_values = means + np.std(runs, axis=0)
            min_values = means - np.std(runs, axis=0)
        elif range == "error":
            from scipy import stats

            means = np.mean(runs, axis=0)
            max_values = means + stats.sem(runs, axis=0)
            min_values = means - stats.sem(runs, axis=0)
        else:
            errors.syntax_error("unrecognized range value: {}".format(range))

        return min_values, max_values

    def get_values_by_run(self, col, run_log_records):
        runs_dict = {}

        for rr in run_log_records:
            run_name = rr["_id"]
            value_recs = rr["metrics"]["records"]
            new_values = [vr[col] for vr in value_recs]

            runs_dict[run_name] = new_values

        return runs_dict

    