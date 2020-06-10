.. _xt_build:

=======================
XT Build Process
=======================

This page describes steps needed to build a releasable version of XT.

---------------------------------
Build the Documentation
---------------------------------

To build the XT documentation, download the latest ExperimentTools source code to a Windows machine.

Open a command line window follow these steps:
        - **cd** to the folder **ExperimentTools\docs**
        - run the file **build.bat** 

The **build.bat** file will:
    - call XT to generate the command help pages (cmds\\\*.rst files)
    - copy all help pages to xtlib\\htlp_topics 
    - call sphinx to generate HTML pages from the RST files
    - copy all generated HTML files to local IIS folder (for local testing)
    - open a browser to the root HTML file 

Warnings from the sphinx processor appear in red.  About 20 warnings are currently generated for the **xt_config_file.rst** file; these
can be safely ignored, but you should resolve warnings on any other files.

In the browser, sample some pages and ensure everything looks right.  If you know of recent page changes, inspect those closely.  When everything
looks good, proceed to the next step, releasing the documentation.


.. seealso:: 

    - :ref:`XT Internal Development <xt_dev>`
    - :ref:`XT Release Process <xt_release>`
    