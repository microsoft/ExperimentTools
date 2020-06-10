.. _cmd_options:

==================
Using the XT CLI 
==================

Every command you issue in XT has a set of directives you use to shape how the command works and what it works on. These are called *command options*.

You can customize XT command actions through two methods:
    - Override the default XT config file properties with a *local* XT config file. Your local config file takes precedence over the default XT config file (see :ref:`Understanding the XT Config file <xt_config_file>` for more information);
    - Override default and local config file properties using *command options* in the XT CLI. These take precedence over any config file properties.

This topic describes how to use XT command options in the XT CLI, and additional CLI elements you'll need to know about.

    - *Command flags*, which you can use in all CLI commands when needed. See :ref:`Using XT flags <usingxtflags>` for more information.
    - *XT command pipes*, which allow you to tie two or more XT commands into a single longer expression to create new and more powerful combinations. See :ref:`XT Command Piping <pipes>` for more information.
    - Customize data displays from the **xt list runs** and **xt list jobs** commands using properties in your local xt_config file. See :ref:`Filtering Job and Run Listings <filteringjobs>` for more information.
    - **Filtering**, using a special XT command option called *--filter*. See :ref:`Managing Data Columns in XT <datacolumns>` for more information.

.. note:: The **xt run** command is a special case with some syntax differences.

We also discuss some key tools to run the important **xt list runs** and **xt list jobs** commands.

------------------------------------------
Standard XT command options
------------------------------------------

The syntax for all XT commands (excluding **xt run**) is as follows::

   - **xt** [ <root options/flags> ] <**command keyword**> <command arguments> <command options>

XT uses two main types of command options. Rules for their placement in an XT command are as follows:

    - *Root* options appear before the command keyword and define settings for the command to do its work. They apply to each XT command and always use two hyphens, such as::

        --plot-type

    - *XT* command options are command-specific and appear after the command keyword(s)). Use them to specify Python scripts, scripts of other types, and operating system commands & executables. These options also always use two hyphens, such as::

        --filter

-------------------
Command value types
-------------------

XT CLI commands and command options act on a number of different types of data. As you get more familiar with the command set and the types of data you're working with, you'll start seeing them everywhere. 

Option data value types include the following:
    - flag            (**true** or **false**, 0 or 1, 'on' or 'off')
    - string          (quoted string; can be unquoted if value is a simple token)
    - int             (integer value)
    - float           (floating point number)
    - bool            (**true** or **false**)
    - string list     (a comma separated list of unquoted strings - a single-row array)
    - number list     (a comma separated list of numbers - can be mixture of ints and floats)
    - prop_op_value   (a triple of a property name, a relational operator, and a string or number value, with no spaces between the parts)

-------------------------------------
Specifying XT root options
-------------------------------------

Root options (**console**, **stack-trace**, etc.) appear immediately after the **xt** name.  These options apply to all XT commands and control how much output is displayed during command execution.

For root command options, always use the general syntax with a double hyphen (--)::

    --<name>=<value>

Where the <name> of the option (such as **cluster=**) equates to a <value> (such as **ML_Cluster_102**)::

    --cluster=ML_Cluster_102

Example::

    xt **--console=diagnostics** list runs

The command executes the XT 'list runs' command, enabling timing and diagnostic messages.

Command options appear *after* invoking the command::

    > xt list runs **--sort=metrics.test-acc --last=15**

Root options and command options may coexist in the same command::

    > xt --console=diagnostics list runs --sort=metrics.test-acc --last=15

----------------------
XT Run command options
----------------------

XT run command options are a special case, because they apply only to the **xt run** command. You use **xt run** to execute scripts, run executable programs, or to invoke operating system commands;  its primary task is to run jobs for machine learning. **Xt run** also uses a substantial set of dedicated root options.

The syntax for the **xt run** command is::

   xt [ <root options> ] run [ <run options> ] <script file> [ <script arguments> ]

XT run command options also use the double-hyphen convention, such as::

    --attach=
    --cluster=

Run command options apply only to the **run** command and must appear before the **run** keyword in the XT run command. See the section :ref:`XT run command <run>` for more information about **run** command options.

At any time, enter::

    > xt help run 

XT shows a complete listing and descriptions of **xt run**'s root options, arguments, and examples.

.. _usingxtflags:

--------------
Using XT flags
--------------

XT flags are global to all XT commmands. They appear before any command names, similar to root options. You use flags in XT commands to enable a limited set of capabilities, including stack tracing, levels of console output, enabling a faster startup time, and showing help for XT commands.

**Flags** are a small subset of command options that don't require a `<value>`. When you invoke a flag by its name, it's automatically set to **true**. 

You can also explicitly set flags to **On** (using **on**, **true**, or **1**) or **Off** (using **off**, **false**, or **0**).

