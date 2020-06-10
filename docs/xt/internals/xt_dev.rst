.. _xt_dev:

==========================
XT Internal Development
==========================


-------------------------------------
Initial environment setup
-------------------------------------

To setup your environment for XT internal development:
  - install Anaconda if you don't already have it  (https://docs.anaconda.com/anaconda/install/)
  - create a conda virtual envrionment for XT development.  Suggested::

      > conda create -n exper python=3.6

  - activate the new environment::

      > conda activate exper

  - install latest pytorch from conda (see conda command at pytorch.org)
  
-------------------------------------
Initial XT source code setup
-------------------------------------

  To install the ExperimentTools (aka XTLib) source code:
   - change to your base github directory (the directory that you want ExperimentTools to live under)
   - clone ExperimentTools::

       > git clone https://github.com/MSRDL/ExperimentTools

   - install as an XT developer::

       > cd ExperimentTools
       > pip install -e .[dev]

-------------------------------------
New development session setup:
-------------------------------------

To start a new XT development session (for example, after a reboot):
   - activate your xt conda environment::

      > conda activate exper

You are now ready to develop XT:
    - change code in your editor
    - save results
    - run "xt" at the command line (or in your debugger) against latest changes.  



-------------------------------------
Test/Debug Notes:
-------------------------------------

Notes on testing and debugging:
  - you can use **$lastrun** and **$lastjob** in your command lines to reference last run/job names
  - you can change the uncommented command to be debugged in cmdlineTest/debug_cmd.py 
  - select **CmdLine DEBUG** as your debug configuration in VS CODE

-------------------------------------
Running the XT QuickTest
-------------------------------------

To validate that you changes have not broken any of the core XT commands and features, you can run the **XT quicktest**.  

Here are the details you need to know:
    - to run the XT QuickTest::

        > cd quick-test
        > python quick-test.py

    - note, the quick-test first deletes the quick-test workspace and then re-creates it.  this results in about 1 minute of Azure error/retries displayed.  this is normal for this step.
    - the test will run for about 20 minutes.  if it is successful, the last message it displays will look like this::

        *** quickTest PASSED *** (elapsed: 17.62 mins)

    - WAIT, you are not done.  also check the following::

        - ensure command window has no obvious errors (stack traces)
        - ensure XT controller windows shows no obvious errors (stack traces)

.. seealso:: 

    - :ref:`XT Build Process <xt_build>`   
    - :ref:`XT Release Process <xt_release>`
