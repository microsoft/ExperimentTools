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
