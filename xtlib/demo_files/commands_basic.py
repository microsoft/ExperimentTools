#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# commands_basic.py: commands used in the basic mode xt_demo

def get_command_dicts(prev_exper, curr_exper, browse_flag, browse_opt, timeout_opt, templ, archives_dir, monitor_opt):
	return [
      # PREREQS
      {"title": "XT's basic demo requires Azure Batch to be setup and added to xt_config.yaml "
      + " to get a base template that you can use please run xt config --create batch "
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

	    # INITIAL SYNC LOCAL RUN (this will create MNIST data and model)
	    {"title": "run script without XT and generate data/model", "xt_cmd": "!python code/miniMnist.py --data=data --save-model"},

	    # upload DATA/MODELS (depends on miniMnist generated data and model)
	    # {"title": "upload MNIST dataset", "xt_cmd": "xt upload ./data/MNIST/processed/**MNIST/processed --share=data"},
	    # {"title": "upload previously trained MNIST model", "xt_cmd": "xt upload .\models\miniMnist\** miniMnist --share=models"},
	    {"title": "upload MNIST dataset", "xt_cmd": "xt upload ./data/MNIST/processed/** MNIST/processed --share=data"},
	    {"title": "upload MNIST models", "xt_cmd": "xt upload ./models/miniMnist/** miniMnist --share=models"},

	    # RUNS
	    # {"title": "run script on LOCAL MACHINE", "xt_cmd": "xt run --target=local --exper={} code\miniMnist.py".format(curr_exper)},
	    # {"title": "run script on PHILLY", "xt_cmd": "xt run --target=philly --exper={} code\miniMnist.py".format(curr_exper)},
	    # {"title": "run script on AZURE BATCH", "xt_cmd": "xt run --target=batch --exper={} code\miniMnist.py".format(curr_exper)},
	    # {"title": "run script on AZURE ML", "xt_cmd": "xt run --target=aml --exper={} code\miniMnist.py".format(curr_exper)},
	    {"title": "run script on LOCAL_MACHINE", "xt_cmd": "xt run {}--target=local code/miniMnist.py".format(monitor_opt)},
	    {"title": "run script on AZURE BAtCH", "xt_cmd": "xt run {}--target=batch code/miniMnist.py".format(monitor_opt)},

	    # REPORTS
	    {"title": "OVERVIEW: status of jobs", "xt_cmd": "xt list jobs --last=4"},
	    # {"title": "ZOOM in on CURRENT experiment", "xt_cmd": "xt list runs --exper={}".format(curr_exper)},
	    {"title": "List runs", "xt_cmd": "xt list runs"},
	    {"title": "List runs and sort by metrics", "xt_cmd": "xt list runs --sort=metrics.test-acc --last=5"},
	    {"title": "run script on Philly", "xt_cmd": "xt run --target=philly --data-action=mount --model-action=download code/miniMnist.py --auto-download=0 --eval-model=1", "needs_philly": True},

	    {"title": "run script on Batch", "xt_cmd": 
            "xt run {}--runs=50 --nodes=5 --search-type=dgd --hp-config=code/miniSweeps.yaml --target=batch --data-action=mount " \
                "--model-action=download code/miniMnist.py --auto-download=0 --eval-model=1".format(monitor_opt)
        }
	]