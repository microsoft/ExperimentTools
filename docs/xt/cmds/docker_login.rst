.. _docker_login:  

========================================
docker login command
========================================

Usage::

    xt docker login [OPTIONS]

Description::

        logs the user into docker using docker credentials from the XT config file


Options::

  --docker    str    the docker environment that defines the docker registry for login
  --target    str    one of the user-defined compute targets on which to run

Examples:

  log user into docker::

  > xt docker login

