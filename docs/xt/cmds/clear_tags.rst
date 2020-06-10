.. _clear_tags:  

========================================
clear tags command
========================================

Usage::

    xt clear tags <name-list> <tag-list> [OPTIONS]

Description::

        clear tags on the specified jobs or runs

Arguments::

  name-list    a comma separated list of job or run names, or a single wildcard pattern
  tag-list     a comma separated list of tag names

Options::

  --workspace    str    the workspace for the job to be displayed

Examples:

  clears the tag 'description' for job3341 and job5535::

  > xt clear tags job3341, job5535 description

