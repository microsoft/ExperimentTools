#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# impl_storage.py: implementation of XT storage commands
import os
import sys
import time
import json
import psutil
import fnmatch
import datetime
import tempfile
import subprocess

from xtlib import qfe
from xtlib import utils
from xtlib import errors
from xtlib import capture 
from xtlib import pc_utils
from xtlib import constants
from xtlib import file_utils
from xtlib import job_helper
from xtlib import run_helper
from xtlib import plot_builder
from xtlib import box_information

from xtlib.storage.store import Store
from xtlib.client import Client
from xtlib.console import console
from xtlib.cmd_core import CmdCore
from xtlib.impl_base import ImplBase
from xtlib.helpers import file_helper
from xtlib.backends import backend_aml 
from xtlib.cache_client import CacheClient
from xtlib.report_builder import ReportBuilder   
from xtlib.impl_storage_api import ImplStorageApi
from xtlib.hparams.hyperex import HyperparameterExplorer
from xtlib.qfe import command, argument, keyword_arg, option
from xtlib.qfe import flag, faq, root, example, clone, command_help, see_also

'''
This module implements the following commands:

manage resources:
     - xt create workspace <name>               # create new workspace
     - xt delete workspace <name>               # delete the specified workspace
     - xt extract <name> to <output directory>  # copy the specified run from the store to a local directory

general information:
     - xt list workspaces                       # list workspaces 
     - xt list experiments [ <wildcard> ]       # list all (or matching) experiments in current workspace
     - xt list jobs [ <wildcard> ]              # list all jobs in store
     - xt list boxes [ <wildcard> ]             # list all boxes defined in config file
     - xt list pools [ <wildcard> ]             # list all pools defined in config file
     - xt view console <name>                   # view console output from run (after it has finished running)
     - xt view log <name>                       # view live log of run name, job name, or "controller"
     - xt view metrics <name>                   # view the metrics logged for the specified run
     - xt plot <name list>                      # display a line plot for the metrics of the specified runs
     - xt explore <name>                        # run hyperparameter explorer on specified experiment
     - xt cat [ <path> ]                        # display contents of store file
     - xt workspace                             # display the default workspace
     - xt list runs [ <name list> ]             # list all (or matching) runs in current workspace

blob/file store:
     - xt upload blob(s) from <local path> [ to <path> ]      # upload local file to blob store path or blob name
     - xt upload file(s) from <local path> [ to <path> ]      # upload local files to file store path or filename
     - xt download blob(s) from <path> to [ <local path> ]    # download file from blob store to local directory or filename
     - xt download file(s) from <path> [ to <local path> ]    # download files from file store to local directory or filename
     - xt list blobs [ <path> ]                               # list files in blob store
     - xt list files [ <path> ]                               # list files in file store
     - xt delete files [ <path> ]                             # delete files from file store
'''     

