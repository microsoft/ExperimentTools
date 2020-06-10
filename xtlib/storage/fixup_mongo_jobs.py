#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# fixup_mongo_jobs.py: add "job_num" to JOB collection records, as needed
import pymongo
import time

from xtlib import console
from xtlib import job_helper

batch_size = 100

def process_job_batch(collection, records):
    '''
    due to UPDATE RATE restrictions on MongoDB/Cosmos, we must process in 
    batches (not all at once)
    '''
    updates = []

    for record in records:
        job_id = record["_id"]
        if not job_id or not job_helper.is_job_id(job_id):
            continue

        job_num = int(job_id[3:])

        fd = {"_id": job_id}
        ud = {"$set": {"job_num": job_num}}

        update = pymongo.UpdateOne(fd, ud)
        updates.append(update)

    # write batch
    if len(updates):
        collection.bulk_write(updates)

def fixup_jobs_if_needed(client):
    collection = client["__jobs__"]
    updated_count = 0

    while True:
        # build next batch of original records where JOB_ID is defined but JOB_NUM is not
        cursor = collection.find( {"job_id": {"$exists": True}, "job_num": {"$exists": False}} , {"_iid": 1}).limit(batch_size)
        records = list(cursor)
        if len(records) == 0:
            break

        if updated_count == 0:
            console.print("found mongo-db JOB records written by older version of XT; upgrading them to new format...")

        process_job_batch(collection, records)
        updated_count += len(records)
        console.print("update progress=", updated_count)

    if updated_count:
        console.print("upgrade complete (updated {:,} records)".format(updated_count))

