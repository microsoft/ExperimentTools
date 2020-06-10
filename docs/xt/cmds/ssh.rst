.. _ssh:  

========================================
ssh command
========================================

Usage::

    xt ssh [OPTIONS] <name> [cmd]

Description::

        executes the specified command, on begins a console session, with the specified box

Options::

  --output       str    the name of the file to write the cmd output to
  --workspace    str    the workspace for the runs to be displayed

Arguments::

  name    the box or run name to communicate with or connect to
  cmd     the optional command to execute

Examples:

  initiate a remote console session with box 'vm10'::

  > xt ssh vm10

  get a directory listing of files on box 'vm23''::

  > xt ssh vm10 ls -l

