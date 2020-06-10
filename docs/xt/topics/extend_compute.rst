.. _extend_compute:

=====================================================
Adding compute providers
=====================================================

.. only:: not internal 

    XT's supported backend compute providers (such as Azure ML) can be extended by the user.

.. only:: internal 

    XT's supported backend compute providers (such as Philly and Azure ML) can be extended by the user.

The general idea is to write a python class that implements the **BackendInterface** interface.

The  **BackendInterface** interface is defined as follows::

    # backend_interface.py: specifies the interface for backend compute services
    from interface import Interface

    class BackendInterface(Interface):

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

        def submit_job(self, job_id, job_runs, workspace, compute_def, resume_name, 
                repeat_count, using_hp, runs_by_box, experiment, snapshot_dir, args):
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
                args: a dictionary of key/value pairs corresponding to the the run commmand options for this job
            Returns:
                (service_job_id, monitor_url)

            Description:
                This method is submits a job to run on the backend service.  It returns a tuple of a service id for 
                the newly submitted job, and a URL where the job can be monitored using the backend website.
            '''
            pass

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

        def provides_container_support(self):
            '''
            Returns:
                returns True if docker run command is handled by the backend.
            '''
            pass

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

The steps for adding a new computer provider to XT are:
    - create a python class with that implements each method of the **BackendInterface** interface
    - add a provider name and its **code path**  as a key/value pair to the **compute** provider dictionary in your local XT config file
    - add a compute service under **external-services** that uses the compute provider (in your local XT config file)
    - add 1 or more targets (under **compute-targets** in your local XT file) that use your new compute service
    - ensure your provider package is available to XT (in the Python path, or a direct subdirectory of your app's working directory), so that 
      XT can load it when needed (which could be on the XT client machine and/or the compute node)

For example, to add our new compute provider to XT, we can include the following YAML section to our local XT config file::

    external-services:
        cloudcomputeservice: {type: "myCloudCompute", account: "https://johnsmith@mycoudcompute.com/myservice"}

    compute-targets:
        cloud4x: {service: "cloudcomputeservice", sku: "G4", nodes: 1}
        cloud16x: {service: "cloudcomputeservice", sku: "G16", nodes: 1}

    providers:
        comopute: {
            "myCloudCompute": "extensions.my_cloud_compute.MyCloudCompute" 
        }

Where **extensions** is the parent directory of the **my_cloud_compute.py** file)

.. seealso:: 

    - :ref:`XT Config file <xt_config_file>`
    - :ref:`Extensibility in XT <extensibility>`
