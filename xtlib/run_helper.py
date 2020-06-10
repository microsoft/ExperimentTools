#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# run_helper.py: functions needed for processing run-related information
import json
import fnmatch

from xtlib import qfe
from xtlib import utils
from xtlib import errors
from xtlib import constants
from xtlib import file_utils
from xtlib import job_helper

from xtlib.console import console
from xtlib.report_builder import ReportBuilder   
from xtlib.storage import fixup_mongo_runs

def expand_run_list(store, mongo, workspace, name_list):
    '''
    args:
        - mongo: instance of our mongodb mgr
        - workspace: name of the workspace associated with name_list
        - name_list: a list of run sources (run_names, job_names, experiment_names)

    processing:
        - extract pure list of run names from the name_list (all runs must be from same workspace)

    returns:
        - pure run_list
        - actual workspace used

    special:
        - name_list is a comma separated list of entries
        - entry format:
            <name>           (run_name, job_name, or experiment_name)
            <run wildcard>   (must start with "run" and can contain "*" and "?" chars)
            <name>-<name>    (a range of run or job names)
    '''
    run_list = []
    actual_ws = workspace

    if name_list:
        for entry in name_list:
            if entry.startswith("run"):
                actual_ws = expand_run_entry(store, mongo, workspace, run_list, entry)
            elif job_helper.is_job_id(entry):
                actual_ws = expand_job_entry(store, mongo, workspace, run_list, entry)
            else:
                actual_ws = expand_experiment_name(store, mongo, workspace, run_list, entry)

    return run_list, actual_ws

def expand_run_entry(store, mongo, workspace, run_list, name):
    
    if name in ["*", "run*"]:
        # return  "all records" indicator
        sub_list = ["*"]
        actual_ws = workspace
    elif "*" in name:
        #match wildcard to all run names in workspace
        re_pattern = utils.wildcard_to_regex(name)
        filter_dict = {"_id": {"$regex": re_pattern} }

        records = mongo.get_info_for_runs(workspace, None, {"_id": 1})
        sub_list = [rec["_id"] for rec in records]
        actual_ws = workspace
    else:            
        sub_list, actual_ws = parse_run_list(store, workspace, [name])
        
    run_list += sub_list
    return actual_ws

def expand_job_entry(store, mongo, workspace, run_list, name_entry):
    from xtlib import job_helper

    # expand name_entry into a list of job names
    job_list, actual_ws = job_helper.expand_job_list(store, mongo, workspace, [name_entry], can_mix=False)

    run_filter = {"job_id": {"$in": job_list}}
    result = mongo.get_info_for_runs(workspace, run_filter, {"_id": 1})
    if result:
        names = [run["_id"] for run in result]
        run_list += names

    return actual_ws

def expand_experiment_name(store, mongo, workspace, run_list, exper_name):

    actual_ws = workspace

    run_filter = {"exper_name": exper_name}
    result = mongo.get_info_for_runs(workspace, run_filter, {"_id": 1})
    if result:
        names = [run["_id"] for run in result]
        run_list += names

    return actual_ws

def set_run_tags(store, mongo, name_list, tag_list, workspace, fd, clear):
    run_list, actual_ws = expand_run_list(store, mongo, workspace, name_list)

    if run_list:
        matched_count = 0

        if len(run_list)==1 and run_list[0] == "*":
            # update all records
            filter = {}
        else:
            # update specified run names
            filter = {"run_name": {"$in": run_list}}

            result = mongo.update_runs_from_filter(workspace, filter, fd, clear=clear, upsert=False)
            matched_count = result.matched_count
        # for run in run_list:
        #     mongo.update_run_info(workspace, run, fd, clear=clear, upsert=False)  

        if clear:
            console.print("{} runs, tags cleared: {}".format(matched_count, tag_list))
        else:
            console.print("{} runs, tags set: {}".format(matched_count, tag_list))
    else:
        console.print("no matching runs found")

def list_run_tags(store, mongo, name_list, tag_list, workspace):
    run_list, actual_ws = expand_run_list(store, mongo, workspace, name_list)

    if run_list:
        filter_dict = {"run_name": {"$in": run_list}}
        fields_dict = {"tags": 1}

        records = mongo.get_info_for_runs(workspace, filter_dict, fields_dict)
        for record in records:
            run = record["_id"]
            console.print("{}:".format(run))

            if "tags" in record:
                tags = record["tags"] 
                tag_names = list(tags.keys())
                tag_names.sort()

                for tag in tag_names:
                    if tag_list and not tag in tag_list:
                        continue
                    console.print("  {}: {}".format(tag, tags[tag]))
    else:
        console.print("no matching run found")

