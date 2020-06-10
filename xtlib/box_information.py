#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# box_information.py: returns info about the specified box_name
import json

from xtlib import qfe
from xtlib import utils
from xtlib import errors
from xtlib import pc_utils
from xtlib import box_secrets

from xtlib.console import console
from xtlib.backends.backend_batch import AzureBatch

class BoxInfo():
    def __init__(self, config, box_name, store, pool_info=None, is_batch_pool=None, args=None):
        self.config = config
        self.box_name = box_name

        self._set_box_info(box_name, store, pool_info, is_batch_pool, args)

    def _get_pool_info(self, box_name, store):
        pool_info = None

        # extract job from box_name
        job_id = box_name.split("-")[0]
        # get pool from job
        text = store.read_job_info_file(job_id)
        if text:        
            job_info = json.loads(text)
            pool_info = utils.safe_value(job_info, "pool_info")
        return pool_info

    def _set_box_info(self, box_name, store, pool_info, is_batch_pool, args):

        fake_submit = args["fake_submit"] if args else False

        if utils.is_azure_ml_box(box_name):
            self.box_class = "azureml" 
            self.box_os = "linux"
            self.address = None
            self.max_runs = 1
        elif utils.is_azure_batch_box(box_name):
            if not pool_info:
                if fake_submit:
                    pool_info = {"box-class": "dsvm", "os": "linux"}
                else:
                    pool_info = self._get_pool_info(box_name, store)
            self.box_class = pool_info["box-class"] if pool_info and "box-class" in pool_info else "dsvm" 
            self.box_os = pool_info["os"] if pool_info and "os" in pool_info else "linux" 
            self.address = None
            self.max_runs = 1
        elif utils.is_philly_box(box_name):
            self.box_class = "philly"
            self.box_os = "linux" 
            self.address = None
            self.max_runs = 1
        else:
            # must be localhost or a box defined in config file
            if not box_name in self.config.get("boxes"):
                if pc_utils.is_localhost(box_name):
                    box_name = "local"

            box_info = {}
            if box_name in self.config.get("boxes"):
                box_info = self.config.get("boxes", box_name, default_value={})

            if box_name == "local" or box_name == "localhost":
                # the definition of LOCAL box is optional, so provide default properties
                box_info.setdefault("max-runs", 1)
                box_info["address"] = "localhost"
                box_info["box-class"] = "windows" if pc_utils.is_windows() else "linux"

            if not box_info:
                errors.config_error("target/box not defined in config file: " + box_name)

            if not "address" in box_info:
                raise Exception("address property not defined for boxes[{}] in config file".format(box_name))

            # for key, value in defaults_dict.items():
            #     if not key in box_info:
            #         box_info[key] = value

            box_info["name"] = box_name

            info = get_box_addr(self.config, box_name, store)
            box_addr = info["box_addr"]
            
            if pc_utils.is_localhost(box_name, box_addr):
                box_info["os"] = "windows" if pc_utils.is_windows() else "linux"

            #console.print("box_name=", box_name, ", box_info=", box_info)

            self.box_os = box_info["os"]
            self.address = self.config.expand_system_symbols(box_info["address"])
            self.box_class = box_info["box-class"]
            self.max_runs = box_info["max-runs"] if "max-runs" in box_info else 1
            self.actions = box_info["actions"] if "actions" in box_info else []

        self.shell_launch_prefix = self.config.get("script-launch-prefix", self.box_class)

    def get_box_os(self, box_name):
        #console.print("box_name=", box_name)
        if utils.is_azure_batch_box(box_name):
            box_os = "linux"
        elif pc_utils.is_localhost(box_name):
            box_os = "windows" if pc_utils.is_windows() else "linux"
        else:
            box_info = self.config.get("boxes", box_name, default_value={})
            box_os = box_info["os"] if "os" in box_info else "linux"     # default to linux
        return box_os

    def get_serializable_info(self):
        return {"box_name": self.box_name, "os": self.box_os, "address": self.address, "class": self.box_name}

def get_compute_from_job(store, job_id):
    text = store.read_job_info_file(job_id)
    job_info = json.loads(text)
    compute = utils.safe_value(job_info, "compute")
    return compute

