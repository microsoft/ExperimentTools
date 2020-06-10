.. _view_portal:  

========================================
view portal command
========================================

Usage::

    xt view portal <target-name> [OPTIONS]

Description::

        display or browse the URL for the specified backend service portal

Arguments::

  target-name    the name of the target whose portal is to be opened

Options::

  --browse     flag    specifies that the URL should be opened in the user's browser
  --cluster    str     the name of the Philly cluster to be used
  --vc         str     the name of the Philly virtual cluster to be used

Examples:

  view the AML portal for exper5::

  > xt view portal aml --experiment=exper5