def get_run_property_dicts():
    # user-friendly property names for jobs
    user_to_actual = {"box": "box_name", "created": "create_time", "child": "is_child", "cluster": "cluster",
        "description": "description", "experiment": "exper_name", "exit_code": "exit_code", 
        "from_host": "from_computer_name", "from_ip": "from_ip", 
        "guid": "run_guid", "job": "job_id", "last_time": "last_time",
        "node": "node_index", "outer": "is_outer", "parent": "is_parent", "path": "path", 
        "pool": "pool", "repeat": "repeat", "restarts": "restarts", "run": "run_name", "run_num": "run_num", 
        "script": "script", "search": "search_type", "search_style": "search_style", "service_type": "service_type", "sku": "sku",
        "status": "status", "target": "compute", "username": "username", "vc": "vc", "workspace": "ws", "xt_build": "xt_build", 
        "xt_version": "xt_version",
        "hparams": "hparams", "metrics": "metrics", "tags": "tags",

         "ended": "end_time", "started": "start_time", "duration": "run_duration", "queued": "queue_duration",

         # special info (not a simple property)
         "metric_names": "metric_names",
        }

    std_cols_desc = {
        #"app": "the application associated with the run",
        "box": "the name of the box the run executed on",
        "child": "indicates that this run is a child run",
        "created": "the time when the run was created", 
        "cluster": "the name of the service cluster for the run", 
        "ended": "when the run execution ended",
        "description": "the user specified description associated with the run",
        "experiment": "the name of the experiment associated with the run",
        "exit_code": "the integer value returned by the run",
        "from_host": "the name of the computer that submitted the run",
        "from_ip": "the IP address of the computer that submitted the run",
        "guid": "a string that uniquely identifies the run",
        "job": "the job id that the run was part of",
        "last_time": "the time of the most recent operation associated with the run",
        "run": "the name of the run",
        "run_num": "the sort-compatible number portion of run",
        "node": "the 0-based node index of the run's box",
        "outer": "indicates this run is not a child run",
        "parent": "indicates that the run spawned child runs",
        "path": "the full path of the run's target script or executable file",
        "pool": "the user-defined name describing the backend service or set of boxes on which the run executed",
        "repeat": "the user-specified repeat-count for the run",
        "restarts": "the number of times the run was preempted and restarted",
        "script": "the base name of the run's script or executable file",
        "search": "the type of hyperparameter search used to start the run",
        "search_style": "describes how search is being accomplished (one of: static, dynamic, multi, repeat, single)",
        "service_type": "the type of service of the compute target",
        "sku": "the name of the service SKU (machine size) specified for the run",
        "started": "when the run started executing",
        "status": "the current status of the run",
        "target": "the compute target the run was submitted to",
        "username": "the login name of the user who submitted the run",
        "vc": "the name of the virtual cluster for the run",
        "workspace": "the name of the workspace containing the run",
        "xt_build": "the build date of xt that was used to launch the run",
        "xt_version": "the version of xt that was used to launch the run",

        "ended": "when the run completed",
        "started": "when the run started running",
        "duration": "how long the run has been executing",
        "queued": "how long the run was waiting to start",

        "metric_names": "list of metrics names, ordered by their reporting",

        }

    return user_to_actual, std_cols_desc
        
def build_filter_part(fd, args, arg_name, store_name):
    value = args[arg_name]
    if value:
        if isinstance(value, list):
            fd[store_name] = {"$in": value}
        else:
            fd[store_name] = value

def build_run_filter_dict(run_list, user_to_actual, builder, args):
    fd = {}
    option_filters = ["job", "experiment", "target", "service_type", "box", "status", "parent", "child", "outer", "username"]  

    if run_list:
        # filter by specified job names
        fd["_id"] = {"$in": run_list}

    # filter by specified options
    for name in option_filters:
        if name in args:
            build_filter_part(fd, args, name, user_to_actual[name])

    # filter by filter_list
    if "filter" in args:
        filter_exp_list = args["filter"]
        if filter_exp_list:
            builder.process_filter_list(fd, filter_exp_list, user_to_actual)

    # filter by tags_all
    if "tags_all" in args:
        tags_all = args["tags_all"]
        if tags_all:
            for tag in tags_all:
                fd["tags." + tag] = {"$exists": True}

    # filter by tags_any
    if "tags_any" in args:
        tags_any = args["tags_any"]
        if tags_any:
            fany_list = []
            for tag in tags_any:
                f = {"tags." + tag: {"$exists": True}}
                fany_list.append(f)

            # or all of fany conditions together
            fd["$or"] = fany_list

    #fd["is_parent"] = True
    return fd