Current XT flags include the following::

    --console         (option)  Sets the level of console output (specify *none*, *normal*, *diagnostics*, or *detail*)
    --help            (flag)    Shows an overview of XT command syntax
    --stack-trace     (flag)    Show the stack trace when an exception is raised
    --quick-start     (flag)    XT startup time is reduced (experimental)

.. code-block::

    xt --help

    xt --console=detail monitor job3321

    xt --stack-trace run job3321

---------------------------------------
Specifying string values in XT commands
---------------------------------------

Because XT is a command line program, it gets most of its input from the OS command line shell. To use strings as arguments in command options, format the strings depending on the operating system on which you are running XT. Text string formatting is as follows:

    - On Linux, remove single and double quotes; 
    - On Windows, remove double quotes.

We recommend the following when specifying string values to XT.

    - For strings that consist of a single token, no quotes are needed::

        title=Accuracy

    - On Windows, use brackets '{}' *or* single quotes::
        
        --title={this is my title}
        --title='this is my title'

    - On Linux, use {}, nested quotes, *or* escaped quotes::

        --title={this is my title}
        --title="'this is my title'"
        --title=\'this is my title\'

.. _pipes:

----------------------
XT Command Piping
----------------------

Two XT commands support query options: **xt list runs** and **xt_list_jobs**. Several other XT commands accept a list of runs or jobs, but don't support the same query options.

For commands that don't support query options, you can use *command line piping* to pipe runs or jobs matched by a query command to another XT command. You can use them in Windows or Linux command lines. The pipe character (|) enables you to string two or more commands together to create more effective XT CLI operations.

*******************
Pipe examples
*******************

Consider a case where you want to tag the top 15 highest scoring runs with "Top15". Use the **xt list runs** command with the necessary filters and sorting, and then copy/paste or enter the run names into the "set tags" command.

With XT command piping, you can do this in one step. The *pipe* symbol (|) enables you to chain two XT commands to achieve a result::

    > xt list runs --sort=metrics.test-acc --last=15 | xt set tags **$ Top15**

As the second command following the pipe, the *xt set tags* command specifies a '$' in the location where the run names from the first command will be inserted. The '$' is required; without it, XT ignores the names from the incoming argument.

Show the most recently completed 10 runs in a set of plots::

    > xt list runs --status=completed --last=10 | xt plot $ train-acc, test-acc --layout=2x5

After the pipe, the **xt plot** command receives the specified data and formats it into a table. Data plots can be hard to read on-screen; the following section gives you tools to manage them.

.. _datacolumns:

---------------------------
Managing Data Columns in XT 
---------------------------

You can customize data columns shown in the reporting commands **list runs** and **list jobs**. The benefit is that you can have your job and run reports show only the information that's important to your work. You can keep some control over the reporting data that appears in your CLI console session.

Edit the *run-reports* and *job-reports* **columns** properties in your XT installation's local xt_config file. 

.. note:: When you add new column display settings to your local xt_config file, they override the settings in the XT installation's *default* xt_config file. 

****************************************
Where are the default column properties?
****************************************

The default xt_config file's *run-reports* **columns** property includes the following list of columns that appear by default in run reports::

    # "columns" defines the columns to show (and their order) for the "list runs" cmd.  The columns listed 
    # should be a standard column, or a user-logged hyperparameter or metric.  use "list runs --available" to find available columns.
    columns: ["run", "created:$do", "experiment", "queued", "job", "target", "repeat",      
        "search", "status", "tags.priority", "tags.description", "hparams.lr", 
        "hparams.momentum", "hparams.optimizer", "hparams.steps", "hparams.epochs", 
        "metrics.step", "metrics.epoch", "metrics.train-loss", "metrics.train-acc", 
        "metrics.dev-loss", "metrics.dev-acc", "metrics.dev-em", "metrics.dev-f1", 
        "metrics.test-loss", "metrics.test-acc", "duration", 
    ]

The corresponding defaults for the *job-reports* **columns** property are the following::

    # "columns" defines the columns to show (and their order) for the "list jobs" cmd.  The columns listed 
    # should be a standard column.  use "list jobs --available" to find available columns.
    columns: ["job", "created", "started", "workspace", "experiment", "target", 
        "nodes", "repeat", "tags.description", "tags.urgent", "tags.sad=SADD", "tags.funny", 
        "low_pri", "vm_size", "azure_image", "service", "vc", "cluster", "queue", "service_type", 
        "search", "job_status:$bz", "running_nodes:$bz", "running_runs:$bz", "error_runs:$bz", 
        "completed_runs:$bz"]

Each **columns** property is a list of column spec strings. Each column spec string consists of 3 parts:

    column-name     (**required**: name of the column to include)
    =header-name    (*optional*: the name shown in the Column Header, defaults to the column name) 
    :format-code    (*optional*: the Python or XT formatting code to use in formatting values for the column)

