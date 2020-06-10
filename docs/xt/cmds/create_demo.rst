.. _create_demo:  

========================================
create demo command
========================================

Usage::

    xt create demo <destination> [OPTIONS]

Description::

        This command will removed the specified destination directory if it exists (prompting the user for approval).
    Specifying the current directory as the destination will produce an error.

Arguments::

  destination    the path in which the demo files should be created

Options::

  --overwrite    flag    When specified, any existing xtd-prefixed job names that match xt-demo job names will be overwritten
  --response     str     the response to be used to confirm the directory deletion

Examples:

  create a set of demo files in the subdirectory xtdemo::

  > xt create demo ./xtdemo

