.. _scp:  

========================================
scp command
========================================

Usage::

    xt scp <cmd>

Description::

        copy file(s) between the local machine and a remote box

Arguments::

  cmd    the scp command to execute

Examples:

  copy the local file 'miniMnist.py' to the outer directory of box 'vm10'::

  > xt scp miniMnist.py vm10:~/

  copy the all \*.py files from the outer directory of box 'vm10' to the local directory /zip::

  > xt scp vm10:~/*.py /zip