class ImplStorage(ImplBase):
    def __init__(self, config, store):
        super(ImplStorage, self).__init__()
        self.config = config
        self.store = store
        self.core = CmdCore(self.config, self.store, None)
        self.client = Client(config, store, None)
        self.client.core = self.core
        self.impl_storage_api = ImplStorageApi(self.config, self.store)

    def is_aml_ws(self, ws_name):
        return False  # self.azure_ml.does_ws_exist(ws_name)

    def get_first_last_filtered_names(self, names, first_count=None, last_count=None, top_adjust=0, bot_adjust=0):
        if first_count:
            names = names[:first_count]   #  + top_adjust]
        elif last_count:
            # don't forget to include header + blank line (first 2 lines)
            #names = names[0:2] + names[-(last_count + bot_adjust):]
            names = names[-last_count:]

        return names            

    #---- LIST SHARES command ----
    @example(task="list shares in current Azure storage", text="xt list shares")
    @command(kwgroup="list", help="list currently defined shares")
    def list_shares(self):
        shares = self.store.get_share_names()
        console.print("\nXT shares:")
        for share in shares:
            console.print("  {}".format(share))

    #---- LIST WORKSPACES command ----
    @option("detail", default="names", help="when specified, some details about each workspace will be included")
    @example(task="list workspaces known to XT", text="xt list work")
    @command(kwgroup="list", help="list currently defined workspaces")
    def list_workspaces(self, detail):
        show_counts = detail=="counts"

        # # AML workspaces
        # names = self.azure_ml.get_workspaces()

        # STORE workspaces
        names = self.store.get_workspace_names()
        #console.print("names=", names)
        fmt_workspace = utils.format_store(self.store.store_type)
        console.print("\nXT workspaces:")
        
        # console.print HEADERS
        if show_counts:
            console.print('  {:20.20s} {:>8s}\n'.format("NAME", "RUNS"))  

            # console.print VALUES for each record
            for name in names:
                exper_count = len(self.store.get_run_names(name))
                if len(name) > 20:
                    name = name[0:18] + "..."
                console.print('  {:20.20s} {:>8d}'.format(name, exper_count))
        else:
            for name in names:
                console.print('  {:20.20s}'.format(name))

    #---- CREATE SHARE command ----
    @argument("share", help="the name for the newly created share")
    @example(task="create a new share named 'trajectories", text="xt create share trajectories")
    @command(kwgroup="create", help="creates a new XT share")
    def create_share(self, share):
        self.store.create_share(share)
        console.print("share created: " + share)

    #---- CREATE WORKSPACE command ----
    @argument("workspace", help="the name for the newly created workspace")
    @example(task="create a new workspace named 'project-x", text="xt create work project-x")
    @command(kwgroup="create", help="creates a new XT workspace")
    def create_workspace(self, workspace):
        ''' creates a new XT workspace.  Note that the workspace name can only contain letters, digits,
        and the "-" character.
        '''
        self.store.create_workspace(workspace)
        console.print("workspace created: " + workspace)

    #---- DELETE SHARE command ----
    @argument("share", help="the name of the share to be deleted")
    @option("response", default=None, help="the response to be used to confirm the share deletion")
    @example(task="delete the share named 'trajectories'", text="xt delete share trajectories")
    @command(kwgroup="delete", help="deletes the specified share")
    def delete_share(self, share, response):
        if not self.store.does_share_exist(share):
            errors.store_error("share not defined: " + share)
        else:
            # get top level folders
            fs = self.impl_storage_api.create_file_accessor(use_blobs=True, share=share, ws_name=None, exper_name=None, job_name=None, run_name=None)
            dd = fs.list_directories("", subdirs=0)
            folders = dd["folders"]
            count = len(folders)

            answer = pc_utils.input_response("Enter '{}' to confirm deletion of share ({} top level folders): ".format(share, count), response)
            if answer == share:
                self.store.delete_share(share)
                console.print("share deleted: " + share)
            else:
                console.print("share not deleted")

    #---- DELETE WORKSPACE command ----
    @argument("workspace", help="the name of the workspace to be deleted")
    @option("response", default=None, help="the response to be used to confirm the workspace deletion")
    @example(task="delete the workspace named 'project-x'", text="xt delete work project-x")
    @command(kwgroup="delete", help="deletes the specified workspace")
    def delete_workspace(self, workspace, response):
        if not self.store.does_workspace_exist(workspace):
            errors.store_error("workspace not defined: " + workspace)
        else:
            run_names = self.store.get_run_names(workspace)
            run_count = len(run_names)

            job_names = self.store.mongo.get_job_names({"ws_name": workspace})
            job_count = len(job_names)

            answer = pc_utils.input_response("Enter '{}' to confirm deletion of workspace ({} jobs, {} runs): ". \
                format(workspace, job_count, run_count), response)

            if answer == workspace:
                self.store.delete_workspace(workspace)
                console.print("workspace deleted: " + workspace)
            else:
                console.print("workspace not deleted")

    #---- LIST EXPERIMENTS command ----
    @option("detail", default="names", help="when specified, some details about each workspace will be included")
    @option(name="workspace", default="$general.workspace", help="the name of the workspace containing the experiments")
    @argument(name="wildcard", required=False, help="a wildcard pattern used to select matching experiment names")
    @example(task="list the experiments in the current workspace", text="xt list exper")
    @example(task="list the experiments starting with the name 'george' in the 'curious' workspace", text="xt list exper george* --work=curious")
    @command(kwgroup="list", kwhelp="displays the specified storage items", help="list experiments defined in the current workspace")
    def list_experiments(self, wildcard, workspace, detail):
        ws_name = workspace if workspace else workspace
        console.print("Experiments for workspace: {}".format(ws_name))

        # if self.is_aml_ws(ws_name):
        #     names = self.azure_ml.get_experiments(ws_name)
        # else:
        #     names = self.store.get_experiment_names(ws_name)
        names = self.store.get_experiment_names(ws_name)

        for name in names:
            if not wildcard or fnmatch.fnmatch(name, wildcard):
                console.print("  " + name)
        
    #---- LIST BOXES command ----
    @argument(name="wildcard", required=False, help="a wildcard pattern used to select box names")
    @option(name="first",  help="limit the list to the first N items", type=int)
    @option(name="last",  help="limit the list to the last N items", type=int)
    @flag(name="detail",  help="when specified, the associated job information is included")
    @example(task="list the boxes defined in the XT config file", text="xt list boxes")
    @command(kwgroup="list", help="list the boxes (remote computers) defined in your XT config file")
    def list_boxes(self, wildcard, detail, first, last):
        # get all box names
        names = list(self.config.get("boxes").keys())

        if wildcard:
            names = [name for name in names if fnmatch.fnmatch(name, wildcard)]
        names = self.get_first_last_filtered_names(names, first, last)

        if detail:
            # show detail of matching boxes
            console.print("box definitions:")
            for name in names:
                dd = self.config.get("boxes", name)
                console.print("  {}: {}".format(name, dd))
        else:
            console.print("boxes defined in config file:")
            for name in names:
                console.print("  " + str(name))

    #---- LIST TARGETS command ----
    @argument(name="wildcard", required=False, help="a wildcard pattern used to select compute names")
    @option(name="first",  help="limit the list to the first N items", type=int)
    @option(name="last",  help="limit the list to the last N items", type=int)
    @flag(name="detail",  help="when specified, the associated job information is included")
    @example(task="list the compute targets along with their definitions", text="xt list computes --detail")
    @command(kwgroup="list", help="list the user-defined compute targets")
    def list_targets(self, wildcard, detail, first, last):
        # get all compute names
        names = list(self.config.get("compute-targets").keys())

        if wildcard:
            names = [name for name in names if fnmatch.fnmatch(name, wildcard)]
        names = self.get_first_last_filtered_names(names, first, last)

        if detail:
            # show detail of matching boxes
            console.print("compute targets:")
            for name in names:
                dd = self.config.get_compute_def(name)
                console.print("  {}: {}".format(name, dd))
        else:
            console.print("compute targets:")
            for name in names:
                console.print("  " + str(name))

    #---- VIEW CONSOLE command ----
    @argument(name="name", help="the name of the run or job")
    @option(name="workspace", default="$general.workspace", help="the workspace that the run resides in")
    @option(name="node-index", default=0, help="the node index for the specified job")
    @example(task="view the console output for run26 in the curious workspace", text="xt view console curions/run26")
    @example(task="view the console output for job201, node3", text="xt view console job201 --node-index=3")
    @command(kwgroup="view",  help="view console output for specified run")
    def view_console(self, name, workspace, node_index):
        if job_helper.is_job_id(name):
            # treat target as job_name
            job_name = name
            workspace = job_helper.validate_job_name_with_ws(self.store, job_name, True)
            fn = "node-{}/after/stdout.txt".format(node_index)

            if not self.store.does_job_file_exist(job_name, fn):
                console.print("job '{}' has no file'{}'".format(job_name, fn))
            else:
                console.print("{} for {}:\n".format(fn, job_name))

                text = self.store.read_job_file(job_name, fn)
                text = pc_utils.make_text_display_safe(text)
                console.print(text)            
        else:
            # treat target as run_name
            run_name = name
            is_aml = False # self.is_aml_ws(workspace)
            ws, run_name, full_run_name = run_helper.validate_run_name(self.store, workspace, run_name, parse_only=is_aml)

            fn = "after/output/console.txt"
            if not self.store.does_run_file_exist(ws, run_name, fn):
                # legacy run layout 
                fn = "after/console.txt"

            if not self.store.does_run_file_exist(ws, run_name, fn):
                console.print("run '{}' has no file'{}'".format(full_run_name, fn))
            else:
                console.print("{} for {}:\n".format(fn, full_run_name))

                text = self.store.read_run_file(ws, run_name, fn)
                text = pc_utils.make_text_display_safe(text)
                console.print(text)

    #---- EXPORT WORKSPACE command ----
    @argument(name="output-file", help="the name of the output file to export workspace to")
    @option(name="workspace", default="$general.workspace", help="the workspace that the run resides in")
    @option(name="experiment", type="str_list", help="matches jobs belonging to the experiment name")
    @option(name="tags-all", type="str_list", help="matches jobs containing all of the specified tags")
    @option(name="tags-any", type="str_list", help="matches jobs containing any of the specified tags")
    @option(name="jobs", type="str_list", help="list of jobs to include")
    @example(task="export workspace ws5 to ws5_workspace.zip", text="xt export workspace ws5_workspace.zip --workspace=ws5")
    @command(help="exports a workspace to a workspace archive file")
    def export_workspace(self, output_file, workspace, tags_all, tags_any, jobs, experiment):
        self.impl_storage_api.export_workspace(output_file, workspace, tags_all, tags_any, jobs, experiment, show_output=True)

    #---- IMPORT WORKSPACE command ----
    @argument(name="input-file", help="the name of the archive file (.zip) to import the workspace from")
    @argument(name="new-workspace", required=False, help="the new name for the imported workspace")
    @option(name="job-prefix", default="imp", help="the prefix to add to imported job names")
    @flag("overwrite", help="When specified, any existing jobs with the same prefix and name will be overwritten")
    @example(task="import workspace from workspace.zip as new_ws5", text="xt import workspace workspace.zip new_ws5")
    @command(help="imports a workspace from a workspace archive file")
    def import_workspace(self, input_file, new_workspace, job_prefix, overwrite):
        self.impl_storage_api.import_workspace(input_file, new_workspace, job_prefix, overwrite, show_output=True)

    #---- VIEW RUN command ----
    @argument(name="run-name", help="the name of the run")
    @option(name="workspace", default="$general.workspace", help="the workspace that the run resides in")
    @example(task="view information for run26", text="xt view run26")
    @command(kwgroup="view",  help="view information for specified run")
    def view_run(self, run_name, workspace):
        console.print("run: {}".format(run_name))

    #---- VIEW LOG command ----
    @argument(name="target", help="the name of the run or job")
    #@option(name="box", default="local", help="the name of the box to use (for the controller log)")
    @option(name="workspace", default="$general.workspace", help="the workspace that the run resides in")
    @example(task="view the log entries for run26 in the curious workspace", text="xt view log curious/run26")
    @command(kwgroup="view", help="view the run log for specified run")
    def view_log(self, target, workspace):
        is_aml = self.is_aml_ws(workspace)

        # if target == "controller":
        #     # view CONTROLLER LOG from specified box
        #     if self.client.connect_to_controller(box):
        #         text = self.client.get_controller_log()
        #         console.print("box={}, controller log:".format(box.upper()))
        #         console.print(text)
        #     else:
        #         console.print("couldn't connect to controller for target: {}".format(target))

        if job_helper.is_job_id(target):
            # view JOB LOG
            records = self.store.get_job_log(target)
            console.print("log for {}:\n".format(target))
            for record in records:
                console.print(record)

        else:
            # view RUN LOG
            #errors.user_error("must specify a run name, job name, or 'controller'")
            ws, run_name, full_run_name = run_helper.validate_run_name(self.store, workspace, target, parse_only=is_aml)
            records = self.store.get_run_log(ws, run_name)
            console.print("log for {}:\n".format(full_run_name))

            for record in records:
                console.print(record)

    #---- VIEW METRICS command ----
    @argument(name="runs", type="str_list", help="a comma separated list of runs, jobs, or experiments", required=True)
    @argument(name="metrics", type="str_list", required=False, help="optional list of metric names")
    @option(name="workspace", default="$general.workspace", help="the workspace that the run resides in")
    @option(name="steps", type="int_list", help="show metrics only for the specified steps")
    @option(name="export", type="str", help="will create a tab-separated file for the report contents")
    @flag(name="merge", help="will merge all datasets into a single table")
    @option(name="hparams", type="str_list", help="will list the specified hyperparmeter names and values before the metrics")
    @example(task="view the logged metrics for run153 in the current workspace", text="xt view metrics run153")
    @command(kwgroup="view", help="view the set of logged metrics for specified run")
    def view_metrics(self, runs, workspace, steps, merge, metrics, hparams, export):

        args = {"run_list": runs, "workspace": workspace, "all": True, "sort_col": "name", 
            "max_runs": None, "columns": ["run", "hparams.*", "metrics.*"]}

        # actual store col names (vs. user-level names) used here
        col_dict = {"run_name": 1, "node_index": 1, "job_id": 1, "exper_name": 1, "ws": 1, "hparams": 1, "log_records": 1}

        run_log_records, using_default_last, user_to_actual, available, builder, last, std_cols_desc = \
            run_helper.get_filtered_sorted_limit_runs(self.store, self.config, False, col_dict=col_dict, args=args)

        for rr in run_log_records:
            console.print("\n{}:".format(rr["_id"]), end="")

            if hparams:
                #console.print("  hyperparameters:")
                rrh = rr["hparams"]
                first_value = True

                for name in hparams:
                    value = utils.safe_value(rrh, name)
                    if first_value:
                        console.print(" (", end="")
                        first_value = False
                    else:
                        console.print(", ", end="")

                    console.print("{}: {}".format(name, value), end="")

                # finish line and skip a line
                if first_value:
                    console.print("\n")
                else:
                    console.print(")\n")
 
            # build the metric sets
            log_records = rr["log_records"]
            metric_sets = run_helper.build_metrics_sets(log_records, steps, merge, metrics)
            just_one = len(metric_sets) == 1

            for i, ms in enumerate(metric_sets):
                lb = ReportBuilder(self.config, self.store, client=None)

                if export:
                    sep_char = "\t"
                    count = lb.export_records(export, ms["records"], ms["keys"], sep_char)
                    console.print("report exported to: {} ({} rows)".format(export, count-1))
                else:
                    if not just_one:
                        console.print("Dataframe {}:".format(1+i))

                    text, row_count = lb.build_formatted_table(ms["records"], ms["keys"])
                    # indent text 2 spaces on each line
                    text = "  " + text.replace("\n", "\n  ")
                    console.print(text)

    #---- PLOT command ----
    # args, flags, options
    @argument(name="runs", type="str_list", help="a comma separated list of runs, jobs, or experiments", required=True)
    @argument(name="col-list", type="str_list", required=False, help="a comma separated list of metric names to plot")

    @option(name="aggregate", values=["none", "mean", "min", "max", "std", "var", "sem"], help="how to aggregate data from multiple runs into a single plot")
    @option(name="break-on", type="str_list", help="the entity that triggers a plot change: usually 'run' or 'col' or 'group'")
    @option(name="colors", type="str_list", help="the colors to cycle thru for each trace in a plot")
    @option(name="color-map", type="str", help="the name of a matplotlib color map to use for trace colors")
    @option(name="color-steps", type="int", default=10, help="the number of steps in the color map")
    @option(name="error-bars", values=["none", "std", "var", "sem"], help="value to use for error bars")
    @option(name="group-by", values=["run", "node", "job", "experiment", "workspace"], help="the column to group data by (for --aggregate option) ")
    @option(name="layout", help="specifies how the plots should be layed out, e.g., '2x3'")
    @option(name="legend-args", type="named_arg_list", help="a list of name=value arguments to pass to the matplotlib legend object")
    @option(name="legend-titles", type="str_list", help="the titles to show in the legends of each plot")
    @option(name="max-runs", type=int, default=1024, help="the maximum number of runs to plot")
    @option(name="max-traces", type=int, default=64, help="the maximum number of plot traces to draw")
    @option(name="plot-titles", type="str_list", help="the titles to display on the plots")
    @option(name="shadow-alpha", type=float, default=.2, help="the alpha blending factor used to draw the plot shadow ")
    @option(name="shadow-type", default="none", values=["none", "pre-smooth", "min-max", "std", "var", "sem"], help="the type of plot shadow to draw")
    @option(name="save-to", help="path to file to which the plot will be saved")
    @flag(name="show-legend", default=True, help="controls if the legend is shown")
    @flag(name="show-plot", default=True, help="specifies if plot should be displayed")
    @flag(name="show-toolbar", default=True, help="controls if the matplotlib toolbar is shown")
    @option(name="smoothing-factor", type="float", help="the smoothing factor to apply to values before plotting (0.0-1.0)")
    @option(name="style", values=["darkgrid", "whitegrid", "dark", "white", "ticks", "none"], default="darkgrid", help="the seaborn plot style to use")
    @option(name="timeout", type=float, help="the maximum number of seconds the window will be held open")
    @option(name="title", type="str", help="the title to use for the set of plots")
    @option(name="workspace", default="$general.workspace", help="the workspace for the runs to be displayed")
    @option(name="x", default="$general.step-name", help="the metric to use for plotting along the x axis")
    @option(name="x-label", default=None, help="the label to display on the x axis")

    # plot attribute options
    #@option(name="plot-type", default="line", values=["line", "scatter", "histogram"], help="the type of plot to produce")
    # @option(name="alpha", type=float, default=1, help="the alpha blending factor to plot with")
    # @option(name="cap-size", type=float, default=5, help="the size of cap on the error bars")
    # @option(name="edge-color", type=str, help="the color of the edges of the marker")
    # @option(name="marker-shape", type=str, help="the marker shape to plot with")
    # @option(name="marker-size", type=float, default=2, help="the size of the markers drawn on the plot")
    @option(name="plot-args", type="named_arg_list", help="a list of name=value arguments to pass to the matplotlib plot object")

    @see_also("XT Plotting", "plotting")
    @example(task="plot the specified metrics for the specified runs, with a new plot for each run, in a 2x3 grid of plots", 
        text="xt plot run2264.1-run2264.6  train-acc, test-acc --break=run --layout=2x3", image="../images/plot2x3.png")
    @command(help="plot the logged metrics for specified runs in a matrix of plots")
    
    # command
    def plot(self, runs, col_list, x, layout, break_on, title, show_legend, plot_titles, legend_titles, 
        smoothing_factor, workspace, timeout, aggregate, shadow_type, shadow_alpha, style, 
        show_toolbar, max_runs, max_traces, group_by, error_bars, show_plot, save_to, 
        x_label, legend_args, plot_args, colors, color_map, color_steps, plot_type="line"):

        # hand-validate break-on values
        if break_on:
            for value in break_on:
                if not value in ["col", "run", "group"]:
                    errors.syntax_error("break-on values must be one of: col, run, or group")

        args = {"run_list": runs, "workspace": workspace, "all": True, "sort_col": "name", 
            "max_runs": max_runs, "columns": ["run", "metrics.*"] }

        x_col = x
        
        # store col names used here
        col_dict = {"run_name": 1, "node_index": 1, "job_id": 1, "exper_name": 1, "ws": 1, 
            "search_style": 1, "log_records": 1}

        run_log_records, using_default_last, user_to_actual, available, builder, last, std_cols_desc = \
            run_helper.get_filtered_sorted_limit_runs(self.store, self.config, False, col_dict=col_dict, args=args)

        # metric string will later contain calculated expressions
        if not col_list:
            col_list = []

        run_names = [rlr["_id"] for rlr in run_log_records]

        pb = plot_builder.PlotBuilder(run_names, col_list, x_col, layout, break_on, title, show_legend, plot_titles,
            legend_titles, smoothing_factor, plot_type, timeout, aggregate, shadow_type, shadow_alpha, 
            run_log_records, style, show_toolbar, max_runs, max_traces, 
            group_by, error_bars, show_plot, save_to, x_label, colors, color_map, color_steps, legend_args, plot_args)

        pb.build()

    #---- EXTRACT command ----
    @argument(name="runs", type="str_list", help="a comma separated list of runs, jobs, or experiments", required=True)
    @argument(name="dest-dir", help="the path of the directory")
    @flag(name="browse", help="specifies that an folder window should be opened for the dest_dir after the extraction has completed")
    @option(name="workspace", default="$general.workspace", help="the workspace that the runs resides in")
    @option("response", default=None, help="the response to be used to confirm the directory deletion")
    @example(task="extract files from curious/run26 to ./run26_files", text="xt extract curious/run26 ./run26_files")
    @command(help="download all files associated with the run to the specified directory")
    def extract(self, runs, dest_dir, workspace, response, browse):
        is_aml = self.is_aml_ws(workspace)
        #ws, run_name, full_run_name = run_helper.validate_run_name(self.store, workspace, run_name, parse_only=is_aml)

        console.print("extracting files for: {}...".format(runs))

        extract = True

        if os.path.exists(dest_dir):
            answer = pc_utils.input_response("'{}' already exists; OK to delete? (y/n): ".format(dest_dir), response)
            if answer != "y":
                extract = False

        if extract:
            file_utils.ensure_dir_clean(dest_dir)

            # first, determine nodes to be added to dest_dir
            nodes = "run"   # default

            for name_entry in runs:
                if job_helper.is_job_id(name_entry):
                    # if we find at least 1 job name specified, output to dest_dir/jobNNN/runNNN
                    if not nodes == "exper":
                        nodes = "job"
                elif not name_entry.startswith("run"):
                    # if we find at least 1 experiment, output to dest_dir/experFoo/jobNNN/runNNN
                    # this takes priority over all other nodes values
                    nodes = "exper"
            
            # convert list of runs, jobs, experiments into a list of runs
            pure_run_list, actual_ws = run_helper.expand_run_list(self.store, self.store.mongo, workspace, runs)

            for run_name in pure_run_list:

                if nodes == "exper":
                    # get exper_name and job_id of run
                    record = self.store.mongo.get_info_for_runs(actual_ws, {"_id": run_name}, {"job_id": 1, "exper_name": 1})
                    job_id = utils.safe_cursor_value(record, "job_id")
                    exper_name = utils.safe_cursor_value(record, "exper_name")
                    
                    actual_dest_dir = "{}/{}/{}/{}".format(dest_dir, exper_name, job_id, run_name)

                elif nodes == "job":
                    # get job_id of run
                    record = self.store.mongo.get_info_for_runs(actual_ws, {"_id": run_name}, {"job_id": 1})
                    job_id = utils.safe_cursor_value(record, "job_id")

                    actual_dest_dir = "{}/{}/{}".format(dest_dir, job_id, run_name)

                else:
                    # run_name only
                    actual_dest_dir = "{}/{}".format(dest_dir, run_name)
                    
                # download files for run (and unzip as needed)
                files = capture.download_run(self.store, actual_ws, run_name, actual_dest_dir)
                console.print("  {} files downloaded to: {}".format(len(files), actual_dest_dir))

            if browse:
                if pc_utils.is_windows():
                    os.startfile(dest_dir)
                else:
                    subprocess.Popen(['xdg-open', dest_dir])

    #---- CLEAR CREDENTIALS command ----
    @example(task="clears the XT authentication credentials cache", text="xt clear credentials")
    @command(kwgroup="clear", kwhelp="clears the specified object", help="clears the XT credentials cache")
    def clear_credentials(self):
        cc = CacheClient()
        response = cc.terminate_server()

        if response:
            console.print("XT cache server cleared")
        else:
            console.print("XT cache was not active")

    #---- EXPLORE command ----
    @argument(name="aggregate-name", help="the name of the job or experiment where run have been aggregated (hyperparameter search)")
    @option(name="cache-dir", default="$hyperparameter-explorer.hx-cache-dir", help="the local directory used to cache the Hyperparameter Explorer runs")
    #@option(name="search-rollup", default="$hyperparameter-search.search-rollup", help="the name of the aggregate function to apply to the primary metric values within a run")
    @option(name="workspace", default="$general.workspace", help="the workspace that the experiment resides in")
    @option(name="timeout", type=float, help="the maximum number of seconds the window will be held open")

    # hyperparameter-explorer hyperparameter name
    @option(name="steps-name", default="$hyperparameter-explorer.steps-name", help="the name of the steps/epochs hyperparameter")
    @option(name="log-interval-name", default="$hyperparameter-explorer.log-interval-name", help="the name of the log interval hyperparameter")

    # hyperparameter-explorer metric name
    @option(name="primary-metric", default="$general.primary-metric", help="the name of the metric to explore")
    @option(name="step-name", default="$general.step-name", help="the name of the step/epoch metric")
    @option(name="time-name", default="$hyperparameter-explorer.time-name", help="the name of the time metric")
    @option(name="success-rate-name", default="$hyperparameter-explorer.success-rate-name", help="the name of the success rate metric")
    @option(name="sample-efficiency-name", default="$hyperparameter-explorer.sample-efficiency-name", help="the name of the sample efficiency metric")

    @example(task="explore the results of all runs from job2998", text="xt explore job2998")
    @command(help="run the Hyperparameter Explorer on the specified job or experiment")
    def explore(self, aggregate_name, workspace, cache_dir, steps_name, log_interval_name, 
        primary_metric, step_name, time_name, success_rate_name, sample_efficiency_name, timeout): 
    
        # we need to respond to the job or experiment name user has specified
        dest_name = aggregate_name
        aggregate_dest = "job" if job_helper.is_job_id(dest_name) else "experiment"

        #console.print("metric=", metric)
        if aggregate_dest == "job":
            _, filenames = self.store.get_job_filenames(dest_name, constants.HP_CONFIG_DIR)
            if not filenames:
                errors.store_error("Missing hp-config file for job={}".format(dest_name))
        else:
            _, filenames = self.store.get_experiment_filenames(workspace, dest_name, constants.HP_CONFIG_DIR)
            if not filenames:
                errors.store_error("Missing hp-config file for experiment={}".format(dest_name))

        for f in filenames:
            if f.endswith('.yaml'):
                filename = f

        fn_hp_config = constants.HP_CONFIG_DIR + "/" + filename
        #console.print("found hp-config file: ", fn_hp_config)

        if job_helper.is_job_id(dest_name):
            job_ws = self.store.get_job_workspace(dest_name)
            if job_ws:
                console.diag("{} found in ws={}".format(dest_name, job_ws))
            console.diag("after get_job_workspace call (mongo-db)")

            # See if this job has tags for metric names needed by HX.
            filter_dict = {"job_id": dest_name}
            fields_dict = {"tags.plotted_metric": 1, "tags.primary_metric": 1, "tags.step_name": 1}
            records = self.store.mongo.get_info_for_jobs(filter_dict, fields_dict)
            tags = utils.safe_cursor_value(records, "tags")
            value = utils.safe_value(tags, "plotted_metric")
            if value:
                plotted_metric = value
            value = utils.safe_value(tags, "primary_metric")
            if value:
                primary_metric = value
            value = utils.safe_value(tags, "step_name")
            if value:
                step_name = value

        hx = HyperparameterExplorer(
            store=self.store,
            ws_name=workspace,
            run_group_type=dest_name,
            run_group_name=aggregate_dest,
            hp_config_cloud_path=fn_hp_config,
            hp_config_local_dir=cache_dir,
            plot_x_metric_name=step_name,
            plot_y_metric_name=plotted_metric,
            hist_x_metric_name=primary_metric)
        hx.run(timeout)

    #---- VIEW BLOB command ----
    @argument(name="path", help="the relative or absolute store path to the blob)")
    @option(name="share", help="the share name that the path is relative to")
    @option(name="workspace", default="$general.workspace", help="the workspace name that the path is relative to")
    @option(name="job", help="the job id that the path is relative to")
    @option(name="run", help="the run name that the path is relative to")
    @option(name="experiment", help="the experiment that the path is relative to")
    @example(task="display the contents of the specified file from the 'after' snapshot for the specified run", text="xt view blob after/output/userapp.txt --run=curious/run14")
    @command(kwgroup="view", kwhelp="view the specified storage item", help="display the contents of the specified storage blob")
    def view_blob(self, path, share, workspace, job, experiment, run):

        use_blobs = True
        fs = self.impl_storage_api.create_file_accessor(use_blobs=True, share=share, ws_name=workspace, 
            exper_name=experiment, job_name=job, run_name=run)

        text = fs.read_file(path)
        # if job:
        #     text = self.store.read_job_file(job, path)
        # elif experiment:
        #     text = self.store.read_experiment_file(workspace, experiment, path)
        # elif run:
        #     is_aml = self.is_aml_ws(workspace)
        #     ws, run_name, full_run_name = run_helper.validate_run_name(self.store, workspace, run, parse_only=is_aml)

        #     text = self.store.read_run_file(ws, run_name, path)
        # else:
        #     text = self.store.read_workspace_file(workspace, path)

        console.print("contents of " + path + ":")
        console.print(text)

    #---- VIEW WORKSPACE command ----
    @option(name="workspace", default="$general.workspace", help="the name of the workspace to use")
    @example("xt view workspace", task="display information about the current workspace")
    @command(kwgroup="view", help="display information about the current or specified workspace")
    def view_workspace(self, workspace):
        # for now, its just an echo of your CURRENT (or specified) workspace name
        console.print("workspace: {}".format(workspace))

    #---- VIEW PORTAL command ----
    @argument(name="target-name", help="the name of the target whose portal is to be opened")
    # @option(name="job", help="the name of the job to navigate to in the portal")
    # @option(name="experiment", default="$general.experiment", help="the name of the experiment to use")
    # @option(name="run-name", help="the name of the run to navigate to in the portal")
    # @option(name="workspace", default="$general.workspace", help="the workspace for the run")
    @option("cluster", help="the name of the Philly cluster to be used")
    @option("vc", help="the name of the Philly virtual cluster to be used")
    @flag("browse", help="specifies that the URL should be opened in the user's browser")
    @example("xt view portal aml --experiment=exper5", task="view the AML portal for exper5")
    @command(kwgroup="view", help="display or browse the URL for the specified backend service portal")
    def view_portal(self, target_name, cluster, vc, browse):

        # get service dict from target name
        service = self.config.get_external_service_from_target(target_name)

        service_name = service["name"]
        service_type = service["type"]

        if service_type == "aml":
            subscription_id = service["subscription-id"]
            resource_group = service["resource-group"]

            url = "https://ml.azure.com/experiments?wsid=/subscriptions/{}/resourcegroups/{}/workspaces/{}".format(\
                subscription_id, resource_group, service_name)

        elif service_type == "philly":
            username = self.config.expand_system_symbols("$username")
            if not cluster:
                target = self.config.get_compute_def(target_name)
                cluster = target["cluster"]

            url = "https://philly/#/jobSummary/{}/all/{}".format(cluster, username)
        elif service_type == "batch":
            url = "BatchExplorer.exe"
        else:
            errors.syntax_error("Unrecognized service_type: " + service_type)

        if browse:
            import webbrowser
            webbrowser.open(url)
        else:
            console.print("the portal url: {}".format(url))

    #---- VIEW EXPERIMENT command ----
    @option(name="experiment", default="$general.experiment", help="the name of the experiment to use")
    @flag(name="portal", help="specifies that the backend portal for the job should be opened")
    @example("xt view experiment", task="display information about the current experiment")
    @command(kwgroup="view", help="display information about the current or specified experiment")
    def view_experiment(self, experiment, portal):
        # for now, its just an echo of your CURRENT (or specified) workspace name
        console.print("experiment: {}".format(experiment))

    #---- VIEW TEAM command ----
    @option(name="team", default="$general.xt-team-name", help="the name of the team to use")
    @example("xt view team", task="show the currently active or specified team")
    @command(kwgroup="view", help="display information about the currently active team")
    def view_team(self, team):
        # for now, its just an echo of your CURRENT (or specified) team name
        console.print("team: {}".format(team))

    #---- LIST RUNS command ----
    @argument(name="run-list", type="str_list", help="a comma separated list of: run names, name ranges, or wildcard patterns", required=False)
    @option(name="workspace", default="$general.workspace", help="the workspace for the runs to be displayed")
    @option(name="job", type="str_list", help="a list of jobs names (acts as a runs filter)")
    @option(name="experiment", type="str_list", help="a list of experiment names (acts as a runs filter)")
    #@option(name="application", help="the application name for the runs to be displayed (acts as a filter)")
    @option(name="box", type="str_list", help="a list of boxes on which the runs were running (acts as a filter)")
    @option(name="target", type="str_list", help="a list of compute targets used by runs (acts as a filter)")
    @option(name="service-type", type="str_list", help="a list of back services on which the runs executed (acts as a filter)")

    # report options 
    @flag(name="all", help="don't limit the output; show all records matching the specified filters")
    @option(name="add-columns", type="str_list", help="list of columns to add to those in config file")
    @option(name="first", type=int, help="limit the output to the first N items")
    @option(name="last", type=int, default="$run-reports.last", help="limit the output to the last N items")
    @option(name="filter", type="prop_op_value", multiple=True, help="a list of filter expressions used to include matching records")
    @option(name="tags-all", type="str_list", help="matches records containing all of the specified tags")
    @option(name="tags-any", type="str_list", help="matches records containing any of the specified tags")
    @option(name="group", default="$run-reports.group", help="the name of the column used to group the report tables")
    @flag(name="number-groups", default="$run-reports.number-groups", help="the name of the column used to group the report tables")
    @option(name="sort", default="$run-reports.sort", help="the name of the report column to use in sorting the results")
    @option(name="max-width", type=int, default="$run-reports.max-width", help="set the maximum width of any column")
    @option(name="precision", type=int, default="$run-reports.precision", help="set the number of factional digits for float values")
    @option(name="columns", type="str_list", default="$run-reports.columns", help="specify list of columns to include")
    @option(name="export", type="str", help="will create a tab-separated file for the report contents")
    @option(name="status", type="str_list", default="$run-reports.status", 
        values= ["created", "allocating", "queued", "spawning", "running", "completed", "error", "cancelled", "aborted", "unknown"], 
        help="match runs whose status is one of the values in the list")
    @option(name="username", type="str_list", help="a list of usernames to filter the runs")
    
    # report flags
    @flag(name="flat", help="do not group runs")
    @flag(name="reverse", help="reverse the sorted items")
    #@flag(name="boxout", help="only list the latest run record for each box")
    @flag(name="parent", help="only list parent runs")
    @flag(name="child", help="only list child runs")
    @flag(name="outer", help="only outer (top) level runs")
    @flag(name="available", help="show the columns (std, hyperparameter, metrics) available for specified runs")

    # examples
    @example("xt list runs", task="display a runs report for the current workspace")
    @example("xt list runs run302.*", task="display the child runs for run302")
    @example("xt list runs --job=job2998 --last=10 --sort=metrics.test-acc", task="display the runs of job132, sorted by the metric 'test-acc', showing only the last 10 records")
    @example("xt list runs --status=error", task="display the runs that were terminated due to an error")
    @example("xt list runs --filter='epochs > 100'", task="only display runs that have run for more than 100 epochs")
    @faq("how can I find out which columns are available", "use the --available flag")
    @faq("why do some runs show their status as 'created', even though they have completed", "runs that are executed in direct mode, on a service backend without using the XT controller, do not always update the XT database correctly")
    @see_also("Using the XT CLI", "cmd_options")
    @command(kwgroup="list", pass_by_args=True, help="displays a run report for the specified runs")
    def list_runs(self, args):
        '''
        This command is used to display a tabular report of runs.  
        
        The columns shown can be customized by the run-reports:column entry in the XT config file.  In addition to specifying which columns to display, 
        you can also customize the appearance of the column header name and the formatting of the column value.  Examples:

            - To display the hyperparameter "discount_factor" as "discount", specify the column as "discount_factor=factor".
            - To display the value for the "steps" metric with the thousands comma format, specify the column as "steps:,".  
            - To specify the column "train-acc" as "accuracy" with 5 decimal places, specify it as "train-acc=accuracy:.5f".  

        The --filter option can be used to show a subset of all runs in the workspace.  The general form of the filter is <column> <relational operator> <value>. 
        Values can take the form of integers, floats, strings, and the special symbols $true, $false, $none, $empty (which are replaced with the corresponding Python values).

        Examples:
        
            - To show runs where the train-acc metric is > .75, you can specify: --filter="train-acc>.75".
            - To show runs where the hyperparameter lr was == .03 and the test-f1 was >= .95, you can specify the filter option twice: --filter="lr=.03"  --filter="test-f1>=.95"
            - To show runs where the repeat is set to something other than None, --filter="repeat!=$none".
        '''
        return run_helper.list_runs(self.store, self.config, args)

    #---- LIST JOBS command ----
    @argument(name="job-list", type="str_list", required=False, help="a comma separated list of job names, or a single wildcard pattern")
    @option(name="workspace", default="$general.workspace", help="the workspace for the job to be displayed")
    @option(name="experiment", type="str_list", help="a list of experiment names for the jobs to be displayed (acts as a filter)")
    #@option(name="application", help="the application name for the runs to be displayed (acts as a filter)")
    @option(name="target", type="str_list", help="a list of compute target associated with the jobs (acts as a filter)")
    @option(name="service-type", type="str_list", help="a list of backend services associated with the jobs (acts as a filter)")

    # report options 
    @flag(name="all", help="don't limit the output; show all records matching the specified filters")
    @option(name="first", type=int, help="limit the output to the first N items")
    @option(name="last", type=int, default="$job-reports.last", help="limit the output to the last N items")
    @option(name="filter", type="prop_op_value", multiple=True, help="a list of filter expressions used to include matching records")
    @option(name="tags-all", type="str_list", help="matches records containing all of the specified tags")
    @option(name="tags-any", type="str_list", help="matches records containing any of the specified tags")
    @option(name="sort", default="$run-reports.sort", help="the name of the report column to use in sorting the results")
    @option(name="max-width", type=int, default="$run-reports.max-width", help="set the maximum width of any column")
    @option(name="precision", type=int, default="$run-reports.precision", help="set the number of factional digits for float values")
    @option(name="columns", type="str_list", default="$job-reports.columns", help="specify list of columns to include")
    @option(name="export", type="str", help="will create a tab-separated file for the report contents")
    @option(name="username", type="str_list", help="a list of usernames that started the jobs (acts as a filter)")
    
    # report flags
    @flag(name="reverse", help="reverse the sorted items")
    @flag(name="available", help="show the columns (name, target, search-type, etc.) available for jobs")

    # examples, FAQs
    @example(task="display a report of the last 5 jobs that were run", text="xt list jobs --last=5")
    @see_also("Using the XT CLI", "cmd_options")
    @command(kwgroup="list", pass_by_args=True, help="displays a job report for the specified jobs")
    def list_jobs(self, args):
        '''
        This command is used to display a tabular report of jobs.  
        
        The columns shown can be customized by the job-reports:column entry in the XT config file.  In addition to specifying which columns to display, 
        you can also customize the appearance of the column header name and the formatting of the column value.  Examples:

            - To display the column "job_status" as "status", specify the column as "job_status=status".

        The --filter option can be used to show a subset of all runs in the workspace.  The general form of the filter is <column> <relational operator> <value>. 
        Values can take the form of integers, floats, strings, and the special symbols $true, $false, $none, $empty (which are replaced with the corresponding Python values).

        Examples:
        
            - To show runs where the repeat is set to something other than None, --filter="repeat!=$none".
        '''
        return job_helper.list_jobs(self.store, self.config, args)

    #---- UPLOAD command ----
    @argument(name="local-path", help="the path for the local source file, directory, or wildcard")
    @argument(name="store-path", required=False, help="the path for the destination store blob or folder")
    @option(name="share", required=True, help="the name of the share that the path is relative to")
    @option(name="workspace", default="$general.workspace", help="the workspace name that the path is relative to")
    @option(name="job", help="the job id that the path is relative to")
    @option(name="experiment", help="the experiment that the path is relative to")
    @option(name="run", help="the run name that the path is relative to")
    @flag(name="feedback", default=True, help="when True, incremental feedback will be displayed")
    @example(task="copy python files from local directory to the BLOB store area associated with workspace 'curious'", text="xt upload *.py . --share=data --work=curious")
    @example(task="copy the local file 'single_sweeps.txt' as 'sweeps.txt' in the BLOB store area for job2998", text="xt upload single_sweeps.txt sweeps.txt --share=data --job=job2998")
    @example(task="copy MNIST data from local dir to data upload folder name 'my-mnist'", text="xt upload ./mnist/** my-mnist --share=data")
    @command(help="copy local files to an Azure storage location")
    def upload(self, local_path, store_path, share, workspace, experiment, job, run, feedback):
        self.impl_storage_api.upload(local_path, store_path, share, workspace, experiment, job, run, feedback, show_output=True)

    #---- DOWNLOAD command ----
    @argument(name="store-path", help="the path for the source store blob or wildcard")
    @argument(name="local-path", required=False, help="the path for the destination file (if downloading a single file) or directory (if downloading multiple files)")
    @option(name="share", help="the name of the share that the path is relative to")
    @option(name="workspace", default="$general.workspace", help="the workspace name that the path is relative to")
    @option(name="job", help="the job id that the path is relative to")
    @option(name="experiment", help="the experiment that the path is relative to")
    @option(name="run", help="the run name that the path is relative to")
    @flag(name="feedback", default=True, help="when True, incremental feedback will be displayed")
    @flag(name="snapshot", help="when True, a temporary snapshot of store files will be used for their download")
    @example(task="download all blobs in the 'myrecent' folder (and its children) of the BLOB store area for job2998 to local directory ./zip", text="xt download myrecent/** ./zip --job=job2998")
    @command(help="copy Azure store blobs to local files/directory")
    def download(self, store_path, local_path, share, workspace, experiment, job, run, feedback, snapshot):
        self.impl_storage_api.download(store_path, local_path, share, workspace, experiment, job, run, feedback, snapshot, show_output=True)

    #---- LIST BLOBS command ----
    @argument(name="path", required=False, help="the path for the source store blob or wildcard")
    @option(name="share", help="the name of the share that the path is relative to")
    @option(name="workspace", default="$general.workspace", help="the workspace name that the path is relative to")
    @option(name="job", help="the job id that the path is relative to")
    @option(name="experiment", help="the experiment that the path is relative to")
    @option(name="run", help="the run name that the path is relative to")
    @option(name="subdirs", type=int, help="controls the depth of subdirectories listed (-1 for unlimited)")
    @example(task="list blobs from store for job2998", text="xt list blobs --job=job2998")
    @example(task="list blobs from 'models' share", text="xt list blobs --share=models")
    @command(kwgroup="list", kwhelp="displays the specified storage items", help="lists the Azure store blobs matching the specified path/wildcard and options")
    def list_blobs(self, path, share, workspace, experiment, job, run, subdirs):

        if subdirs is None:
            subdirs = 0
        elif subdirs == -1:
            subdirs = True

        run_name = run
        use_blobs = True

        fs = self.impl_storage_api.create_file_accessor(use_blobs, share, workspace, experiment, job, run)

        dd = fs.list_directories(path, subdirs)
        #console.print("dd[folders]=", dd["folders"])

        console.print("")
        console.print("Volume " + dd["store_name"])

        for folder in dd["folders"]:
            if use_blobs:
                console.print("\nDirectory of blob-store:/{}".format(folder["folder_name"]))
            else:
                console.print("\nDirectory of file-store:/{}".format(folder["folder_name"]))
            console.print("")
            
            # find maximum size of files in this folder
            max_size = 0
            for fi in folder["files"]:
                size = fi["size"]
                max_size = max(size, max_size)

            max_size_str = "{:,d}".format(max_size)
            size_width = max(5, len(max_size_str))

            fmt_folder = "{:20s}  {:<99s}  {}".replace("99", str(size_width))
            fmt_file =   "{:20s}  {:>99,d}  {}".replace("99", str(size_width))
            #console.print("fmt_folder=", fmt_folder)

            for dir_name in folder["dirs"]:
                console.print(fmt_folder.format("", "<DIR>", dir_name))

            for fi in folder["files"]:
                size = fi["size"]
                name = fi["name"]
                dt = datetime.datetime.fromtimestamp(fi["modified"])
                dt = dt.strftime("%m/%d/%Y  %I:%M %p")
                console.print(fmt_file.format(dt, size, name))

    def remove_store_dir(self, fs, dir_path, nesting=0):
        file_count = 0
        dir_count = 0

        # this is a shallow dir listing (not recursive)
        dir_names, file_names = fs.get_filenames(dir_path, full_paths=True)

        for dname in dir_names:
            #self.remove_store_dir(fs, "/" + dname, nesting=1+nesting)
            self.remove_store_dir(fs, dname, nesting=1+nesting)
            if not nesting:
                dir_count += 1

        for fname in file_names:
            #fs.delete_file("/" + fname)
            fs.delete_file(fname)
            if not nesting:
                file_count += 1

        # now, delete this directory
        fs.delete_directory(dir_path)

        return file_count, dir_count

    #---- DELETE BLOBS command ----
    @argument(name="path", required=False, help="the path for the store blob or wildcard")
    @option(name="share", help="the name of the share that the path is relative to")
    @option(name="workspace", default="$general.workspace", help="the workspace name that the path is relative to")
    @option(name="job", help="the job id that the path is relative to")
    @option(name="experiment", help="the experiment that the path is relative to")
    @option(name="run", help="the run name that the path is relative to")
    @example(task="delete the blobs under project-x for workspace curious", text="xt delete blobs project-x --work=curious")
    @command(kwgroup="delete", kwhelp="deletes the specified storage object", help="deletes specified Azure store blobs")
    def delete_blobs(self, path, share, workspace, experiment, job, run):
        # currently, deleting blobs is not supported to minimize risk of XT Store corruption
        use_blobs = True    # (object_type != "files") 

        if not share:
            errors.general_error("To help minimize the risk of corrupting XT run data, 'xt remove' currently can only be used with the --share option")

        store_path = path
        if not store_path:
            errors.syntax_error("must supply a STORE file path")
        #console.print("store_path=", store_path)

        # should the main dir and its child directories be removed?
        remove_dirs = store_path.endswith("**") or not "*" in store_path

        fs = self.impl_storage_api.create_file_accessor(use_blobs, share, workspace, experiment, job, run)

        uri = fs.get_uri(store_path)

        if not "*" in store_path and not "?" in store_path and fs.does_file_exist(store_path):
            # special case: a named file
            fs.delete_file(store_path)
            if use_blobs:
                console.print("blob removed: \n   " + uri)
            else:
                console.print("file removed: \n   " + uri)
            return 

        if remove_dirs:
            # special case: a named directory
            file_count, dir_count = self.remove_store_dir(fs, store_path)
            FILES = "file" if file_count == 1 else "files"
            SUBDIRS = "subdirectory" if dir_count == 1 else "subdirectories"
            console.print("\nremoved directory:\n   {} ({} {}, {} {})".format(uri, file_count, FILES, dir_count, SUBDIRS))
            return

        # process wildcard specification
        dir_names, file_names = fs.get_filenames(store_path, full_paths=False)
        what = "blobs" if use_blobs else "files"

        if len(file_names) == 0:
            console.print("no matching {} found in: {}".format(what, uri))
            return

        if len(file_names) == 1:
            what = "blob" if use_blobs else "file"

        console.print("\nfrom {}, removing {} {}:".format(uri, len(file_names), what))

        max_name_len = max([len(name) for name in file_names])
        name_width =  1 + max_name_len
        #console.print("max_name_len=", max_name_len, ", name_width=", name_width)

        for bn in file_names:
            rel_bn = uri + "/" + bn
            console.print("  {1:<{0:}} ".format(name_width, bn + ":"), end="", flush=True)
            fs.delete_file(rel_bn)
            console.print("removed")

    def dump_mongo_doc(self, name, doc, prev_indent):
        console.print("{}{}:".format(prev_indent, name))
        indent = prev_indent + "  "
        keys = list(doc.keys())
        keys.sort()

        for key in keys:
            value = doc[key]
            if isinstance(value, dict):
                self.dump_mongo_doc(key, value, indent)
            else:
                console.print("{}{}: {}".format(indent, key, value))

    def load_template(self, name):
        fn = file_utils.get_xtlib_dir() + "/templates/" + name
        td = utils.load_json_file(fn)
        return td

    #---- CREATE SERVICES TEMPLATE command ----
    @example(task="create a template for a new XT team", text="xt create services template")
    @flag(name="base", help="generate a template to create XT base services")
    @flag(name="batch", help="generate a template to create XT base services with Azure Batch")
    @flag(name="all", help="generate a template to create all XT services")
    @flag(name="aml", help="generate a template to create XT base services with Azure Machine Learning")
    @command(kwgroup="create", kwhelp="create the specified storage object", help="generate an Azure template for creating a set of resources for an XT Team")
    def create_services_template(self, base, batch, all, aml):
        '''Once you have run this command to generate a team template, follow these instructions to complete the process:
        
        1. browse to the Azure Portal Custom Template Deployment page: https://ms.portal.azure.com/#create/Microsoft.Template
        2. select 'Build your own template in the editor'
        3. copy/paste the contents of the generated file into the template editor
        4. click 'Save'
        5. select the billing subscription for the resources
        6. for resource group, choose 'Create new' and enter a simple, short, unique team name (no special characters)
        7. check the 'I Agree' checkbox and click on 'Purchase'
        8. if you receive a 'Preflight validation error', you may need to choose another (unique) team name
        9. after 5-15 minutes, you should receive a 'Deployment succeeded' message in the Azure Portal
        '''

        # if not flags specified, use BATCH as the default
        if not (base or batch or aml or all):
            batch = True

        # always read base part of template
        template = self.load_template("teamResourcesBase.json")

        if batch or all:
            bt = self.load_template("teamResourcesBatch.json")
            template["resources"].extend(bt)

        if aml or all:
            at = self.load_template("teamResourcesAml.json")
            template["resources"].extend(at)

        # load the template as a string
        template_text = json.dumps(template, indent=4)

        # # personalize it for team name
        # template = template.replace("teamx7", name)

        # add user's object_id from azure active directory
        object_id = self.config.get_vault_key("object_id")
        template_text = template_text.replace("$object_id", object_id)
        
        # write to local directory
        fn_team_template = "azure_template.json"
        file_utils.write_text_file(fn_team_template, template_text)

        # explain how to use
        PORTAL_URL = "https://ms.portal.azure.com/"
        TEMPLATE_URL = "https://ms.portal.azure.com/#blade/Microsoft_Azure_Marketplace/MarketplaceOffersBlade/selectedMenuItemId/home/searchQuery/template"

        console.print()
        console.print("To create the resources for your XT team:")
        console.print("  1. browse to the Azure Portal Custom Template Deployment page: https://ms.portal.azure.com/#create/Microsoft.Template")
        console.print("  2. select 'Build your own template in the editor'")
        console.print("  3. copy/paste the contents of the generated file into the template editor")
        console.print("  4. click 'Save'")
        console.print("  5. select the billing subscription for the resources")
        console.print("  6. for resource group, choose 'Create new' and enter a simple, short, unique team name (no special characters)")
        console.print("  7. check the 'I Agree' checkbox and click on 'Purchase'")
        console.print("  8. if you receive a 'Preflight validation error', you may need to choose another (unique) team name")
        console.print("  9. after 5-15 minutes, you should receive a 'Deployment succeeded' message in the Azure Portal")
        console.print("  10. at this point, you can create a new local XT config file for your team, for example:")

        console.print()
        console.print("--> template file generated: {}".format(fn_team_template))
        console.print()

        # TODO: add --team option to xt config cmd
        #console.print("  > xt config --template=batch --team=YourTeamNameHere")
        
    #---- VIEW MONGO command ----
    @argument(name="name", help="the name of the run or job to show the mongo-db data for")
    @option(name="workspace", default="$general.workspace", help="the workspace that the run is defined in")
    @example(task="view the mongo-db information for run23 in the curious workspace", text="xt view mongo curious/run23")
    @command(kwgroup="view", help="view the mongo-db JSON data associated with the specified run")
    def view_mongo(self, name, workspace):
        # view MONGO-DB document for run or job

        if name.startswith("run"):
            ws, run_name, full_run_name = run_helper.validate_run_name(self.store, workspace, name)

            include_log = False         # can make this an option later
            run_names = [run_name]      # can support multiple runs later
            filter_dict = {}

            filter_dict["run_name"] = {"$in": run_names}
            mongo_docs = self.store.get_ws_runs(ws, filter_dict, include_log)

            for doc in mongo_docs:
                #console.print("doc:")
                self.dump_mongo_doc("\nMONGO-DB for " + full_run_name, doc, "")
        elif job_helper.is_job_id(name):
            ws = job_helper.validate_job_name_with_ws(self.store, name, True)

            include_log = False         # can make this an option later
            job_names = [name]      # can support multiple runs later
            filter_dict = {}

            filter_dict["job_id"] = {"$in": job_names}
            mongo = self.store.get_mongo()
            mongo_docs = mongo.get_info_for_jobs(filter_dict, None)

            for doc in mongo_docs:
                #console.print("doc:")
                self.dump_mongo_doc("\nMONGO-DB for " + name, doc, "")
        else:
            errors.syntax_error("name argument must start with 'run' or 'job'")

    def find_available_tensorboard_port(self):
        port = None
        ports_used = {}

        for process in psutil.process_iter():
            try:
                if "python" in process.name().lower():
                    cmd_line = process.cmdline()
                    if len(cmd_line) > 3 and "(port=" in cmd_line[3]:
                        pycmd = cmd_line[3]
                        index = 6 + pycmd.index("(port=")
                        portstr = pycmd[index:index+4]
                        ports_used[portstr] = 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        for p in range(6006, 6999):
            pstr = str(p)
            if not pstr in ports_used:
                port = p
                break

        return port

    def get_runs_by_prop(self, ws_name, prop, value):
        mongo = self.store.get_mongo()
        records = mongo.get_info_for_runs(ws_name, {prop: value}, {"_id": 1, "compute": 1, "run_name": 1})
        #names = [rr["_id"] for rr in records]
        return records

    def record_has_cols(self, rr, columns):
        found_all = True

        for col in columns:
            if not col in rr:
                found_all = False
                break
        
        return found_all

    def find_value_in_parts(self, text, name, terminator=","):
        value = None

        if name in text:
            pre, post = text.split(name, 1)
            if terminator in post:
                value, _ = post.split(terminator, 1)
            else:
                value = post

        return value

    #---- VIEW EVENTS command ----
    @keyword_arg(name="name", keywords=["xt", "controller", "quick-test"], help="name of the event log")
    @option(name="last", default=25, help="the number of most recent entries to display")
    @flag(name="all", help="specify to display all entries")
    @example(task="view the most recent events in the XT log", text="xt view events xt")
    @command(kwgroup="view", help="view formatted information in the XT event log")
    def view_events(self, name, last, all):
        
        file_names = {"xt": constants.FN_XT_EVENTS, "controller": constants.FN_CONTROLLER_EVENTS, "quick-test": constants.FN_QUICK_TEST_EVENTS}
        fn = os.path.expanduser(file_names[name])

        if not os.path.exists(fn):
            console.print("no file found: {}".format(fn))
        else:
            lines = file_utils.read_text_file(fn, as_lines=True)

            if not all:
                lines = lines[-last:]

            in_stack_trace = False

            for line in lines:
                if not line:
                    continue

                parts = line.split(",", 3)
                if len(parts) < 4 or len(parts[0]) != 10:
                    # STACK TRACE
                    if not in_stack_trace:
                        console.print("\n========================================")
                        in_stack_trace = True
                    console.print(line)
                    continue

                if in_stack_trace:
                    console.print("")
                    in_stack_trace = False

                date = parts[0].strip()
                time = parts[1].strip()
                level = parts[2].strip()
                extra = parts[3].strip()

                if ":" in extra:
                    name, rest = extra.split(":", 1)
                    name = name.strip()
                else:
                    name = extra
                    rest = ""

                if level == "ERROR":
                    in_stack_trace = True
                    console.print("\n==================================")

                if not "Client-Request-ID=" in line:
                    # non-auzre event
                    msg = "{}, {}, {}, {}: {}".format(date, time, level, name, rest)
                    console.print(line)
                    continue

                # this is an azure traffic entry
                codes = rest.split("-")
                client_id = codes[2][-4:]

                msg = "{}, {}, {}, {} [{}]: ".format(date, time, level, name, client_id)
                parts = rest.split(" ", 2)
                rest = parts[2]

                if rest.startswith("Outgoing request:"):
                    # skip a line to improve readability
                    msg = "\n" + msg

                    method = self.find_value_in_parts(rest, "Method=")
                    if method:
                        msg += method + ": " 

                    path = self.find_value_in_parts(rest, "Path=")
                    if path:
                        msg += path

                elif rest.startswith("Receiving Response:"):
                    parts = rest.split(" ", 4)

                    status = self.find_value_in_parts(rest, "HTTP Status Code=")
                    if status:
                        msg += "status=" + status

                    message = self.find_value_in_parts(rest, "Message=")
                    if message:
                        msg += " ({})".format(message)
                
                elif rest.startswith("Received expected http error"):
                    msg += "error recognized"
                    # parts = rest.split(" ", 4)

                    # status = self.find_value_in_parts(rest, "HTTP Status Code=")
                    # if status:
                    #     msg += "status=" + status

                    # exception = self.find_value_in_parts(rest, "Exception=", terminator="<")
                    # if exception:
                    #     msg += " ({})".format(exception)

                console.print(msg)
          

    #---- VIEW TENSORBOARD command ----
    @argument(name="run-list", type="str_list", help="a comma separated list of: run names, name ranges, or wildcard patterns", required=False)

    @option(name="experiment", help="the experiment that the path is relative to")
    @option(name="interval", type=int, default=10, help="specifies interval between polling for changes in the run's 'output' storage")
    @option(name="job", help="the job id that the path is relative to")
    @option(name="template", default="$tensorboard.template", help="specifies a template for building the collected log paths")
    @flag(name="browse", help="specifies that a browser page should be opened for the link")
    @option(name="workspace", default="$general.workspace", help="the workspace that the runs are defined within")
    @example(task="view tensorboard plots for run23 in the curious workspace", text="xt view tensorboard curious/run23")
    @command(kwgroup="view", help="create a tensorboard instance to show data associated with the specified runs")
    def view_tensorboard(self, run_list, experiment, interval, job, browse, workspace, template):
        '''
        this cmd will run a separate process that runs the XTLIB tensorboard_reader to run TB and sync TB logs to 
        local files.
        '''
        # extract columns from template
        columns = []
        us_columns = []
        templ = template

        while "{" in templ:
            index = templ.index("{")
            if not "}" in templ:
                errors.syntax_error("template '{}' is missing a matching '}' at index={}".format(template, index))
            index2 = templ.index("}")

            col = templ[index+1:index2].strip()
            if "." in col:
                # python format() doesn't like dotted names, so convert to underscore name
                col2 = col.replace(".", "_")
                template = template.replace(col, col2)
                columns.append(col)
                us_columns.append(col2)
            else:
                columns.append(col)
                us_columns.append(col)
            templ = templ[index2+1:]

        args = {"experiment": experiment, "job": job, "run_list": run_list, "workspace": workspace, "columns": columns}

        # don't default to --last=10
        args["all"] = True

        # gather run records for specified runs
        orig_records, using_default_last, user_to_actual, available, builder, last, std_cols_desc = \
            run_helper.get_filtered_sorted_limit_runs(self.store, self.config, True, args=args)

        # build tb_path for each run record
        run_records = []

        for rr in orig_records:

            # replace dotted names with underscore names
            rr = {key.replace(".", "_"): value for key, value in rr.items()}

             # logdir not available here, so add a placeholder that tensorboard reader will process
            rr["logdir"] = "{logdir}"  

            # ensure all requests columns are present; if not, skip run (e.g., could be parent run)
            if not self.record_has_cols(rr, us_columns):
                continue

            # remove pesky leading zeros by pre-formatting values
            for key, value in rr.items():
                if isinstance(value, float):
                    value = str(value).lstrip("0")
                    rr[key] = value                    

            # format the partial path
            tb_path = template.format(**rr)

            # store in run record for tensorboard reader 
            # reader will write log files for this run to tb_path in local dir
            rr["tb_path"] = tb_path

            run_records.append(rr)

        cwd = file_utils.fix_slashes(file_utils.make_tmp_dir("xt_tb_reader_", False), True)

        spd = self.store.get_props_dict()
        port = self.find_available_tensorboard_port()
        if not port:
            errors.internal_error("No available port for tensorboard")

        pd = {"cwd": cwd, "store_props_dict": spd, "ws_name": workspace, "run_records": run_records, 
            "browse": browse, "interval": interval}
        text = json.dumps(pd)

        # due to large number of run_records, json text can be too long for OS, so we pass as a temp file 
        fn_base = "run_records.json"
        fn_temp = os.path.join(cwd, fn_base)

        with open(fn_temp, "wt") as outfile:
            outfile.write(text)
            outfile.flush()

        fn_temp_esc = fn_temp.replace("\\", "\\\\")     # escape single backslashes

        # get quotes right (start cmd wants double quotes around python cmd)
        python_cmd = '"import xtlib.tensorboard_reader as reader; reader.main(port={}, fn_run_records=\'{}\')"'.format(port, fn_temp_esc)
        console.print("launching tensorboard reader process...")

        # we want to start a new visible command window running python with our command
        if pc_utils.is_windows():
            # EASIEST way to do this without creating a separate .bat file is to use os.system
            full_cmd = 'start /D "{}" cmd /K python -u -c {}'.format(cwd, python_cmd)
            console.diag("cmd=", full_cmd)

            os.system(full_cmd)
        else:
            # linux
            parts = ["gnome-terminal", "--", "bash", "-c", "python -c {}".format(python_cmd)]
            console.diag("parts=", parts)

            subprocess.Popen(args=parts)

    def build_tag_fd(self, tag_list):
        fd = {}
        # convert tags to filter dictionary entries
        for tag in tag_list:
            if "=" in tag:
                name, value = tag.split("=")
                fd["tags." + name] = value
            else:
                fd["tags." + tag] = None

        return fd

    #---- SET TAGS command ----
    @argument(name="name-list", type="str_list", required=True, help="a comma separated list of job or run names, or a single wildcard pattern")
    @argument(name="tag-list", type="tag_list", required=True, help="a comma separated list of tag name or tag assignments")
    @option(name="workspace", default="$general.workspace", help="the workspace for the job to be displayed")
    # examples, FAQs, command
    @example(task="add the tag 'description' with the value 'explore effects of 5 hidden layers' to the jobs job3341 thru job3356", text="xt set tags job3341-job3356 description='explore effects of 5 hidden layers'")
    @command(help="set tags on the specified jobs or runs")
    def set_tags(self, name_list, tag_list, workspace):
        first_name = name_list[0]
        fd = self.build_tag_fd(tag_list)
        mongo = self.store.get_mongo()

        if job_helper.is_job_id(first_name):
            job_helper.set_job_tags(self.store, mongo, name_list, tag_list, workspace, fd, clear=False)
        elif first_name.startswith("run"):
            run_helper.set_run_tags(self.store, mongo, name_list, tag_list, workspace, fd, clear=False)
        else:
            errors.syntax_error("first name must start with 'run' or 'job', found '{}'".format(first_name))

    #---- CLEAR TAGS command ----
    @argument(name="name-list", type="str_list", required=True, help="a comma separated list of job or run names, or a single wildcard pattern")
    @argument(name="tag-list", type="tag_list", required=True, help="a comma separated list of tag names")
    @option(name="workspace", default="$general.workspace", help="the workspace for the job to be displayed")
    # examples, FAQs, command
    @example(task="clears the tag 'description' for job3341 and job5535", text="xt clear tags job3341, job5535 description")
    @command(kwgroup="clear", help="clear tags on the specified jobs or runs")
    def clear_tags(self, name_list, tag_list, workspace):
        first_name = name_list[0]
        fd = self.build_tag_fd(tag_list)
        mongo = self.store.get_mongo()

        if job_helper.is_job_id(first_name):
            job_helper.set_job_tags(self.store, mongo, name_list, tag_list, workspace, fd, clear=True)
        elif first_name.startswith("run"):
            run_helper.set_run_tags(self.store, mongo, name_list, tag_list, workspace, fd, clear=True)
        else:
            errors.syntax_error("first name must start with 'run' or 'job'")

    #---- LIST TAGS command ----
    @argument(name="name-list", type="str_list", required=True, help="a comma separated list of job or run names, or a single wildcard pattern")
    @argument(name="tag-list", type="tag_list", required=False, help="a comma separated list of tag names")
    @option(name="workspace", default="$general.workspace", help="the workspace for the job to be displayed")
    # examples, FAQs, command
    @example(task="list the tags for job3341 and job5535", text="xt list tags job3341, job5535")
    @command(kwgroup="list", help="list tags of the specified jobs or runs")
    def list_tags(self, name_list, tag_list, workspace):
        first_name = name_list[0]
        mongo = self.store.get_mongo()

        if job_helper.is_job_id(first_name):
            job_helper.list_job_tags(self.store, mongo, name_list, tag_list, workspace)
        elif first_name.startswith("run"):
            run_helper.list_run_tags(self.store, mongo, name_list, tag_list, workspace)
        else:
            errors.syntax_error("first name must start with 'run' or 'job'")
