.. _micro_mnist:

======================================
Micro Mnist Tutorial Sample
======================================

The Micro Mnist sample is a small python program to demonstrate how a program running under XT can write log and checkpoint information to the cloud, and use that information to detect and process run restarts on low-priority compute services.

The sample consists of::

    - microMnist.py    
    - xt_config.yaml   

------------------------------
The program
------------------------------

The MicroMnist Python script is as follows:

.. code-block::

    # microMnist.py: a tiny program to show how ML apps can write to mounted cloud storage in XT
    import os
    import json
    import time

    # point to run's output dir (on cloud if under XT, else local dir)
    output_dir = os.getenv("XT_OUTPUT_MNT", "output")

    fn_log = os.path.join(output_dir, "log.txt")
    fn_checkpoint = os.path.join(output_dir, "checkpoint.json")
    first_step = 1

    def log(msg):
        print(msg)

        with open(fn_log, "a") as outfile:
            outfile.write(msg + "\n")

    # ensure output directory exists (for local dir case)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # read checkpoint info for restart
    if os.path.exists(fn_checkpoint):
        with open(fn_checkpoint, "r") as outfile:
            text = outfile.read()
            cp = json.loads(text)
            first_step = 1 + cp["step"] 
            log("---- restarted ----")

    for step in range(first_step, 10+1):
        # log progress
        log("processing step: {}".format(step))

        # simulate step processing
        time.sleep(60)   # wait for 1 min

        # step processing complete; write checkpoint info
        cp = {"step": step}
        cp_text = json.dumps(cp)
        with open(fn_checkpoint, "w") as outfile:
            outfile.write(cp_text)

    log("all steps processed")

The key line of code in the above program is the line::

    output_dir = os.getenv("XT_OUTPUT_MNT", "output")

When XT runs the microMnist program, it uses Azure BlobFuse to mount the (cloud) storage container associated with the run, and maps it to a local path. It then sets the value of the environment variable **XT_OUTPUT_MNT** to the same local path.

If you run the program under XT, the above line of code sets **output_dir** to the path for the mounted run storage (). If you don't run the program under XT, it sets **output_dir** to a local **output** directory.

To run microMnist, copy the following xt_config text into a separate file in the /tutorials directory:

.. only:: internal

  .. code-block:: none

    # local xt_config.yaml file for microMnist directory
    compute-targets:
        philly-rr2: {service: "philly", cluster: "rr2", vc: "resrchvc", sku: "G1", nodes: 1, low-pri: true, docker: "philly-pytorch", setup: "philly"}

    xt-services:
        target: philly-rr2        # default target for XT run command

    general:
        workspace: "ws1"          # name of current workspace 
        experiment: "exper5"      # default name of experiment associated with each run

    code:
        code-omit: ["output"]     # directories and files to omit when capturing code files

.. only:: not internal

  .. code-block:: none

    # local xt_config.yaml file for microMnist directory
    compute-targets:
        xtbatch: {type: "batch", key: "$vault", url: "https://xtbatch.eastus.batch.azure.com"}

    xt-services:
        target: batch-rr2        # default target for XT run command

    general:
        workspace: "ws1"          # name of current workspace 
        experiment: "exper5"      # default name of experiment associated with each run

    code:
        code-omit: ["output"]     # directories and files to omit when capturing code files    

--------------------------
Running MicroMnist
--------------------------

To run microMnist, you can use:

.. code-block:: none

    > xt run microMnist.py

.. note::

    You can find the microMnist.py file in the /tutorials directory of your top-level XT folder.

The above command runs the program under the control of the XT controller. To run it without the controller, in "direct mode", use the command:

.. code-block:: none

    > xt run --direct-mode microMnist.py

.. seealso:: 

    - :ref:`Understanding the XT Config file <xt_config_file>`
