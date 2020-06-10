.. _view_events:  

========================================
view events command
========================================

Usage::

    xt view events <name> [OPTIONS]

Description::

        view formatted information in the XT event log

Arguments::

  name    name of the event log
          --> choose one: xt, controller, quick-test


Options::

  --all     flag    specify to display all entries
  --last    str     the number of most recent entries to display

Examples:

  view the most recent events in the XT log::

  > xt view events xt

