#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# backend_interface.py: specifies the interface for backend compute services
from interface import Interface

class BackendInterface(Interface):

    def __init__(self, compute, compute_def, core, config, username=None, arg_dict=None):
        '''
        arg_dict are backend-specific properties
        '''
        pass

    # API call
    def get_name(self):
        '''
        Returns:
            name of the service (e.g., batch or aml)

        Description:
            This method is called to get the name of the backend service.
        '''
        pass
    
    # API call
    def adjust_run_commands(self, job_id, job_runs, using_hp, experiment, service_type, snapshot_dir, args):
        '''
        Args:
            job_id: the name of job that is being prepared to be submitted
            job_runs: a list of run description records for the job's runs
            using_hp: True if this job is a hyperparameter search
            experiment: the name of experiment associated with the job
            service_type: the type of compute backend associated with the job
            snapshot_dir: the directory that holds the code files for the job (which will soon be uploaded)
            args: a dictionary of key/value pairs corresponding to the the run commmand options for the job
        Returns:
            None

        Description:
            This method is called to allow the backend to inject needed shell commands before the user cmd.  At the
            time this is called, files can still be added to snapshot_dir.
        '''
        pass

    # API call
    def submit_job(self, job_id, job_runs, workspace, compute_def, resume_name, 
            repeat_count, using_hp, runs_by_box, experiment, snapshot_dir, controller_scripts, args):
        '''
        Args:
            job_id: the name of job that is being prepared to be submitted
            job_runs: a list of run description records for the job's runs
            workspace: the name of the workspace associated with the job
            compute_def: the target dictionary from the XT config file (matched from the --target option)
            resume_name: the name of the run being resumed (depreciated)
            repeat_count: the repeat count for the runs in this job (from the --repeat option)
            using_hp: True if this job is a hyperparameter search
            runs_by_box: for each node that the job will run on, a list of run records for that node
            experiment: the name of experiment associated with this job
            snapshot_dir: the directory that holds the code files for this job (which will soon be uploaded)
            controller_scripts: list of files needed to start running the controller
            args: a dictionary of key/value pairs corresponding to the the run commmand options for this job
        Returns:
            service_job_info: a dictionary of service-specific info about the job
            service_info_by_node: a dictionary with service-specific info about each node of the job

        Description:
            This method is submits a job to run on the backend service.  It returns a tuple of a service id for 
            the newly submitted job, and a URL where the job can be monitored using the backend website.
        '''
        pass

    # API call
    def get_client_cs(self, service_node_info):
        '''
        Args:
            service_node_info: info that service maps to a compute node for a job
        Returns:
            {"ip": value, "port": value, "box_name": value}

        Description:
            This method is used to get IP address and PORT information needed to connect to 
            the XT controller on the specified node.
        '''
        pass

    # API call
    def view_status(self, run_name, workspace, job, monitor, escape_secs, auto_start, 
            stage_flags, status, max_finished):
        '''
        Args:
            run_name: if specified, the name of the run whose status is requested 
            workspace: the name of the workspace associated with the run
            job: if specified, the id of the job whose status is being requested
            monitor: True if status should be continually monitored
            escape_secs: if monitor is True, how long the montoring should continue
            auto_start: if True, the XT controller should be started if needed (pool service only)
            status: if specified, the status value to filter the runs
            max_finished: if specificed, the maximum number of finished runs to return 
        Returns:
            None

        Description: 
            queries the backend compute service for the status of the specified run or job.  The status
            should be formatted into a table and output to the console (using **console.print()**).
        '''
        pass

    # API call
    def provides_container_support(self):
        '''
        Returns:
            returns True if docker run command is handled by the backend.
        '''
        pass

    # API call
    def cancel_runs_by_names(self, workspace, run_names, box_name):
        '''
        Args:
            workspace: the name of the workspace containing the run_names
            run_names: a list of run names
            box_name: the name of the box the runs ran on (pool service)
        Returns:
            cancel_results: a list of cancel_result records 
                (keys: workspace, run_name, exper_name, killed, status, before_status)

        Description:
            kills the specified runs and returns information about which runs were affected.
        '''
        pass

    # API call
    def cancel_runs_by_job(self, job_id, runs_by_box):
        '''
        Args:
            job_id: the name of the job containing the run_names
            runs_by_box: a dict of box_name/run lists
        Returns:
            cancel_results_by box: a dict of box_name, cancel_result records
                (keys: workspace, run_name, exper_name, killed, status, before_status)

        Description:
            kills the specified job and returns information about which runs were affected.
        '''
        pass

    # API call
    def cancel_runs_by_user(self, box_name):
        '''
        Args:
            box_name: the name of the box the runs ran on (pool service)
        Returns:
            cancel_results: a list of kill results records 
                (keys: workspace, run_name, exper_name, killed, status, before_status)

        Description:
            kills the runs associated with the XT user and returns information about which runs were affected.
        '''
        pass

    # API call
    def read_log_file(self, service_node_info, log_name, start_offset=0, end_offset=None, 
        encoding='utf-8', use_best_log=True):
        '''
        Args:
            service_node_info: a service-defined dictionary that identifies a node assoicated with a job
            log_name: the name of a specific log file to read (stdout, stderr, log70, etc.)
            start_offset: starting offset to read from in log file
            end_offset: last offset of log file to read (if None, rest of file is read)
            encoding: how to encode bytes to text for log content
            use_best_log: when True, backend will continually choose the best log to be return
        Returns a dictionary with following keys:
            new_text  (the specified subset of the file)
            simple_status (a string, one of: queued, running, completed) 
            service_status (the service specific status value)
            log_name (the name of the returned log file)
            next_offset (the next streaming offset to be used for the returned log file)

        Description:
            reads the specified subset of the specified log file, for the node identified by
            service_node_info.
       '''
        pass

    # API call
    def get_simple_status(self, status):
        '''
        Args:
            status: the backend-specific status value
        Returns:
            returns a simple status from one of these values: queued, running, completed

        Description:
            translated the service status to a simple status.
        '''
        pass

    # API call
    def cancel_job(self, service_job_info, service_info_by_node):
        '''
        Args:
            service_job_info: backend-specific dict to identify the job
            service_info_by_node: dict of backend-specific dict to identify each node

        Returns:
            result_by_node: a dict of cancel result records: {cancelled: bool, server_status, simple_status}
            
        Description:
            cancels each node of the specified job, and if appropriate for the service, cancels the job itself
        '''
        pass

    # API call
    def cancel_node(self, service_node_info):            
        '''
        Args:
            service_node_info: backend-specific dict to identify the node

        Returns:
            result_record: {cancelled: bool, server_status, simple_status}
            
        Description:
            cancels the run/task running on the specified node.
        '''
        pass

    # API call
    def get_node_status(self, service_node_info):
        '''
        Args:
            service_node_info: backend-specific dict to identify the node

        Returns:
            service-specific status (string)
            
        Description:
            returns the status of the specified node.
        '''
        pass

    # API call
    def get_service_queue_entries(self, service_node_info):
        '''
        Args:
            service_node_info: backend-specific dict to identify the node

        Returns:
            a list of records: first is the currently executing job and 
            the others are the jobs in the queue, waiting to run.
            record keys: current (bool), name (name job entry)
            
        Description:
            gathers and returns the list of current + queue entries.
        '''
        pass