def extract_dotted_cols(records, prefix):
    nd = {}
    prefix += "."
    prefix_len = len(prefix)

    for record in records:
        for key in record.keys():
            if key.startswith(prefix):
                col = key[prefix_len:]
                nd[col] = 1

    return list(nd.keys())

def get_filtered_sorted_limit_runs(store, config, show_gathering, col_dict=None, args=None):
    
    console.diag("start of: get_filtered_sorted_limit_runs")
    # required
    run_list = args["run_list"]

    # optional
    pool = utils.safe_value(args, "target")
    available = utils.safe_value(args, "available")
    workspace = utils.safe_value(args, "workspace")
    
    if workspace:
        store.ensure_workspace_exists(workspace, flag_as_error=True)

    mongo = store.get_mongo()

    # have MONGO update any old RUN documents to new format
    fixup_mongo_runs.fixup_runs_if_needed(mongo.mongo_db, workspace)

    # get info about run properties
    user_to_actual, std_cols_desc = get_run_property_dicts()        
    actual_to_user = {value: key for key, value in user_to_actual.items()}

    builder = ReportBuilder(config, store, client=None)

    # get list of specified runs
    pure_run_list, actual_ws = expand_run_list(store, mongo, workspace, run_list)
    if run_list and not pure_run_list:
        errors.general_error("no run(s) found")

    # build a filter dict for all specified filters
    filter_dict = build_run_filter_dict(pure_run_list, user_to_actual, builder, args)

    # if show_gathering:
    #     console.print("gathering run data...", flush=True)

    # get the mongo records for the matching RUNS
    records, using_default_last, last = builder.get_mongo_records(mongo, filter_dict, workspace, "runs", actual_to_user, 
        col_dict=col_dict, args=args)

    console.diag("end of: get_filtered_sorted_limit_runs")

    return records, using_default_last, user_to_actual, available, builder, last, std_cols_desc

def list_runs(store, config, args):

    records, using_default_last, user_to_actual, available, builder, last, std_cols_desc = \
        get_filtered_sorted_limit_runs(store, config, True, args=args)

    if available:
        std_cols = list(user_to_actual.keys())
        hparams_cols = extract_dotted_cols(records, "hparams")
        metrics_cols = extract_dotted_cols(records, "metrics")
        tags_cols = extract_dotted_cols(records, "tags")

        lines = builder.available_cols_report("run", std_cols, std_cols_desc, hparams_list=hparams_cols, 
            metrics_list=metrics_cols, tags_list=tags_cols)

        for line in lines:
            console.print(line)
    else:            
        #avail_list = list(user_to_actual.keys())
        lines, row_count, was_exported = builder.build_report(records, report_type="run-reports", args=args)

        if was_exported:
            console.print("")

            for line in lines:
                console.print(line)
        else:
            # console.print the report
            if row_count > 0:
                console.print("")

                for line in lines:
                    console.print(line)

                if row_count > 1:
                    if using_default_last:
                        console.print("total runs listed: {} (defaulted to --last={})".format(row_count, last))
                    else:
                        console.print("total runs listed: {}".format(row_count))
            else:
                console.print("no matching runs found")

def get_run_records(store, workspace, run_names, fields_dict=None):
    ''' return run records for specified run names'''

    mongo = store.get_mongo()

    filter_dict = {}
    filter_dict["run_name"] = {"$in": run_names}

    if not fields_dict:
        # by default, get everything but the log records
        fields_dict = {"log_records": 0}

    run_records = mongo.get_info_for_runs(workspace, filter_dict, fields_dict)

    return run_records

def get_run_record(store, workspace, run_name, fields_dict = None):
    run_records = get_run_records(store, workspace, [run_name], fields_dict)
    if not run_records:
        errors.store_error("Run {} does not exist in workspace {}".format(run_name, workspace))
    rr = run_records[0]
    return rr

def get_service_node_info(store, workspace, run_name):
    rr = run_helper.get_run_record(store, workspace, name, {"job_id": 1, "node_index": 1})
    job_id = rr["job_id"]
    node_index = rr["node_index"]

    service_node_info, backend = job_helper.get_service_node_info(job_id, node_index)

def get_rightmost_run_num(run):
    if not run.startswith("run"):
        errors.syntax_error("Illegal run name, must start with 'run'")

    if "." in run:
        prefix, num = run.split(".")
        prefix += "."
    else:
        num = run[3:]
        prefix = "run"

    num = int(num)
    return num, prefix

