#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# repair_runs.py: code moved from list_builder; currently not used
import logging

logger = logging.getLogger(__name__)


class RepairRuns():

    def validate_unfinished_records(self, ws, records_by_run, ask_boxes_status=True):
        status_dict = {}
        unfinished_by_box = {}
        count = 0
        init_status = None   # if detect_and_repair else "running"  

        for key, records in records_by_run.items():
            #console.print("run=", key)

            if len(records) == 1:
                first_record = records[0]
                #console.print("\nfirst_record=", first_record)
                box_name = first_record["box_name"]
                run_name = first_record["run_name"]
                exper_name = first_record["exper_name"]
                #console.print("unfinished run=", run_name)

                if not box_name in unfinished_by_box:
                    unfinished_by_box[box_name] = []

                unfinished_by_box[box_name].append(run_name)
                status_dict[run_name] = {"status": init_status, "exper_name": exper_name}     # default
                count += 1

        if count and ask_boxes_status:
            # workaround for not being able to "import client" in this file (cyclic import)
            xt_client = self.client.create_new_client(self.config)

            #console.print("validating {} unfinished runs in workspace '{}'".format(count, ws))

            for box_name, run_names in unfinished_by_box.items():
                box_status_dict = self.get_run_status_from_box(xt_client, ws, box_name, run_names)

                if box_status_dict:
                    # add box_status_dict to status_dict
                    for key, value in box_status_dict.items():
                        status_dict[key]["status"] = value

        #console.print("status_dict=", status_dict)
        return status_dict

    def get_run_status_from_azure_box(self, box_name, run_names):
        box_status_dict = {}
        job_id = box_name.split("-")[0]
        
        from .backends.backend_batch import AzureBatch
        job = AzureBatch(core=self.core)
        
        status = job.get_job_status(job_id)
        #console.print("job_id=", job_id, ", status=", status)

        for run_name in run_names:
            box_status_dict[run_name] = status

        return box_status_dict

    def get_run_status_from_box(self, xt_client, ws, box_name, run_names):
        box_status_dict = None
        try:
            if utils.is_azure_batch_box(box_name):
                box_status_dict = self.get_run_status_from_azure_box(box_name, run_names)
            else:
                if not pc_utils.is_localhost(box_name) and not \
                    self.config.get("boxes", box_name, default_value=None, suppress_warning=True):
                        console.print("  skipping unknown box=", box_name)
                elif not xt_client.connect_to_controller(box_name):
                    console.print("  skipping unreachable box=", box_name)
                else:
                    box_status_dict = xt_client.get_status_of_runs(ws, run_names)
        except BaseException as ex:
            logger.exception("Error in get_run_status_from_box, ex={}".format(ex))
            console.print("exception raised by box={}: {}".format(box_name, ex))
            if self.config.get("internal", "raise"):
                raise ex   
        
        return box_status_dict
        
    def repair_phantom_runs(self, ws_name, status_dict):
        #console.print("status_dict=", status_dict)

        metric_rollup_dict = self.config.get("metrics", None)
        count = 0
        dry_run = self.config.get("general", "dry-run")

        for run_name, dd in status_dict.items():
            status = dd["status"]
            aggregate_dest = self.config.get("hyperparameter-search", "aggregate-dest")

            if aggregate_dest == "experiment" and "exper_name" in dd:
                dest_name = dd["exper_name"]
            elif aggregate_dest == "job" and "job" in dd:
                dest_name = dd["job"]
            else:
                dest_name = None

            if status is None:
                if dry_run:
                    console.print("  (dry-run) repairing phantom run: {}".format(run_name))
                else:
                    console.print("  repairing phantom run: {}".format(run_name))
                    self.store.rollup_and_end_run(ws_name, run_name, aggregate_dest, dest_name, "aborted", None, \
                        metric_rollup_dict, use_last_end_time=True)
                    count += 1
        return count
