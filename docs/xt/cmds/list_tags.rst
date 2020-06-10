.. _list_tags:  

========================================
list tags command
========================================

Usage::

    xt list tags <name-list> [tag-list] [OPTIONS]

Description::

        list tags of the specified jobs or runs

Arguments::

  name-list    a comma separated list of job or run names, or a single wildcard pattern
  tag-list     a comma separated list of tag names

Options::

  --workspace    str    the workspace for the job to be displayed

Examples:

  list the tags for job3341 and job5535::

  > xt list tags job3341, job5535