def parse_run_helper(store, workspace, run, validate, actual_ws, run_names):
    if validate:
        ws, run_name, full_run_name = validate_run_name(store, workspace, run)

        run_names.append(run_name)
        actual_ws = ws
    else:
        run_names.append(run)
        if not actual_ws:
            actual_ws = workspace

    return actual_ws

def correct_slash(name):
    if "\\" in name:
        name = name.replace("\\", "/")
    return name

def parse_run_list(store, workspace, runs, validate=True):
    run_names = []
    actual_ws = None

    if runs:
        for run in runs:
            run = run.strip()
            run = correct_slash(run)

            if "/" in run:
                ws, run_name = run.split("/")
                if actual_ws and actual_ws != ws:
                    errors.syntax_error("Cannot mix run_names from different workspaces for this command")

            if not run.startswith("run"):
                errors.argument_error("run name", run)

            if "-" in run:
                # parse run range
                low, high = run.split("-")
                low, low_prefix = get_rightmost_run_num(low)
                high, high_prefix = get_rightmost_run_num(high)

                if low_prefix != high_prefix:
                    errors.syntax_error("for run name range, prefixes must match: {} vs. {}".format(low_prefix, high_prefix))

                for rx in range(low, high+1):
                    rxx = low_prefix + str(rx)
                    actual_ws = parse_run_helper(store, workspace, rxx, validate, actual_ws, run_names)
            else:
                actual_ws = parse_run_helper(store, workspace, run, validate, actual_ws, run_names)
    else:
        actual_ws = workspace
        
    #console.print("actual_ws=", actual_ws)
    return run_names, actual_ws   

def parse_run_name(workspace, run):
    actual_ws = None
    run_name = None

    run = correct_slash(run)
    if "/" in run:
        actual_ws, run_name = run.split("/")
    else:
        run_name = run
        actual_ws = workspace

    return run_name, actual_ws

def full_run_name(store_type, ws, run_name):
    #return "xt-{}://{}/{}".format(store_type, ws, run_name)
    run_name = correct_slash(run_name)
    if "/" in run_name:
        full_name = run_name
    else:
        full_name = "{}/{}".format(ws, run_name)
    return full_name

def is_simple_run_name(text):
    is_simple = isinstance(text, str) and text.startswith("run") and len(text) > 3 and text[3].isdigit()
    if not is_simple:
        # check for aml run_name:  exper.run34
        is_simple = isinstance(text, str) and ".run" in text
    return is_simple

def is_well_formed_run_name(text):
    well_formed = True
    if not "*" in text:
        text = correct_slash(text)
        if "/" in text:
            parts = text.split("/")
            if len(parts) != 2:
                well_formed = False
            elif not is_simple_run_name(parts[1]):
                well_formed = False
        elif not is_simple_run_name(text):
            well_formed = False
    return well_formed

def validate_run_name(store, ws, run_name, error_if_invalid=True, parse_only=False):
    run_name = correct_slash(run_name)
    if "/" in run_name:
        parts = run_name.split("/")
        if len(parts) != 2:
            errors.syntax_error("invalid format for run name: " + run_name)
        ws, run_name = parts

    run_name = run_name.lower()
    if not parse_only and not "*" in run_name:
        if not store.mongo.does_run_exist(ws, run_name):
            if error_if_invalid:
                errors.store_error("run '{}' does not exist in workspace '{}'".format(run_name, ws))
            else:
                return None, None, None
    return ws, run_name, ws + "/" + run_name

