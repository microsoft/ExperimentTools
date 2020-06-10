.. _set_tags:  

========================================
set tags command
========================================

Usage::

    xt set tags <name-list> <tag-list> [OPTIONS]

Description::

        set tags on the specified jobs or runs

Arguments::

  name-list    a comma separated list of job or run names, or a single wildcard pattern
  tag-list     a comma separated list of tag name or tag assignments

Options::

  --workspace    str    the workspace for the job to be displayed

Examples:

  add the tag 'description' with the value 'explore effects of 5 hidden layers' to the jobs job3341 thru job3356::

  > xt set tags job3341-job3356 description='explore effects of 5 hidden layers'

