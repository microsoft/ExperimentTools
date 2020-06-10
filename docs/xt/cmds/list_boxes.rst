.. _list_boxes:  

========================================
list boxes command
========================================

Usage::

    xt list boxes [wildcard] [OPTIONS]

Description::

        list the boxes (remote computers) defined in your XT config file

Arguments::

  wildcard    a wildcard pattern used to select box names

Options::

  --detail    flag    when specified, the associated job information is included
  --first     int     limit the list to the first N items
  --last      int     limit the list to the last N items

Examples:

  list the boxes defined in the XT config file::

  > xt list boxes

