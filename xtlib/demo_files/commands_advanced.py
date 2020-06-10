#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# commands_advanced.py: commands used in the advanced mode xt_demo

def get_command_dicts(prev_exper, curr_exper, browse_flag, browse_opt, timeout_opt, templ, archives_dir, 
    monitor_opt):
	return [
      # PREREQS
      {"title": "XT's advanced demo requires Azure Batch and Azure Machine Learning (AML) to be setup and added to xt_config.yaml "
      + " to get a base template that you can use please run xt config --create batch and xt config --create aml "
      + " or review the Creating Azure Cloud Services for XT topic on the documentation.", "xt_cmd" : "xt --version"},

	    # OVERVIEW
	    {"title": "show the XT about page", "xt_cmd": "xt help --about"},
	    {"title": "show the help topic on Getting Started with XT", "xt_cmd": "xt help topic getting_started"},

	    # CONFIG FILES
	    {"title": "view the XT default config file", "xt_cmd": "xt config --default"},
	    {"title": "view the local XT config file", "xt_cmd": "xt config"},

	    # HELP
	    {"title": "display XT commands", "xt_cmd": "xt help"},
	    {"title": "display help for LIST JOBS command", "xt_cmd": "xt help list jobs"},

	    {"title": "browse the XT HTML docs", "xt_cmd": "xt help --browse", "needs_gui": True},

	    # VERSION / RESTART
	    {"title": "display XT version", "xt_cmd": "xt help --version"},

	    # STATUS    
	    {"title": "display STATUS of jobs on AZURE BATCH", "xt_cmd": "xt view status --target=batch"}, 

        # turn this off until "view status" for local/pool has been updated for pool service manager API (psm client)
        #{"title": "display all active jobs on any of my compute targets", "xt_cmd": "xt view status --target=all --active"},

	    # INITIAL SYNC LOCAL RUN (this will create MNIST data and model)
	    {"title": "run script without XT and generate data/model", "xt_cmd": "!python code\\miniMnist.py --data=data --save-model"},

	    # upload DATA/MODELS (depends on miniMnist generated data and model)
	    {"title": "upload MNIST dataset", "xt_cmd": "xt upload ./data/MNIST/processed/** MNIST/processed --share=data"},
	    {"title": "upload previously trained MNIST model", "xt_cmd": "xt upload .\models\miniMnist\** miniMnist --share=models"},

	    # RUNS
	    {"title": "run script on LOCAL MACHINE", "xt_cmd": "xt run {}--target=local --exper={} code\miniMnist.py".format(monitor_opt, curr_exper)},
	    {"title": "run script on PHILLY", "xt_cmd": "xt run {}--target=philly --exper={} code\miniMnist.py".format(monitor_opt, curr_exper), "needs_philly": True},
	    {"title": "run script on AZURE BATCH", "xt_cmd": "xt run {}--target=batch --exper={} code\miniMnist.py".format(monitor_opt, curr_exper)},
	    {"title": "run script on AZURE ML", "xt_cmd": "xt run {}--target=aml --exper={} code\miniMnist.py".format(monitor_opt, curr_exper)},

	    # REPORTS
	    {"title": "OVERVIEW: status of jobs", "xt_cmd": "xt list jobs --last=4"},
	    {"title": "ZOOM in on CURRENT experiment", "xt_cmd": "xt list runs --exper={}".format(curr_exper)},

	    # TAGGING
	    {"title": "add tag 'good_run' to run1, run2", "xt_cmd": "xt set tags run1, run2 good_run"},
	    {"title": "list runs with the 'good_run' tag", "xt_cmd": "xt list runs --tags=good_run"},

	    # CMD LINE PIPING
	    {"title": "the 'list runs' and 'list jobs' have powerful filtering and sorting options", "xt_cmd": "xt list runs --exper=search10 --sort=metrics.test-acc --last=5"},
	    {
		    "title": "you can leverage the 'list runs' cmd to feed runs into another cmd, using XT command piping", \
		    "xt_cmd": "!xt list runs --exper=search10 --sort=metrics.test-acc --last=5 | xt set tags $ top5"
		},
	    # {"title": "let's see which runs are now tagged with 'top5", "xt_cmd": "xt list runs --tags=top5"},

	    # VIEW PORTAL
	    {"title": "Browse the portal for the 'philly' target", "xt_cmd": "xt view portal philly {}".format(browse_flag), "needs_philly": True},
	    {"title": "Browse the portal for the 'aml' target", "xt_cmd": "xt view portal aml {}".format(browse_flag)},

	    # TENSORBOARD
        {
	        "title": "view LIVE tensorboard of cross-service experiments with custom path template",
	        "xt_cmd": 'xt view tensorboard --exper=search10 {} --template="{}"'.format(browse_flag, templ),
	        "needs_gui": True
	    },

	    # LOG, CONSOLE, ARTIFACTS
	    #{"title": "view log for run5751", "xt_cmd": "xt view log run5751"}
	    {"title": "view console output of run2", "xt_cmd": "xt view console run2"},

	    {"title": "download all source code, output, and logs for run2", "xt_cmd": "xt extract run2 {} {}".format(archives_dir, browse_opt)},

	    # RERUN (monitor_opt is harder to apply here)
	    {"title": "rerun run2, with original source code and hyperparameter settings", "xt_cmd": "xt rerun run2"},

	    # MOUNT data and DOWNLOAD model
	    {"title": "run script, mounting data and downloading model for eval", 
            "xt_cmd": "xt run {}--target=philly --data-action=mount --model-action=download code\miniMnist.py --auto-download=0 --eval-model=1". \
                format(monitor_opt), "needs_philly": True},

	    # DOCKER RUNS
	    # {"title": "log in to azure docker registry", "xt_cmd": "xt docker login  --environment=pytorch-xtlib "}
	    # {"title": "log out from docker registry", "xt_cmd": "xt docker logout  --environment=pytorch-xtlib "}
	    # {"title": "run script in DOCKER container on LOCAL MACHINE", "xt_cmd": "xt --target=local --environment=pytorch-xtlib-local run code\miniMnist.py --no-cuda"}
	    # {"title": "run script in DOCKER container on BATCH", "xt_cmd": "xt --target=batch --environment=pytorch-xtlib run code\miniMnist.py"}

	    # PARALLEL TRAINING
	    # {
		  #   "title": "run parallel training on Azure ML using 4 GPUs", 
	    #     "xt_cmd": "xt run {}--target=aml4x code\miniMnist.py --train-percent=1 --test-percent=1 --epochs=100 --parallel=1".format(monitor_opt)
	    # },

	    # DISTRIBUTED TRAINING
	    {
		    "title": "run distributed training on Azure ML using 8 boxes", 
	        "xt_cmd": "xt run {}--target=aml --direct-run=true --nodes=8 --distributed code\miniMnist.py --train-percent=1 --test-percent=1  " \
                "--epochs=100  --distributed=1".format(monitor_opt)
	    },

	    # HPARAM SEARCH
	    {
		    "title": "start a hyperparmeter search of 50 runs (5 boxes, 10 runs each) using Azure Batch", 
	        "xt_cmd": "xt run {}--target=batch --runs=50 --nodes=5 --search-type=dgd --hp-config=code\miniSweeps.yaml code\miniMnist.py".format(monitor_opt)
	    },

	    {
            "title": "view a report of previously completed HP search, ordered by test accuracy", 
            "xt_cmd": "xt list runs --job=xtd_job10608 --sort=metrics.test-acc"
        },

        # HPARAM EXPLORER
        # NOTE: turn back ON as soon as we merge in PR's #139, #143 
	    # {
		#     "title": "open Hyperparameter Explorer to compare the effect of hyperparameter settings on test accuracy, using a previously completed HP search", 
	    #     "xt_cmd": "xt explore xtd_job10608 {}".format(timeout_opt),
        #     "needs_gui": True
	    # },

	    # AD-HOC PLOTTING (run as external cmd due to problem closing 2nd matplotlib window)
        # SINGLE PLOT of 10 RUNS
        {
	        "title": "display a plot of 10 runs",
	        "xt_cmd": '!xt plot xtd_job10608 ' + "test-acc {}".format(timeout_opt),
			"needs_gui": True
	    },

        # # APPLY SMOOTHING FACTOR
        # cmd = '!xt plot job9554 ' + \
        #     "test-acc --smooth=.85  {}".format(timeout_opt)
        # {"title": "apply a smoothing factor", cmd)

        # # AGGREGATE over runs
        # cmd = '!xt plot job9554 ' + \
        #     "test-acc --smooth=.85 --aggregate=mean --range-type=std {}".format(timeout_opt)
        # {"title": "plot the average the runs, using std as the range area", cmd)

        # 2 METRICS, 2x5 MATRIX (break on run)
        {
	        "title": "alternatively, let's add a 2nd metric, train-acc, and show each run in its own plot",
	        "xt_cmd": '!xt plot xtd_job10608 ' + \
	            "train-acc, test-acc --break=run --layout=2x5 {}".format(timeout_opt),
	        "needs_gui": True
	    },

        # 2 METRICS, 2x1 MATRIX (break on col)
        {
	        "title": "finally, we can easily break on the col, instead of the run",
	        "xt_cmd": '!xt plot xtd_job10608 ' + \
	            "train-acc, test-acc --break=col --layout=2x1 {}".format(timeout_opt),
	        "needs_gui": True
	    }
	]