#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# mongo_run_index.py: mongo functions that specialize in run_index management
import os
import sys
import time
import json
import copy
import uuid
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

class MongoRunIndex():
    '''
    Goal: a simple, reliable, atomic-based way to allocate the next child run 
    index for a node, with restart support.  Support both static and dynamic scheduling.
    '''
    def __init__(self, mongo, job_id, parent_run_name, node_id, new_session=True):
        self.mongo = mongo
        self.job_id = job_id
        self.parent_run_name = parent_run_name
        self.node_id = node_id
        self.ws_name = self._get_job_property("ws_name")
        self.schedule = self._get_job_property("schedule")

        if new_session:
            self._restart_runs_for_node()

    def _restart_runs_for_node(self):
        '''
        non-atomic update of all active runs for this node: set to constants.WAITING
        '''
        elem_dict = {"node_id": self.node_id, "status": {"$in": [constants.STARTED, constants.RESTARTED]}}
        fd = {"_id": self.job_id, "active_runs": {"$elemMatch": elem_dict}}

        while True:
            # this will only update a single array entry at a time (using mongo 3.2)
            cmd = lambda: self.mongo.mongo_db["__jobs__"].find_and_modify(fd , update={"$set": {"active_runs.$.status": constants.WAITING}}, new=True)
            dd = self.mongo.mongo_with_retries("_restart_runs_for_node", cmd)

            if not dd:
                break
            console.print("_restart_runs_for_node: found a run on node=" + self.node_id)

    def get_next_child_run(self):
        if self.schedule == "static":
            entry = self._get_next_child_static()
        else:
            entry = self._get_next_child_dynamic()

        return entry

    def mark_child_run_completed(self, entry):
        console.print("marking child run complete: entry={}".format(entry))
        run_index = entry["run_index"]

        # optional assert
        ar = self._get_job_property("active_runs")
        ent = utils.find_by_property(ar, "run_index", run_index)
        
        if ent["status"] == constants.COMPLETED:
            errors.internal_error("mark_child_run_completed: run already marked completed: {}".format(ent))

        fd = {"_id": self.job_id, "active_runs.run_index": run_index}

        # mark entry as constants.COMPLETED
        cmd = lambda: self.mongo.mongo_db["__jobs__"].find_and_modify(fd , update={"$set": {"active_runs.$.status": constants.COMPLETED}})
        self.mongo.mongo_with_retries("mark_child_run_completed", cmd)
        
    def _get_next_child_name(self):
         child_number = self.mongo.get_next_child_id(self.ws_name, self.parent_run_name)
         run_name = self.parent_run_name + "." + str(child_number)
         return run_name

    def _get_next_child_static(self):
        # look for a constants.WAITING entry to restart
        entry = self._get_first_entry( filter={"node_id": self.node_id, "status": constants.WAITING}, update={"status": constants.RESTARTED})
        if not entry:

            # look for an constants.UNSTARTED entry to start
            run_name = self._get_next_child_name()
            entry = self._get_first_entry( filter={"node_id": self.node_id, "status": constants.UNSTARTED}, update={"status": constants.STARTED, "run_name": run_name})

        return entry

    def _get_next_child_dynamic(self):
        # look for a constants.WAITING entry to restart
        entry = self._get_first_entry( filter={"status": constants.WAITING}, update={"node_id": self.node_id, "status": constants.RESTARTED})
        if not entry:

            # look for an constants.UNSTARTED entry to start
            run_name = self._get_next_child_name()
            entry = self._get_first_entry( filter={"status": constants.UNSTARTED}, update={"node_id": self.node_id, "status": constants.STARTED, "run_name": run_name})

        return entry

    def _get_job_property(self, prop_name):
        cmd = lambda: self.mongo.mongo_db["__jobs__"].find( {"_id": self.job_id}, {prop_name: 1})
        cursor = self.mongo.mongo_with_retries("_get_job_property", cmd)

        value = utils.safe_cursor_value(cursor, prop_name)
        return value

    def _get_first_entry(self, filter, update):
        # build filter dictionary for caller's nested properties
        fd = {"_id": self.job_id}

        em = {}
        for name, value in filter.items():
            em[name] = value

        # must use $elemMatch to match an array element with multiple conditions
        fd["active_runs"] = {"$elemMatch": em}

        # mongodb workaround: since $ projection operator not working with find_and_modify(),
        # we add a unique id (guid) so we know which element we have updated
        guid = str(uuid.uuid4())
        update["guid"] = guid

        # build update dictionary for caller's nested properties
        ud = {}
        for name, value in update.items():
            key = "active_runs.$.{}".format(name)
            ud[key] = value

        cmd = lambda: self.mongo.mongo_db["__jobs__"].find_and_modify(fd, update={"$set": ud}, fields={"active_runs": 1}, new=True)
        result = self.mongo.mongo_with_retries("_get_first_entry", cmd)

        if result:
            active_runs = result["active_runs"]
            result = utils.find_by_property(active_runs, "guid", guid)

        return result

# flat functions
def build_active_runs(schedule, run_count, node_count):
    entries = []

    if schedule == "dynamic":
        # DYNAMIC schedule
        for ri in range(run_count):
            entry = {"run_index": ri, "run_name": None, "node_id": None, "status": "unstarted"}
            entries.append(entry)
    else:
        # STATIC schedule (distribute over nodes)
        node_index = 0

        for ri in range(run_count):
            node_id = "node" + str(node_index)
            entry = {"run_index": ri, "run_name": None, "node_id": node_id, "status": "unstarted"}
            entries.append(entry)

            node_index += 1
            if node_index >= node_count:
                node_index = 0

    return entries