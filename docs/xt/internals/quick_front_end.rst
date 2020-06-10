.. _quick_front_end:

=============================
QFE: Quick Front End Builder
=============================

This page describes the QFE subsystem which is used to build the command line parser for XT.

QFE works by decorating functions or methods that expose commands.  QFE available decorators:

    @command       - exposes the function as a command
    @root          - marks the function for processing root flag value changes
    @argument      - denotes an unamed value used the by command 
    @option        - denotes a named value (always optional)
    @flag          - denotes a name property with an optional boolean value
    @hidden        - denotes a hidden option whose value is extracted from the config file 
    @example       - provides an example of using the command
    @faq           - provides an frequently asked question and answer pair for the command
    @clone         - used to copy attributes and options a previously defined commands

The following explains each decorator and its parameters in more detail.

@command
--------

    Parameters:

        name (default: None)::  

            - the name of the command.  if not specified, it will be set to the function name.  the exposed command name
            is formed by replacing the "_" characters in the name with spaces.

        options_before_args (default: False)::  

            - by default, the order of elements in a command are:
                <command keywords> <command arguments> <command options>

            - when options_before_args is set to True, the following order is used (useful for run type commands):
                <command keywords> <command options> <command arguments> 

        keyword_optional (default: False)::  

            - when set to True, the keyword for the command is optional.  This can only be set only on one command.

        pass_by_args (default: False)::  

            - by default, each argument, option, and flag are passed by name to the associated function.  when 
            pass_by_args is set to True, all of these are passed as a single dictionary parameter called "args"

        help (default: ""):: 

            - this string provides the information about the command for XT help (general and command-specific).  it
            is also used to generate .RST help pages, if no doc string is specified on the function.

    Semantics:

    Functions in xtlib with an '@command' decorator are exposed as XT commands.  Because of the order of decorator processing,
    the @command decorator must the defined after any other decorators for the function, and just before the function itself
    is defined.  Multi-word commands are supported by naming the function with underscore characters between the command keywords.
    Arguments, options, and flags can be defined for the command by including those decorators before the @command.  Note, most command kewords 
    can be abbreviated down to 4 letters for quicker interactive use.

@root
-----

    Parameters:

        help (default: "")
            - this parameter is not currently used, since this function is hidden for help purposes

    Semantics:

        This marks a function (there can only be one such marking) as the callback function for processing the setting of root flags (flags that apply to all commands).
        @flag decorators for each root flag needed by the CLI (command-line interface) shoud proceed this @root.  The callback function should accept 2 named parameters: 
        'name' and 'value', which correspond to the name of root flag being set, and its value (as specified by the user on the command line).

@argument
---------

    Parameters:

        name (required):: 

            - this names the argument for use when displaying help for the associated command
            
        required (default: True):: 

            - if required and a value is not supplied by the user, an error will be issued.
            
        type (default: str):: 

            - the type of the argument.  If the argument value supplied by the user isn't compatible, an error will be issued.  The processed argument 
            value is passed to the command function when the function is called at the end of parsing.

        help (default: ""):: 

            - this string provides the information about the command for XT help (general, command-specific, and docs generation).

    Semantics:

        @argument defines the unnamed values that the command expects/accepts.  Typically, there are 0-2 arguments per command.  The last argument can be
        defined as required=False.

@option
-------

    Parameters:

        name (required):: 

            - this names the option.  This is the same name that will be used by the CLI user when specifying option values, as well as 
              for use when displaying help for the associated command.
            
        default (default: None):: 

            - this specifies the value for the option when it is not specified by the user at the CLI.  if the default value specified here
              is of the form '$groupname.propertyname", it is processed as a config file look-up with the associated group and property names.

        required (default: None):: 

            - if required and a correctly named value is not supplied by the user, an error will be issued.  Most options are not required.
            
        type (default: str):: 

            - the type of the argument.  If the argument value supplied by the user isn't compatible, an error will be issued.  The processed argument 
            value is passed to the command function when the function is called at the end of parsing.

        multiple (default: False):: 
         
            - when set to True, multiple instances of the option build up a list of the values for processing by the command.  When False,
              only the last instance value is used.

        help (default: ""):: 

            - this string provides the information about the command for XT help (general, command-specific, and docs generation).

    Semantics:

        @option defines the named values that the command accepts.  The number of options typically ranges from 0-5, but some commands use over 20.  When the 
        user supplies these values for XT, it is a best practice to use the 'name=value' form.  Note, most names can be abbreviated down to 4 letters for 
        quicker interactive use.
       

