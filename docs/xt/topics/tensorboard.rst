.. _tensorboard:

========================================
Using Tensorboard with XT
========================================

When your script is running under XT, you can continue to log to Tensorboard files
as you normally do, but there are a few Tensorboard-related logging and viewing features in XT
that you might want to take advantage of.

-----------------------------------
Automatic Logging to Tensorboard
-----------------------------------

XT's automatic logging to Tensorboard provides the following benefits:
    - creates a Tensorboard Summary writers for train/test stages of your logged metrics 
    - calls to run.log_metrics() log your metrics to both XT and Tensorboard
    - Tensorboard logs are written to your run's cloud storage (for dynamic Tensorboard viewing) 

.. only:: internal 

    - When running on Philly, XT writes a 2nd copy of Tensorboard logs to Philly's Tensorboard path 

To use XT's automatic logging:
    - create a path for where the tensorboard logs will be written, using the **XT_OUTPUT_MNT** environment variable (which is mapped to the run's cloud storage)::

        tb_path = os.getenv("XT_OUTPUT_MNT", "output")
        if not os.path.exists(tb_path):
            os.makedirs(tb_path)

    - create an instance of the xtlib.run.Run class at the beginning of your ML script, passing in 
      path you just created::

        run = xtlib.run.Run(tensorboard_path=tb_path)

    - use run.log_metrics() to log your train and test metrics (this will log them to XT as well as Tensorboard)

      Here is an example of logging 2 training metrics::

            run.log_metrics({"epoch": epoch, "loss": train_loss, "acc": train_acc}, step_name="epoch", stage="train")

      Here is an example of logging 2 test metrics::

            run.log_metrics({"epoch": epoch, "loss": train_loss, "acc": train_acc}, step_name="epoch", stage="test")

NOTE: XT currently only logs scalar values, so if you need to log other value types to Tensorboard, it is simplest to 
do your Tensorboard logging and not use the automatic logging feature.

-----------------------------------
Logging to **XT_OUTPUT_MNT**
-----------------------------------

If you are doing your own Tensorboard logging, we recommend that you write your Tensorboard 
files to the path specified by the XT supplied environment variable **XT_OUTPUT_MNT**.

This path is mapped to the cloud storage associated with your current run.  This means that if
your job is interruped (preempted), you logging history is not lost.  It is also recommended 
that you write your checkpoint files to this directory.

One additional change is needed to make this work for Tensorboard logs.  Tensorboard doesn't close the files each time you log 
values; as a consequence, the underlying blob-fuse technology used to map to the cloud storage doesn't push the file changes.  To 
force this to happen, you should include the following code in your ML script **before** creating your Tensorboard logging instance::

            # TENSORBOARD WORKAROUND: this code causes tensorboard files to be closed when they are appended to
            # this allow us to just write the files to MOUNTED output dir (and not have to mirror them)
            try:
                from tensorboard.compat import tf
                delattr(tf.io.gfile.LocalFileSystem, 'append')
            except:
                import tensorflow as tf
                import tensorboard as tb
                tf.io.gfile = tb.compat.tensorflow_stub.io.gfile
                delattr(tf.io.gfile.LocalFileSystem, 'append')

.. only:: internal 

  -----------------------------------
  Logging to Philly's Tensorboard
  -----------------------------------

  If you are doing your own Tensorboard logging and your script runs on the Philly backend, you may want to write a copy of your 
  Tensorboard logs to the Philly Tensorboard path defined by the environment variable **"PHILLY_JOB_DIRECTORY**.  Doing so will
  let you create a Tensorboard view from the Philly portal (using the **Tensorboard** link shown with your run).

-----------------------------------
Dynamic Tensorboard Viewing
-----------------------------------

Once your job has started running, you can create a Tensorboard for selected runs that will dynamically combine them together
in a single Tensorboard view. Typically, you specify a single run or the runs within a job.  

As an extreme example, you could specify a run that was completed last week on Azure Batch, together with a live run on a VM, 
together with a run on Azure ML the just completed, and view them in a single Tensorboard view. 

Examples::

    xt view tensorboard run343   (creates a tensorboard for the single run run343)

    xt view tensorboard job2300  (creates a tensorboard for all runs within job2300)

    xt view tensorboard run310, run341, run400  (creates a tensorboard combining the specified runs)

-----------------------------------
Tensorboard path templates
-----------------------------------

The parent directory of Tensorboard logs have a special use in the Tensorboard web page.  It is typically named by ML script authors
to reflect some of the hyperparameter values used for the run being logged and Tensorboard provides the ability to filter runs, 
based on regular expression searches on the hyperparameter values (directory names).

To help create this style of Tensorboard parent directory names, XT provides a tensorboard.template property in the XT config file 
that specifies how the directory name should be built.  The default value for the template is::

    template: "{workspace}_{run}_{logdir}"

If you run is called "run23" and is under workspace "ws1", and this was a Tensorboard log associated with training (vs. test), your
Tensorboard directory name would be created as:

    ws1_run23_train

You can include other names in {} in the template, include XT standard column names for runs and logged hyperparameter values.  For example, 
the template::

    {workspace}_{run}_{logdir}_lr={hparams.lr}_epochs={hparams.epochs}

Might result in a directory named:

    ws1_run23_train_lr=.01__epochs=2500

.. seealso:: 

    - :ref:`view tensorboard cmd <view_tensorboard>`