Let's look at each of these in more detail:

    *column-name*: if the column is not a standard one, it needs to be prefixed by one of:
        *hparams.*, *metrics.*, *tags.* (as in *hparams.lr*, *metrics.train_loss*, and *tags.important*). You can see more examples in the run-reports and job-reports default lists.

    *header-name*: the text that appears as the header column in the reports. This field is optional and uses the default if left unspecified.

    *format-code*: this can be any of the following:
        - python formatting string (e.g., *.2f*, or ",")
        - $bz     (if value is zero, display as blanks)
        - $do     (display only the date portion of a datetime value)
        - $to     (display only the date portion of a datetime value)

.. note:: For example, you want to rename a particular column name for easier recognition. There's a *run-reports* column named "metrics.train-loss" that you can rename for display: **metrics.train-loss=Training _Loss_Metric"** uses the optional *header-name* argument, whose value here is 'Training_Loss_Argument', to change the default header name in the job listing.

.. note:: Remember: to change column information in your display, you'll always need to make those changes in the local xt_config file. 

***********************************
Column property examples
***********************************

    - To display the hyperparameter "discount_factor" as "discount", specify the column as  *discount_factor=discount*.
    - To display the value for the "steps" metric with the thousands comma format, specify the column as *steps:,*.  
    - To specify the column "train-acc" as "accuracy" with 5 decimal places, specify it as "train-acc=accuracy:.5f".  

*********************************
Where does column data come from?
*********************************

Data columns in the *list runs* command come from 4 sources of data:

    - Standard run columns (e.g., run, status, target, etc.)
    - Hyperparameter name/value pairs logged by the ML app to XT (e.g. lr, optimizer, epochs, or hidden_dim)
    - Metric name/value pairs logged by the ML app to XT (e.g. step, reward, epoch, train-loss, train-acc, test-loss, test-acc)
    - Tag name/value pairs added to the run by the user 

Columns data shown in the *list jobs* command comes from 2 sources:

    - Standard job columns (e.g., job, status, target, etc.)
    - Tag name/value pairs added to the job by the user 

.. note::
    Use the ``--available`` command option to show a list of all available columns within the set of records returned by a reporting command.

.. _filteringjobs:

-------------------------------------
Filtering Job and Run Listings 
-------------------------------------

Filters control which records of interest appear in **list runs** and **list jobs** XT commands.

Use the ``--filter`` command option to show a subset of data for all runs in the workspace. You can specify it multiple times, which combines the expressions with an implicit *AND* operator.

The general form of a filter is:

    <column> <relational operator> <value>

The *column* of a filter can be a standard run name or job column name, or a custom property name prefixed by one of the following:

    - hparams.      (e.g., *hparams.lr* refers to the learning rate hyperparameter logged by the user ML app to XT)
    - metrics.      (e.g., *metrics.train-loss* refers to the training loss metric logged by the user ML app to XT)
    - tags.         (e.g., *tags.category* refers to the tag "category" added to runs or jobs by the user)

.. note::
    Use the ``--available`` command option to get a list of all available columns in the set of records returned by a report.

********************************
Correctly using filter operators
********************************

A filter *operator* can be one of the following:

        - one of the python relational operators: <, <=, >, >=, ==, !=
        - =             (an alternate way to specify the == operator)
        - <>            (an alternate way to specify the != operator)
        - \:regex\:     (treats the value as a regular expression for matching the specified column on each record)
        - \:exists\:    (the existance of the column matches to each record according to the specified true/false value)
        - \:mongo\:     (the value of this filter is interpreted as a mongo-db filter expression)

When using the relational operators for filtering, the command line shell will interpret inequalities '>' and '<' as command redirections. To prevent it from happening, use either of the following:

    - Surround the filter expression with double quotes: --filter="test-acc>.3" (no spaces within string);
    - Surround the filter expression with {} within double quotes: --filter="{test-acc > .3}" (this form accepts spaces in the string).

A filter *value* in an expression can take the form of:

    - integers
    - floats
    - strings
    - $true    (replaced with a python True value)
    - $false   (replaced with a python False value)
    - $none    (replaced with a python None value)
    - $empty   (replaced with a python empty string value)

*******************
Filtering Examples
*******************
        
    - To show runs where the train-acc metric is > .75, you can specify: ``--filter="train-acc>.75"``
    - To show runs where the hyperparameter lr was == .03 and the test-f1 was >= .95, you can specify the filter option twice: ``--filter="lr=.03"  --filter="test-f1>=.95"``
    - To show runs where the repeat is set to something other than None, ``--filter="repeat!=$none"``

.. seealso:: 

    - :ref:`Understanding the XT Config file <xt_config_file>` for more information about configuring your local XT config file for your XT installation;
    - :ref:`Creating your Azure Cloud Services for XT <creating_xt_services>` to define and implement the template for the Azure cloud services that XT uses for ML experiments;
    - :ref:`XT run command <run>`