@flag
-------

    Parameters:

        name (required):: 

            - this names the flag.  This is the same name that will be used by the CLI user when specifying flag values, as well as 
              for use when displaying help for the associated command.

        default (default: None):: 

            - this specifies the value for the option when it is not specified by the user at the CLI.  if the default value specified here
              is of the form '$groupname.propertyname", it is processed as a config file look-up with the associated group and property names.

        type (default: str):: 

            - the type of the argument.  If the argument value supplied by the user isn't compatible, an error will be issued.  The processed argument 
            value is passed to the command function when the function is called at the end of parsing.

        help (default: ""):: 

            - this string provides the information about the command for XT help (general, command-specific, and docs generation).

    Semantics:

        @option defines the named values that the command accepts.  The number of options typically ranges from 0-5, but some commands use over 20.  When the 
        user supplies these values for XT, it is a best practice to use the 'name=value' form.  Note, most names can be abbreviated down to 4 letters for 
        quicker interactive use.
       

@hidden
-------

    Parameters:

        name (required):: 

            - this names the hidden config property.  
            
        default (default: None):: 

            - this specifies the value for the option when it is not specified by the user at the CLI.  if the default value specified here
              is of the form '$groupname.propertyname", it is processed as a hidden file look-up with the associated group and property names.

        type (default: str):: 

            - the type of the argument.  If the argument value supplied by the user isn't compatible, an error will be issued.  The processed argument 
            value is passed to the command function when the function is called at the end of parsing.

        help (default: ""):: 
        
            - this value is not currently used for @hidden entries.

    Semantics:

        @hidden entries function like hidden @options.  they are used to pass values to the associated command function, usually as config file look-ups,
        but constant default values can also be used.

@example
--------

    Parameters:

        task (required)
            - this should describe the operation being done in the exaple.
            
        text (required)
            - this contains the XT command string for the example.  Running this string should perform the task described above.

    Semantics:

        @example entries are collected for each command and displayed in command-specific help, as well as included in docs generation for each command.

@faq
--------

    Parameters:

        question (required)
            - the text of a frequently asked question about the command.  
            
        answer (required)
            - the answer to the question.

    Semantics:

        @faq entries provide information about the command from the perspective of the user.  They are collected for each command and displayed in command-specific help, as well as included in docs generation for each command.

@clone
------

    Parameters:

        source (required)
            - the name of the command whose attribute/options are to be cloned.
            
        arguments (default: True)
            - when True, the arguments from the source are copied into this command.

        options (default: True)
            - when True, the options and flags from the source are copied into this command.

    Semantics:

        @clone is used for commands that share a large set of common arguments, options, and flags.  


Argument and Option supported types:
------------------------------------

    str             - string (parsed as a token file filename type characters allowed)
    int             - integer 
    float           - floating point number
    flag            - an optional boolean value (can be any of: 0, 1, true, false, on, off)
    str_list        - a comma separated list of str values
    prop_op_value   - a string of the form: <property-name> <relational-op> <value>


How QFE is used in XT:
----------------------

    QFE is implemented in the file qfe.py.

    In the file xt_cmds.py (about 75 lines of python), you can see how to:
        - create a QFE instance
        - hide selected commands
        - dispatch the main command

    In XT, the decorated function for each command are defined in 4 files:

        - impl_compute.py   - commands for creating and controlling runs and related services
        - impl_help.py      - commands and function for general help, command-specific help, and .rst file generation
        - impl_storage.py   - commands for accessing files and blobs in Azure storage services
        - impl_utilities.py - utility commands related to the ML experiement lifecycle
