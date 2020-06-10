.. _list_runs:  

========================================
list runs command
========================================

Usage::

    xt list runs [run-list] [OPTIONS]

Description::

        This command is used to display a tabular report of runs.

    The columns shown can be customized by the run-reports:column entry in the XT config file.  In addition to specifying which columns to display,
    you can also customize the appearance of the column header name and the formatting of the column value.  Examples:

        - To display the hyperparameter "discount_factor" as "discount", specify the column as "discount_factor=factor".
        - To display the value for the "steps" metric with the thousands comma format, specify the column as "steps:,".
        - To specify the column "train-acc" as "accuracy" with 5 decimal places, specify it as "train-acc=accuracy:.5f".

    The --filter option can be used to show a subset of all runs in the workspace.  The general form of the filter is <column> <relational operator> <value>.
    Values can take the form of integers, floats, strings, and the special symbols $true, $false, $none, $empty (which are replaced with the corresponding Python values).

    Examples:

        - To show runs where the train-acc metric is > .75, you can specify: --filter="train-acc>.75".
        - To show runs where the hyperparameter lr was == .03 and the test-f1 was >= .95, you can specify the filter option twice: --filter="lr=.03"  --filter="test-f1>=.95"
        - To show runs where the repeat is set to something other than None, --filter="repeat!=$none".

Arguments::

  run-list    a comma separated list of: run names, name ranges, or wildcard patterns

Options::

  --add-columns      str_list         list of columns to add to those in config file
  --all              flag             don't limit the output; show all records matching the specified filters
  --available        flag             show the columns (std, hyperparameter, metrics) available for specified runs
  --box              str_list         a list of boxes on which the runs were running (acts as a filter)
  --child            flag             only list child runs
  --columns          str_list         specify list of columns to include
  --experiment       str_list         a list of experiment names (acts as a runs filter)
  --export           str              will create a tab-separated file for the report contents
  --filter           prop_op_value    a list of filter expressions used to include matching records
  --first            int              limit the output to the first N items
  --flat             flag             do not group runs
  --group            str              the name of the column used to group the report tables
  --job              str_list         a list of jobs names (acts as a runs filter)
  --last             int              limit the output to the last N items
  --max-width        int              set the maximum width of any column
  --number-groups    flag             the name of the column used to group the report tables
  --outer            flag             only outer (top) level runs
  --parent           flag             only list parent runs
  --precision        int              set the number of factional digits for float values
  --reverse          flag             reverse the sorted items
  --service-type     str_list         a list of back services on which the runs executed (acts as a filter)
  --sort             str              the name of the report column to use in sorting the results
  --status           str_list         match runs whose status is one of the values in the list [one of: created, allocating, queued, spawning, running, completed, error, cancelled, aborted, unknown]
  --tags-all         str_list         matches records containing all of the specified tags
  --tags-any         str_list         matches records containing any of the specified tags
  --target           str_list         a list of compute targets used by runs (acts as a filter)
  --username         str_list         a list of usernames to filter the runs
  --workspace        str              the workspace for the runs to be displayed

Examples:

  display a runs report for the current workspace::

  > xt list runs

  display the child runs for run302::

  > xt list runs run302.*

  display the runs of job132, sorted by the metric 'test-acc', showing only the last 10 records::

  > xt list runs --job=job2998 --last=10 --sort=metrics.test-acc

  display the runs that were terminated due to an error::

  > xt list runs --status=error

  only display runs that have run for more than 100 epochs::

  > xt list runs --filter='epochs > 100'

.. seealso:: 

    - :ref:`Using the XT CLI <cmd_options>`
