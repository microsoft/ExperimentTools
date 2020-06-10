.. _list_targets:  

========================================
list targets command
========================================

Usage::

    xt list targets [wildcard] [OPTIONS]

Description::

        list the user-defined compute targets

Arguments::

  wildcard    a wildcard pattern used to select compute names

Options::

  --detail    flag    when specified, the associated job information is included
  --first     int     limit the list to the first N items
  --last      int     limit the list to the last N items

Examples:

  list the compute targets along with their definitions::

  > xt list computes --detail

