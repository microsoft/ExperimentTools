#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# mongo_db.py: functions that read/write mongo_db data
import os
import sys
import time
import json
import copy
import arrow
import shutil
import numpy as np
import logging

from xtlib import utils
from xtlib import errors
from xtlib import constants
from xtlib import file_utils

from xtlib.console import console

logger = logging.getLogger(__name__)

MONGO_INFO = "__mongo_info__"

class MongoDB():
    '''
    We use MongoDB to provide fast query access to a large collection of run data.
    '''
    def __init__(self, mongo_conn_str, run_cache_dir):
        if not mongo_conn_str:
            errors.internal_error("Cannot initialize MongoDB() with a empty mongo_conn_str")

        self.mongo_conn_str = mongo_conn_str
        self.run_cache_dir = run_cache_dir
        self.mongo_client = None
        self.mongo_db = None

        # keep a count of how many retryable errors we have encountered
        self.retry_errors = 0

        self.run_cache_dir = os.path.expanduser(run_cache_dir) if run_cache_dir else None

        # initialize mondo-db now
        self.init_mongo_db_connection()

    #---- UTILS ----

    def get_service_name(self):
        _, rest = self.mongo_conn_str.split("//", 1)
        name, _ = rest.split(":", 1)

        return name
        
    def init_mongo_db_connection(self):
        ''' create mongo_db on-demand since it has some startup overhead (multiple threads, etc.)
        '''
        if not self.mongo_db:
            if self.mongo_conn_str:
                from pymongo import MongoClient

                self.mongo_client = MongoClient(self.mongo_conn_str)

                # this will create the mongo database called "xtdb", if needed
                self.mongo_db = self.mongo_client["xtdb"]

    def get_mongo_info(self):
        cursor = self.mongo_with_retries("get_mongo_info", lambda: self.mongo_db[MONGO_INFO].find({"_id": 1}, None))
        records = list(cursor) if cursor else [] 
        record = records[0] if len(records) else None
        return record

    def set_mongo_info(self, info): 
        self.mongo_with_retries("set_mongo_info", lambda: self.mongo_db[MONGO_INFO].update( {"_id": 1}, info, upsert=True) )
        
    def remove_workspace(self, ws_name):
        self.remove_cache(ws_name)

        # remove associated mongo_db container
        container = self.mongo_db[ws_name]
        container.drop()
        count = container.count()

        console.diag("  after mongo_db container={} dropped, count={}=".format(container, count))

        # remove counters for this workspace
        cmd = lambda: self.mongo_db.ws_counters.remove( {"_id": ws_name} )
        self.mongo_with_retries("remove_workspace", cmd, ignore_error=True)

        # remove legacy counters for this workspace
        end_id = ws_name + "-end_id"
        cmd = lambda: self.mongo_db.ws_counters.remove( {"_id": end_id} )
        self.mongo_with_retries("remove_workspace", cmd)

    def remove_cache(self, ws_name):
        if self.run_cache_dir:
            # remove appropriate node of run_cache_dir
            cache_fn = os.path.expanduser(self.run_cache_dir) + "/" + constants.RUN_SUMMARY_CACHE_FN
            cache_fn = cache_fn.replace("$ws", ws_name)
            cache_dir = os.path.dirname(cache_fn)

            if os.path.exists(cache_dir):
                console.print("  zapping cache_dir=", cache_dir)
                file_utils.zap_dir(cache_dir)

    def init_workspace_counters(self, ws_name, next_run, next_end):
        update_doc = { "_id": ws_name, "next_run": next_run, "next_end": next_end, "next_child" : {} }

        cmd = lambda: self.mongo_db.ws_counters.find_and_modify( {"_id": ws_name}, update=update_doc, upsert=True)
        self.mongo_with_retries("init_workspace_counters", cmd)

    def delete_job(self, job_id):
        '''
        for use with "delete workspace" cmd, this only deletes
        the specified job (not its runs or related experiments).
        '''
        cmd_func = lambda: self.mongo_db["__jobs__"].delete_one( {"_id": job_id} )
        jobs = self.mongo_with_retries("delete_job", cmd_func)

    def get_next_sequential_job_id(self, default_next):
        jobs_collection = "__jobs__"
        path = "next_job"

        db = self.mongo_db

        # does a counters doc exit for this ws_name?
        cursor = db.ws_counters.find({"_id": jobs_collection}).limit(1)
        if not cursor.count():
            db.ws_counters.insert_one( {"_id": jobs_collection, path: default_next} )

        document = db.ws_counters.find_and_modify( {"_id": jobs_collection}, update={"$inc": {path: 1} }, new=False)
        next_id = document[path]

        return next_id

    def get_legacy_end_id(self, ws_name):
        db = self.mongo_db
        doc_id = ws_name + "-end_id"
        cursor = db.ws_counters.find({"_id": doc_id}).limit(1)
        last_id = utils.safe_cursor_value(cursor, "last_id")
        return last_id

    def get_next_sequential_ws_id(self, ws_name, path, default_next_run):
        db = self.mongo_db

        assert not "/" in ws_name 
        assert not "/" in path 
        
        console.diag("ws={}, path={}, default_next_run={}".format(ws_name, path, default_next_run))

        # does a counters doc exist for this ws_name?
        cursor = db.ws_counters.find({"_id": ws_name}).limit(1)
        if not cursor.count():
            console.diag("LEGACY ws={} found in get_next_sequential_ws_id".format(ws_name))

            # we need BOTH next_run and next_end for a new record 
            last_id = self.get_legacy_end_id(ws_name)
            default_next_end = 1 + last_id if last_id else 1

            info = {"_id": ws_name, "next_run": default_next_run, "next_end": default_next_end, "next_child": {}}
            db.ws_counters.insert_one( info )

        document = db.ws_counters.find_and_modify( {"_id": ws_name}, update={"$inc": {path: 1} }, new=False)
        next_id = utils.safe_nested_value(document, path)

        if not next_id:
            # child id's start at 0; if we got that, skip it and get next one
            document = db.ws_counters.find_and_modify( {"_id": ws_name}, update={"$inc": {path: 1} }, new=False)
            next_id = utils.safe_nested_value(document, path)
     
        return next_id

    def get_next_job_id(self, default_next=1):
        return self.get_next_sequential_job_id(default_next)

    def get_next_run_id(self, ws_name, default_next=1):
        return self.get_next_sequential_ws_id(ws_name, "next_run", default_next)

    def get_next_child_id(self, ws_name, run_name, default_next=1):
        document = self.mongo_db["__next_child__"].find_and_modify( {"run_name": run_name, "ws_name": ws_name}, update={"$inc": {"next_id": 1} }, new=True, upsert=True)
        return utils.safe_nested_value(document, 'next_id')
        
    def get_next_end_id(self, ws_name, default_next_run=1):
        return self.get_next_sequential_ws_id(ws_name, "next_end", default_next_run)

    def mongo_with_retries(self, name, mongo_cmd, ignore_error=False):
        retry_count = 25
        result = None
        import pymongo.errors

        for i in range(retry_count):
            try:
                result = mongo_cmd()
                break
            # watch out for these exceptions: AutoReconnect, OperationFailure (and ???)
            except BaseException as ex:   # pymongo.errors.OperationFailure as ex:
                
                # since we cannot config logger to supress stderr, don't log this
                #logger.exception("Error in mongo_with_retries, ex={}".format(ex))
                
                # pymongo.errors.OperationFailure: Message: {"Errors":["Request rate is large"]}
                if ignore_error:
                    console.print("ignoring mongo-db error: name={}, ex={}".format(name, ex))
                    break
                
                if i == retry_count-1:
                    # we couldn't recover - signal a hard error/failure
                    raise ex

                # we get hit hard on the "Request rate is large" errors when running 
                # large jobs (500 simultaneous runs), so beef up the backoff times to
                # [1,61] so we don't die with a hard failure here
                if i == 0:
                    backoff = 1 + 10*np.random.random()
                    self.retry_errors += 1
                else:
                    backoff = 1 + 60*np.random.random()

                ex_code = ex.code if hasattr(ex, "code") else ""
                ex_msg = str(ex)[0:60]+"..."

                console.print("retrying mongo-db: name={}, retry={}/{}, backoff={:.2f}, ex.code={}, ex.msg={}".format(name, i+1, retry_count, backoff, 
                    ex_code, ex_msg))
                    
                time.sleep(backoff)
                
        return result

    #---- RUNS ----

    def create_mongo_run(self, dd):
        # create run document on Mongo DB
        # copy standard CREATE properties
        run_doc = copy.deepcopy(dd)

        # zap a few we don't want
        if "event" in run_doc:
            del run_doc["event"]

        if "time" in run_doc:
            del run_doc["time"]

        # add some new ones
        is_azure = utils.is_azure_batch_box(dd["box_name"])

        run_doc["_id"] = dd["run_name"]
        run_doc["status"] = "allocating" if is_azure else "created"
        run_doc["duration"] = 0
        
        # add the new RUN document
        ws_name = dd["ws"]

        cmd = lambda: self.mongo_db[ws_name].insert_one(run_doc)
        self.mongo_with_retries("create_mongo_run", cmd, ignore_error=True)

    def add_run_event(self, ws_name, run_name, log_record):

        self.add_log_record_from_dict(ws_name, run_name, log_record)
        
        event_name = log_record["event"]
        data_dict = log_record["data"]
        updates = {}

        if event_name == "hparams":
            # create a "hparams" dict property for the run record
            self.flatten_dict_update(updates, "hparams", data_dict)
            self.update_mongo_run_from_dict(ws_name, run_name, updates)

        elif event_name == "metrics":
            # create a "metrics" dict property for the run record (most recent metrics)
            self.flatten_dict_update(updates, "metrics", data_dict)
            self.update_mongo_run_from_dict(ws_name, run_name, updates)

        if event_name == "started":
            updates = { "status": "running" }
            #console.print("updating run STATUS=", updates)
            self.update_mongo_run_from_dict(ws_name, run_name, updates)

        elif event_name == "status-change":
            updates = { "status": data_dict["status"] }
            #console.print("updating run STATUS=", updates)
            self.update_mongo_run_from_dict(ws_name, run_name, updates)

    def flatten_dict_update(self, updates, dd_name, dd):
        for key, value in dd.items():
            updates[dd_name + "." + key] = value

    def update_mongo_run_at_end(self, ws_name, run_name, status, exit_code, restarts, end_time, log_records, hparams, metrics):
        # update run document on Mongo DB
        #run_doc = self.mongo_db[ws_name].find_one( {"_id": run_name} )
        # update properties
        updates = {}
        updates["status"] = status
        updates["exit_code"] = exit_code
        updates["restarts"] = restarts
        updates["end_time"] = end_time

        # add the unique end_id (relative to ws_name)
        updates["end_id"] = self.get_next_end_id(ws_name)

        # structured properties
        if hparams:
            #updates["hparams"] = hparams
            self.flatten_dict_update(updates, "hparams", hparams)

        if metrics:
            #updates["metrics"] = metrics
            self.flatten_dict_update(updates, "metrics", metrics)
        
        # no longer need this step here (log records are now appended as they are logged)
        #updates["log_records"] = log_records

        self.update_mongo_run_from_dict(ws_name, run_name, updates)

    def add_log_record_from_dict(self, ws_name, run_name, log_record):
        log_record['run_id'] = run_name
        log_record['ws_name'] = ws_name

        self.mongo_with_retries("add_log_record_from_dict", lambda: self.mongo_db["__log_records__"].insert_one(log_record))

    def update_mongo_run_from_dict(self, ws_name, run_name, dd):
        #console.print("update_mongo_run_from_dict: ws_name={}, run_name={}, dd={}".format(ws_name, run_name, dd))

        update_dd = copy.deepcopy(dd)
        update_dd["last_time"] = utils.get_time()

        update_doc = { "$set": update_dd}

        #console.print("update_mongo_run_from_dict: ws_name={}, run_name={}, update_doc={}".format(ws_name, run_name, update_doc))

        # do a REPLACE DOC update operation
        self.mongo_with_retries("update_mongo_run_from_dict", lambda: self.mongo_db[ws_name].update_one( {"_id": run_name}, update_doc) )

    def does_run_exist(self, ws, run_name):
        records = self.get_info_for_runs(ws, {"_id": run_name}, {"_id": 1})
        exists = len(records) == 1
        return exists

    def get_info_for_runs(self, ws_name, filter_dict, fields_dict=None):

        # filter_dict = {}
        # filter_dict["run_name"] = {"$in": run_names}

        cursor = self.mongo_with_retries("get_boxes_for_runs", lambda: self.mongo_db[ws_name].find(filter_dict, fields_dict))
        run_records = list(cursor) if cursor else []

        console.diag("after get_boxes_for_runs()")        
        return run_records

    def get_all_experiments_in_ws(self, ws_name):
        # cannot get "distinct" command to work ("command not supported")
        #cursor = db["__jobs__"].distinct("ws_name") 

        cursor = self.mongo_with_retries("get_all_experiments_in_ws", lambda: self.mongo_db["__jobs__"].find({"ws_name": ws_name}, {"exper_name": 1}) )
        exper_names = [rec["exper_name"] for rec in cursor if "exper_name" in rec]
        exper_names = list(set(exper_names))   # remove dups

        console.diag("after get_all_experiments()")        
        return exper_names

    def get_ws_runs(self, ws_name, filter_dict=None, include_log_records=False, first_count=None, last_count=None, sort_dict=None):
        '''
        design issue: we cannot use a single cache file for different filter requests.  Possible fixes:
            - do not cache here (current option)
            - name cache by filter settings (one cache file per setting) - not ideal
            - keep all runs for ws in cache and apply filter locally (TODO: this option)
        '''
        if include_log_records:
            fn_cache = self.run_cache_dir + "/" + constants.ALL_RUNS_CACHE_FN
        else:
            fn_cache = self.run_cache_dir + "/" + constants.RUN_SUMMARY_CACHE_FN

        fn_cache = fn_cache.replace("$aggregator", ws_name)

        return self.get_all_runs(None, ws_name, None, filter_dict, fields_dict, use_cache=False, fn_cache=fn_cache, first_count=first_count, 
            last_count=last_count, sort_dict=sort_dict)

    def get_all_runs(self, aggregator_dest, ws_name, job_or_exper_name, filter_dict=None, fields_dict=None, use_cache=True, 
        fn_cache=None, first_count=None, last_count=None, sort_dict=None):
        '''
        cache design: 
            - organized all cached run information by the way it was accessed: a folder for each workspace (created on demand), 
              and under each, a folder specifying the filter_dict and fields_dict.  This way, we only use cache records for
              exactly matching query info.

            - whenever sort, first_count, or last_count is used (that is, included in the mongo db query), we should set "use_cache" to False.

            - note: since Azure Cosmos version of mongo-db doesn't correctly support sort/first/last (totally busted as of Aug 2019), we never
              include sort/first/last in mongo db query.

            - as of 12/20/2019, the only code that correctly uses the fn_cache is hparam_search.  all other code should call with use_cache=False.
        '''
        # PERF-critical function 
        # below code not yet cache-compliant
        use_cache = False

        records = []
        target = 0
        cache = None

        if use_cache and not fn_cache:
            # fn_cache = self.run_cache_dir + "/" + constants.ALL_RUNS_CACHE_FN
            # fn_cache = fn_cache.replace("$aggregator", ws_name)
            use_cache = False      # play it safe for now

        if use_cache and os.path.exists(fn_cache):
            # read CACHED runs
            started = time.time()
            cache = utils.load(fn_cache)
            elapsed = time.time() - started

            target = max([rec["end_id"] if "end_id" in rec else 0 for rec in cache])
            console.print("loaded {:,} records in {:.2f} secs from cache: {}".format(len(cache), elapsed, fn_cache))

        if not filter_dict:
            if aggregator_dest == "job":
                filter_dict = {"job_id": job_or_exper_name}
            elif aggregator_dest == "experiment":
                filter_dict = {"exper_name": job_or_exper_name}

        # if not fields_dict:
        #     # by default, do NOT return inner log records
        #     fields_dict = {"log_records": 0}

        # adjust filter to get only missing records
        if target:
            filter_dict["end_id"] = {"$gt": target}

        #console.print("  mongo: filter: {}, fields: {}, sort: {}".format(filter_dict, fields_dict, sort_dict))
        console.diag("  mongo: filter: {}, fields: {}".format(filter_dict, fields_dict))

        # limit query to avoid "message max exceeded" errors
        max_query_records = 3000  
        started = time.time()

        #records = self.mongo_db[ws_name].find(filter_dict, fields_dict)  
        cmd_func = lambda: self.mongo_db[ws_name].find(filter_dict, fields_dict)
        cursor = self.mongo_with_retries("get_all_runs", cmd_func)

        # SORT TOTALLY BUSTED ON COSMOS: 
        #   - sort of "-id" returns random order each time
        #   - sort of "test-acc" returns 0 records (if ANY missing values, NO records returned)
        #   - docs say pass a dict, but code wants list of 2-tuples (pymongo library)

        # if sort_dict:
        #     items = list(sort_dict.items())
        #     key, value = items[0]
        #     import pymongo
        #     cursor = cursor.sort("job", 1)  # key, value)

        # adjust cursor per first_count, last_count

        # because SORT is busted, we can't use mongo for first/last either
        # if last_count:
        #     if last_count is True:
        #         last_count = 25
        #     avail = cursor.count()
        #     skip_count = avail - last_count
        #     if skip_count > 0:
        #         cursor = cursor.skip(skip_count)
        # elif first_count:
        #     if first_count is True:
        #         first_count = 25
        #     cursor = cursor.limit(first_count)

        records = list(cursor)

        return_count = len(records)
        total_count = self.mongo_db[ws_name].count()

        elapsed = time.time() - started
        console.diag("  mongo query returned {} records (of {}), took: {:2f} secs".format(return_count, total_count, elapsed))

        if cache:
            cache += records
            records = cache

        if return_count and use_cache:
            # write to cache 
            started = time.time()
            utils.save(records, fn_cache)
            elapsed = time.time() - started
            console.print("wrote {:,} records to cache, took: {:2f} secs".format(len(records), elapsed))

        return records

    def update_run_info(self, ws_name, run_id, dd, clear=False, upsert=True):
        if clear:
            update_doc = { "$unset": dd}
        else:
            update_doc = { "$set": dd}

        # update, create prop if needed
        self.mongo_with_retries("update_run_info", lambda: self.mongo_db[ws_name].update_one( {"_id": run_id}, update_doc, upsert=upsert) )

    def update_runs_from_filter(self, ws_name, filter, dd, clear=False, upsert=True):
        if clear:
            update_doc = { "$unset": dd}
        else:
            update_doc = { "$set": dd}

        # update, create prop if needed
        result = self.mongo_with_retries("update_runs_from_filter", lambda: self.mongo_db[ws_name].update_many( filter, update_doc, upsert=upsert) )
        return result

    #---- JOBS ----

    def does_jobs_exist(self):
        # does document for ws_name exist?
        job_id = "job1"
        cmd = lambda: self.mongo_db["__jobs__"].find({"_id": job_id}, {"_id": 1}).limit(1)
        cursor = self.mongo_with_retries("does_jobs_exist", cmd)
        found = bool(cursor and cursor.count)

        return found

    def get_info_for_jobs(self, filter_dict, fields_dict=None):

        cursor = self.mongo_with_retries("get_info_for_jobs", lambda: self.mongo_db["__jobs__"].find(filter_dict, fields_dict))
        job_records = list(cursor) if cursor else []

        console.diag("after get_info_for_jobs()")        
        return job_records

    def get_active_runs(self, job_id, run_index=None):
        records = self.mongo_with_retries("get_active_runs", lambda: self.mongo_db["__active_runs__"].find( {"job_id": job_id, "run_index": run_index}), return_records=True)
        console.diag("after get_active_runs")

        return records

    def get_runs_by_box(self, job_id, box_id=None):
        if box_id:
            records = self.mongo_with_retries("get_runs_by_box", lambda: self.mongo_db["__get_runs_by_box__"].find( {"job_id": job_id, "box_id": box_id}), return_records=True)
        else:
            records = self.mongo_with_retries("get_runs_by_box", lambda: self.mongo_db["__get_runs_by_box__"].find( {"job_id": job_id}), return_records=True)

        console.diag("after get_runs_by_box()")        
        return records

    def get_service_info_by_node(self, job_id, node_id=None):
        if node_id:
            records = self.mongo_with_retries("get_service_info_by_node", lambda: self.mongo_db["__service_info_by_node__"].find( {"job_id": job_id, "node_id": node_id}), return_records=True)
        else:
            records = self.mongo_with_retries("get_service_info_by_node", lambda: self.mongo_db["__service_info_by_node__"].find( {"job_id": job_id}), return_records=True)

        console.diag("after get_service_info_by_node")

        return records

    def get_service_job_info(self, job_id):
        records = self.mongo_with_retries("get_service_job_info", lambda: self.mongo_db["__service_job_info__"].find( {"job_id": job_id}), return_records=True)
        console.diag("after get_service_job_info")

        return records

    def update_job_info(self, job_id, dd, clear=False, upsert=True):
        if clear:
            update_doc = { "$unset": dd}
        else:
            update_doc = { "$set": dd}

        # update, create if needed
        self.mongo_with_retries("update_job_info", lambda: self.mongo_db["__jobs__"].update_one( {"_id": job_id}, update_doc, upsert=upsert) )

    def get_job_names(self, filter_dict=None):
        job_names = []
        fields_dict = {"_id": 1}
        
        cmd_func = lambda: self.mongo_db["__jobs__"].find(filter_dict, fields_dict)
        cursor = self.mongo_with_retries("get_job_names", cmd_func)
        if cursor:
            jobs = list(cursor)

            # filter out just the names
            job_names = [ job["_id"] for job in jobs]

        return job_names

    def get_job_workspace(self, job_id):
        ''' returns name of workspace associated with job'''
        ws_name = None

        # does document for ws_name exist?
        cmd = lambda: self.mongo_db["__jobs__"].find({"_id": job_id}, {"ws_name": 1}).limit(1)
        cursor = self.mongo_with_retries("get_job_workspace", cmd)

        if cursor and cursor.count():
            result = list(cursor)[0]
            if "ws_name" in result:
                ws_name = result["ws_name"]

        return ws_name

    def get_run_property(self, ws_name, run_name, prop_name):
        cmd = lambda: self.mongo_db[ws_name].find( {"_id": run_name}, {prop_name: 1})
        cursor = self.mongo_with_retries("get_run_property", cmd)

        value = utils.safe_cursor_value(cursor, prop_name)
        return value
        
    def get_job_property(self, job_id, prop_name):
        cmd = lambda: self.mongo_db["__jobs__"].find( {"_id": job_id}, {prop_name: 1})
        cursor = self.mongo_with_retries("get_job_property", cmd)

        value = utils.safe_cursor_value(cursor, prop_name)
        return value

    def job_node_start(self, job_id):
        '''
        A job's node has started running.  We need to:
            - increment the job's "running_nodes" property
            - set the "job_status" property to "running"
        '''
        cmd = lambda: self.mongo_db["__jobs__"].find_and_modify( {"_id": job_id}, update={"$inc": {"running_nodes": 1} })
        self.mongo_with_retries("job_node_start", cmd)

        cmd = lambda: self.mongo_db["__jobs__"].find_and_modify( {"_id": job_id}, update={"$set": {"job_status": "running"} })
        self.mongo_with_retries("job_node_start", cmd)

    def job_node_exit(self, job_id):
        '''
        A job's node has finished running.  We need to:
            - decrement the job's "running_nodes" property 
            - if running_nodes==0, set the "job_status" property to "completed"
        '''
        cmd = lambda: self.mongo_db["__jobs__"].find_and_modify( {"_id": job_id}, update={"$inc": {"running_nodes": -1} })
        self.mongo_with_retries("job_node_exit", cmd)

        cmd = lambda: self.mongo_db["__jobs__"].find_and_modify( {"_id": job_id, "running_nodes": 0}, update={"$set": {"job_status": "completed"} })
        self.mongo_with_retries("job_node_exit", cmd)

    def update_connect_info_by_node(self, job_id, node_id, connect_info):
        key = "connect_info_by_node." + node_id
        update_doc = { "$set": {key: connect_info} }
        self.mongo_with_retries("update_connect_info_by_node", lambda: self.mongo_db["__jobs__"].update_one( {"_id": job_id}, update_doc) )

    def job_run_start(self, job_id):
        '''
        A job's run has started running.  We need to:
            - increment the job's "running_runs" property 
        '''
        cmd = lambda: self.mongo_db["__jobs__"].find_and_modify( {"_id": job_id}, update={"$inc": {"running_runs": 1} })
        self.mongo_with_retries("job_run_start", cmd)

    def job_run_exit(self, job_id, exit_code):
        '''
        A job's run has finished running.  We need to:
            - decrement the job's "running_runs" property 
            - increment the job's "completed_runs" property
            - if exit_code != 0, increment the job's "error_runs" property
        '''
        error_inc = 1 if exit_code else 0
        cmd = lambda: self.mongo_db["__jobs__"].find_and_modify( {"_id": job_id}, update={"$inc": {"running_runs": -1, "completed_runs": 1, "error_runs": error_inc} })
        self.mongo_with_retries("job_run_exit", cmd)

    def run_start(self, ws_name, run_name):
        '''
        A run has started running.  We need to:
            - set the run "start_time" property to NOW
            - set the run "queue_duration" property to NOW - created_time
        '''
        now = arrow.now()
        now_str = str(now)

        # get create_time of run
        cmd = lambda: self.mongo_db[ws_name].find({"_id": run_name}, {"create_time": 1})
        cursor = self.mongo_with_retries("run_start", cmd)

        doc = cursor.next()
        if doc and "create_time" in doc:
            create_time_str = doc["create_time"]
            create_time = arrow.get(create_time_str)

            # compute time in "queue" 
            queue_duration = utils.time_diff(now, create_time)

            cmd = lambda: self.mongo_db[ws_name].find_and_modify( {"_id": run_name}, update={"$set": {"start_time": now_str, "queue_duration": queue_duration} })
            self.mongo_with_retries("run_start", cmd)

    def run_exit(self, ws_name, run_name):
        '''
        A run has finished running.  We need to:
            - set the run "run_duration" property to NOW - start_time
        '''
        now = arrow.now()
        now_str = str(now)

        # get start_time of run
        cmd = lambda: self.mongo_db[ws_name].find({"_id": run_name}, {"start_time": 1})
        cursor = self.mongo_with_retries("run_exit", cmd)

        doc = cursor.next()
        if doc and "start_time" in doc:
            start_time_str = doc["start_time"]
            start_time = arrow.get(start_time_str)

            # compute run_duration 
            run_duration = utils.time_diff(now, start_time)

            cmd = lambda: self.mongo_db[ws_name].find_and_modify( {"_id": run_name}, update={"$set": {"run_duration": run_duration} })
            self.mongo_with_retries("run_exit", cmd)