def build_metrics_sets(records, steps=None, merge=False, metrics=None):
    '''
    builds a collection of metrics sets.  A metric set is a set of metrics that have been reported together 
    in the run log.  Here 'together' means as a single log entry.

    args:
        'records' is the set of dict records of a run log.
        'steps' is an optional set of steps to filter by.
        'merge': when True, merge all datasets into a single one
        'metrics': list of specific metric names to extract
    '''
    # first step: put each metric into their own set (with time-stamped records)
    metric_sets_by_keys = {}
    step_index = None
    next_step = None
    step_name = None
    
    # for merge
    last_record = {}
    last_step = None
    merged_records = []

    if steps:
        step_index = 0
        next_step = steps[0]

    for log_dict in records:
        if not log_dict:
            continue

        if not "event" in log_dict or not "data" in log_dict or log_dict["event"] != "metrics":
            continue

        dd = log_dict["data"]
        
        if step_name is None:
            if constants.STEP_NAME in dd:
                step_name = dd[constants.STEP_NAME]
            elif "step" in dd:
                step_name = "step"
            elif "epoch" in dd:
                step_name = "epoch"

        if steps and step_name:
            # filter this record (skip if neq next_step)
            step_value = dd[step_name]

            while step_value > next_step:
                # compute next step
                step_index += 1
                if step_index < len(steps):
                    next_step = steps[step_index]
                else:
                    # found all specified steps
                    break

            if step_value < next_step:
                continue

        # add time to record
        dd[constants.TIME] = log_dict["time"]

        if metrics:
            # only collect step_name and metrics in "metrics"
            dd2 = {}
            dd2[step_name] = dd[step_name]
            for name, value in dd.items():
                if name in metrics:
                    dd2[name] = value

            # store back into dd
            dd = dd2

        if merge:
            if last_step == step_value:
                # add to last_record
                for name, value in dd.items():
                    last_record[name] = value
            else:
                merged_records.append(dd)
                last_record = dd
                last_step = step_value
        else:
            # collect into multiple metric sets
            keys = list(dd.keys())
            #keys.sort()
            keys_str = json.dumps(keys)

            if not keys_str in metric_sets_by_keys:
                metric_sets_by_keys[keys_str] = []

            metric_set = metric_sets_by_keys[keys_str]
            metric_set.append(dd)

    metric_sets = []

    if merge:
        # build set of keys that covers all records
        keys = {}
        for dd in merged_records:
            for name in dd:
                keys[name] = 1

        key_list = list(keys.keys())

        df = {"keys": key_list, "records": merged_records}
        metric_sets.append(df)
    else:
        for keys_str, records in metric_sets_by_keys.items():
            df = {"keys": json.loads(keys_str), "records": records}
            metric_sets.append(df)

    return metric_sets

def get_int_from_run_name(run_name):
    id = float(run_name[3:])*100000
    id = int(id)
    return id

def get_client_cs(core, ws, run_name):

    cs = None
    box_secret = None

    filter = {"_id": run_name}
    runs = core.store.mongo.get_info_for_runs(ws, filter, {"run_logs": 0})
    if not runs:
        errors.store_error("Unknown run: {}/{}".format(ws, run_name))

    if runs:
        from xtlib import job_helper

        run = runs[0]
        job_id = utils.safe_value(run, "job_id")
        node_index = utils.safe_value(run, "node_index")

        cs_plus = job_helper.get_client_cs(core, job_id, node_index)
        cs = cs_plus["cs"]
        box_secret = cs_plus["box_secret"]

    return cs, box_secret

def wrapup_runs_by_node(store, job_id, node_id, node_cancel_result):
    '''
    wrap up a run from azure batch.  run may have started, or may have completed.  
    '''
    # get job_record
    job_info = job_helper.get_job_record(store, job_id)
    ws_name = job_info["ws_name"]

    # loads the controller's MRC for context of this node
    text = store.read_job_file(job_id, constants.FN_MULTI_RUN_CONTEXT)
    mrc_data = json.loads(text)

    context_by_nodes = mrc_data["context_by_nodes"]
    context_plus = context_by_nodes[node_id]
    context = context_plus["runs"][0]
    
    # get runs that need wrapup in job
    node_index = utils.node_index(node_id)

    unwrapped = ["created", "queued", "spawning", "allocating", "running"]
    filter_dict = {"job_id": job_id, "node_index": node_index, "status":  {"$in": unwrapped}}
    fields_dict = {"log_records": 0}

    runs = store.mongo.get_info_for_runs(ws_name, filter_dict, fields_dict)

    for run in runs:
        wrapup_run_with_context(store, run, context)

    return runs

def wrapup_run_with_context(store, run, context_dict):
    context = utils.dict_to_object(context_dict)
    status = "cancelled"
    exit_code = 0
    node_id = utils.node_id(context.node_index)

    # use info from run, when possible (context is shared among all child runs)
    run_index = run["run_index"]
    run_name = run["run_name"]

    # these we don't have info for
    rundir = None    # unknown
    log = True
    capture = True

    store.wrapup_run(context.ws, run_name, context.aggregate_dest, context.dest_name, 
        status, exit_code, context.primary_metric, context.maximize_metric, context.report_rollup, 
        rundir, context.after_files_list, log, capture, job_id=context.job_id, node_id=node_id,
        run_index=run_index)    

def get_parent_run_number(name):
    num = 0
    if name and name.startswith("run"):
        part = name[3:]
        if "." in part:
            part = part.split(".")[0]
        num = int(part)

    return num