.. _list_jobs:  

========================================
list jobs command
========================================

Usage::

    xt list jobs [job-list] [OPTIONS]

Description::

        This command is used to display a tabular report of jobs.

    The columns shown can be customized by the job-reports:column entry in the XT config file.  In addition to specifying which columns to display,
    you can also customize the appearance of the column header name and the formatting of the column value.  Examples:

        - To display the column "job_status" as "status", specify the column as "job_status=status".

    The --filter option can be used to show a subset of all runs in the workspace.  The general form of the filter is <column> <relational operator> <value>.
    Values can take the form of integers, floats, strings, and the special symbols $true, $false, $none, $empty (which are replaced with the corresponding Python values).

    Examples:

        - To show runs where the repeat is set to something other than None, --filter="repeat!=$none".

Arguments::

  job-list    a comma separated list of job names, or a single wildcard pattern

Options::

  --all             flag             don't limit the output; show all records matching the specified filters
  --available       flag             show the columns (name, target, search-type, etc.) available for jobs
  --columns         str_list         specify list of columns to include
  --experiment      str_list         a list of experiment names for the jobs to be displayed (acts as a filter)
  --export          str              will create a tab-separated file for the report contents
  --filter          prop_op_value    a list of filter expressions used to include matching records
  --first           int              limit the output to the first N items
  --last            int              limit the output to the last N items
  --max-width       int              set the maximum width of any column
  --precision       int              set the number of factional digits for float values
  --reverse         flag             reverse the sorted items
  --service-type    str_list         a list of backend services associated with the jobs (acts as a filter)
  --sort            str              the name of the report column to use in sorting the results
  --tags-all        str_list         matches records containing all of the specified tags
  --tags-any        str_list         matches records containing any of the specified tags
  --target          str_list         a list of compute target associated with the jobs (acts as a filter)
  --username        str_list         a list of usernames that started the jobs (acts as a filter)
  --workspace       str              the workspace for the job to be displayed

Examples:

  display a report of the last 5 jobs that were run::

  > xt list jobs --last=5

.. seealso:: 

    - :ref:`Using the XT CLI <cmd_options>`
