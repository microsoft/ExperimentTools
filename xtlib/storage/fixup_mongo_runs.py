#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# fixup_mongo_runs.py: fixup runs by adding the "run_num" field to documents that need it (in the specified collection)

import pymongo
import time

from xtlib import console

batch_size = 100

def process_run_batch(collection, records):
    updates = []

    for record in records:
        run_name = record["_id"]
        if ".run" in run_name:
            # obsolete format: experiment.run_name
            _, run_name = run_name.split(".", 1)

        if not run_name or not run_name.startswith("run"):
            # unrecognized format, just group all of these a -1
            run_num = -1
        else:
            base = run_name[3:]

            if "." in base:
                parent, child = base.split(".")
                # allow for 1 million 
                run_num = 1000*1000*int(parent) + int(child)
            else:
                run_num = 1000*1000*int(base)

        fd = {"_id": record["_id"]}
        ud = {"$set": {"run_num": run_num}}

        update = pymongo.UpdateOne(fd, ud)
        updates.append(update)

    # write batch
    if len(updates):
        collection.bulk_write(updates)

def fixup_runs_if_needed(client, workspace):
    collection = client[workspace]
    updated_count = 0

    # count = collection.count()
    # console.print("collection count=", count)

    while True:
        # get next batch of original records
        #cursor = collection.find( {"run_name": {"$exists": True}, "run_num": {"$exists": False}} , {"_iid": 1}).limit(batch_size)
        cursor = collection.find( {"run_name": {"$exists": True}, "run_num": 0} , {"_iid": 1}).limit(batch_size)
        records = list(cursor)
        if len(records) == 0:
            break

        if updated_count == 0:
            console.print("found mongo-db RUN records written by older version of XT; upgrading them to new format...")

        process_run_batch(collection, records)
        updated_count += len(records)
        console.print("update progress=", updated_count)

    if updated_count:
        console.print("upgrade complete (updated {:,} records)".format(updated_count))