def get_box_addr(config, box_name, store):
    #console.print("get_box_addr: box_name=", box_name)
    controller_port = None
    tensorboard_port = None
    azure_batch_state = None

    if utils.is_service_box(box_name):
        job_id, service, node_index = box_name.split("-")
        node_index = int(node_index)
        box_secret = store.get_job_secret(job_id)

        compute = get_compute_from_job(store, job_id)

        # TODO: this should use backend API to get this info
        batch = AzureBatch(compute=compute, compute_def=None, core=None, config=config)
        azure_batch_state, box_addr, controller_port, tensorboard_port = batch.get_azure_box_addr(job_id, node_index)
        #console.print("job_id={}, node_index={}, ip_addr={}, controller_port={}, tensorboard_port={}".format(job_id, node_index, box_addr, controller_port, tensorboard_port))

    elif pc_utils.is_localhost(box_name, None):
        box_addr = "localhost" 
        box_secret = box_secrets.get_secret(box_name)
        #console.print("localhost box_addr=", box_addr)

    else:
        box_addr = config.get("boxes", box_name, dict_key="address", default_value=box_name, 
            prop_error="box not defined in config file: " + box_name)
        #console.print("box_addr=", box_addr)

        if not "." in box_addr and box_addr != "localhost":
            raise Exception("box option must specify a machine by its IP address: " + str(box_addr))

        box_secret = box_secrets.get_secret(box_name)

    info = {"box_addr": box_addr, "controller_port": controller_port, "tensorboard_port": tensorboard_port, 
        "azure_batch_state": azure_batch_state, "box_secret": box_secret}

    return info

def get_box_list(core, job_id=None, explicit_boxes_only=False, box=None, pool=None, args=None):
    boxes = None       
    service_type = None
    pool_info = {}
    config = core.config

    # handle POOL case
    if not pool and args:
        pool = args["pool"]

    if pool:
        pool_info = get_pool_info(core, pool, args)

        # # update the entry in args
        # args["compute_def"] = pool_info
        
        if not "service" in pool_info:
            errors.config_error("compute target '{}' must define a 'service' property".format(pool))

        service = pool_info["service"]
        if service in ["local", "pool"]:
            # POOL of boxes
            if not "boxes" in pool_info:
                errors.config_error("compute-target '{}', with service=pool, must define a 'boxes' property in config file".format(pool))

            boxes = pool_info["boxes"]
        else:
            # BACKEND SERVICE
            service_name = utils.dict_default(pool_info, "service")
            service_type = config.get_service_type(service_name)

            is_batch_pool = (service_type == "batch")
            is_philly_pool = (service_type == "philly")
            is_aml_pool = (service_type == "aml")

            if is_batch_pool:
                num_boxes = pool_info["nodes"] 
                if num_boxes == 0:
                    errors.config_error("no nodes specified for Azure Batch compute")

                boxes = build_service_box_names(job_id, "batch", num_boxes)
            elif is_philly_pool:
                num_boxes = pool_info["nodes"] 
                if num_boxes == 0:
                    errors.config_error("no nodes specified for Philly compute")

                boxes = build_service_box_names(job_id, "philly", num_boxes)
            elif is_aml_pool:
                num_boxes = pool_info["nodes"] 
                if num_boxes == 0:
                    errors.config_error("no nodes specified for Azure ML compute")

                boxes = build_service_box_names(job_id, "aml", num_boxes)
    else:
        #console.print("self.box=", self.box)
        # pool not specified - handle SINGLE BOX case
        if not box and args:
            box = args["box"]
        if box:
            # lowercase all box names so they match the xt_config file
            box = box.lower()

        is_azure_box = utils.is_azure_batch_box(box) if box else False

        if box == "local":
            boxes = [pc_utils.get_hostname()]
        elif box:
            boxes = [box]   

    #console.print("boxes=", boxes)

    if boxes:
        if isinstance(boxes, list):
            pass
        else:
            errors.config_error("a box must be defined as a single box entry or a pool (list of box names): {}".format(pool))

    return boxes, pool_info, service_type

def get_pool_info(core, pool_name, args):

    # get a COPY of the target dict
    pool_info = dict(core.config.get_compute_def(pool_name))
    config = core.config

    if isinstance(pool_info, list):
        pool_info = {"boxes": pool_info, "service": "__pool__"}
    elif "service" in pool_info and args:

        # allow explicit option overriding of properties
        explict = qfe.get_explicit_options()
        opts = ["vm-size", "azure-image", "nodes", "low-pri", "cluster", "vc", "queue", "sku"]

        for opt in opts:
            if opt in explict:
                #opt_under = opt.replace("-", "_")
                value = explict[opt]
                if opt in ["nodes"]:
                    value = 0 if value is None else int(value) 
                pool_info[opt] = value

    pool_info["name"] = pool_name
    return pool_info

def build_service_box_names(job_id, service, num_boxes):
    boxes = []

    # allow for early calls (before job has been created)
    if not job_id:
        job_id = ""

    for i in range(num_boxes):
        box_name = utils.make_box_name(job_id, service, i)
        boxes.append(box_name)

    return boxes

