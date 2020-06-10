.. _extend_commands:

======================================
Adding new XT commands
======================================

XT's built-in set of commands, and their associated console and GUI help text, can be extended by the user.

The general idea is to write python class methods for each command you want to add to XT, and decorate the 
each of the methods with a set of XT decorators.

The steps for adding new commands to XT are:
    - import the **xtlib.qfe** module so that you can use its decorators
    - create a python class that will hold one or more command implementations
    - for each new command, add a decorated method to your class
    - add the provider name and its **code path**  as a key/value pair to the **command** provider dictionary in a local XT config file
    - ensure the provider package is available to XT (in the Python path, or a direct subdirectory of your app's working directory), so that 
      XT can load it when needed (which could be on the XT client machine and/or the compute node)

For example, here is the contents of a file called **user_commands.py** that implements a new command for XT that will remove CR characters (\\r) 
from the specified file::

    # demonstration of user-extensible commands in XT
    from xtlib.qfe import command, argument, option, flag, root, example, command_help
    from xtlib import console

        class ImplMyCommands:

            def __init__(self, config, store):
                pass

            #---- dos2unix command ----
            @argument("name", type=str, help="the name of the file to be converted")
            @example(task="remove the CR characters in the file 'big_sleep.sh'", text="xt dos2unix code/big_sleep.sh")
            @faq("why does VS Code still show CRLF for the converted file?", "you need to close/reopen the file for VS Code to refresh this info")
            @command(group="Utility commands", help="converts the specified file from DOS format (CR/LF) to Unix (LF)")
            def dos2unix(self, name):
                with open(name, "rt") as infile:
                    text = infile.read()
                    text = text.replace("\r", "")

                # specify newline="" here to prevent open() from messing with our newlines
                with open(name, "wt", newline="") as outfile:
                    outfile.write(text)

                console.print("CR characters removed: {}".format(name))    

Some notes on the code above (from top, down):
    - the code imports several decorator methods from the **xtlib.qfe** module
    - we use the **@argument** decorator to describe the **name** argument that the command method will accept 
    - we include an **@example** decorator to give an example of how to use the argument
    - we include a **@faq** decorator to state and answer what we think will be a frequently asked question about the command 
    - we include the **@command** decorator, which is required, and must be the last decorator before the method definition itself
    - since no name argument is specified in the **@command** decorator, the command will take its name from the name of the implementation method
    - more details about these and other decorators can be found in the **Quick Front End** help topic (see below)
    - the command prints its user feedback use the XT **console.print** function, which allows control over the level of feedback the user receives

To add this command to XT, we add the following YAML section to our local XT config file::

    providers:
        command: {
            "mycmds": "extensions.user_commands.ImplMyCommands" 
        }

Where **extensions** is the parent directory of the **user_commands.py** file).

.. seealso:: 

    - :ref:`XT Config file <xt_config_file>`
    - :ref:`Quick Front End <quick_front_end>`
    - :ref:`Extensibility in XT <extensibility>`
