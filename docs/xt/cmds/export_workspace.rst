.. _export_workspace:  

========================================
export workspace command
========================================

Usage::

    xt export workspace <output-file> [OPTIONS]

Description::

        exports a workspace to a workspace archive file

Arguments::

  output-file    the name of the output file to export workspace to

Options::

  --experiment    str_list    matches jobs belonging to the experiment name
  --jobs          str_list    list of jobs to include
  --tags-all      str_list    matches jobs containing all of the specified tags
  --tags-any      str_list    matches jobs containing any of the specified tags
  --workspace     str         the workspace that the run resides in

Examples:

  export workspace ws5 to ws5_workspace.zip::

  > xt export workspace ws5_workspace.zip --workspace=ws5

