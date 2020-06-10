.. _xt_release:

==========================
XT Release Process
==========================

---------------------------------
Release the Documentation
---------------------------------

To release the documentation to XT docs website:
    - use the same machine that you used to build the documentation
    - open the ExperimentTools directory in Visual Studio Code IDE
    - ensure you have installed the Azure Storage add-in for VS Code
    - right click on the **ExperimentTools\\docs\xt\\_build\\html** folder and choose **Deploy to Static Website...**
    - from the next popup, choose **rfernand2-ML_research_and_tools**
    - from the next popup, choose **xtdocs**
    - in the confirmation dialog, click on **Delete and Deploy**
    - once the status box in the lower right shows the deployment has completed, click on **Browse to website**
    - sample a few pages and ensure they look correct
    - look at recently changed pages and verify the changes are present


-----------------------------------------
Release a new version of XTLIB to pypi
-----------------------------------------

Follow these steps to release a new version of XT / XTLib:
    - ensure you have run and passed the XT quick-test (on Windows or Linux)
    - bump the version and release date::

        - constants.py      (top of file)
        - CHANGELOG.md      (top of file)
        - setup.py          (near top of file)
        - conf.py           (two files in docs folder, near top of file)

    - check-in your changes (github)
    - open an SSH session to a clean LINUX box (where you have not been developing XT)
    - copy tools\exper.sh to your linux box and modify it for your username (change "rfernand2" to your github account name)
    - on your linux box::

        $ sh exper.sh    (will clone ExperimentTools)
        $ cd ExperimentTools/pypi
        $ sh release.sh
            - this will prompt you for username and password for pypi  (contact rfernand2 to be added to the XTLIB pypi project)
            - this will release the version to pypi; once complete, everyone can 'pip install -U xtlib" 

    - before announcing the new release, ensure you test it (see next step)

-----------------------------------------
Test newly released version
-----------------------------------------

To test the new **xtlib** in pypi:
    - SSH into a 2nd clean LINUX box and run::

        $ conda activate py36      (assuming it is a DSVM box; if not, substitute an appropriate conda virtual environment)
        $ pip install --U xtlib    (ensure latest version is shown at end; if not, REPEAT THIS CMD a 2nd time)

    - switch to your XT client machine and run::

        >  xt --box=xxxx restart controller  (replace "xxxx" with the box name for your 2nd LINUX box declared in your XT config file)

    - ensure controller message shows it is using the NEW XT version::

        > cd "ExperimentTools\cmdlineTest"
        > xt run --target=xxxx miniMnist.py --epochs=10
        > xt list runs --last=5  

    - ensure 'list runs' shows the miniMnist run active or completed on box xxxx

OK, your XT changes and now been quicktest-ed, released, and you have done a sanity check on the new release.  Now
you are ready to announce the new release to XT users.

.. seealso:: 

    - :ref:`XT Internal Development <xt_dev>`
    - :ref:`XT Build Process <xt_build>`   
    