#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# demonstration of user-extensible commands in XT
from xtlib.qfe import command, argument, option, flag, root, example, command_help
from xtlib import console

class ImplMyCommands:

    def __init__(self, config, store):
        pass

    #---- dos2unix command ----
    @argument("name", type=str, help="the name of the file to be converted")
    @example(task="remove the CR characters in the file 'big_sleep.sh'", text="xt dos2unix code/big_sleep.sh")
    @command(group="Utility commands", help="converts the specified file from DOS format (CR/LF) to Unix (LF)")
    def dos2unix(self, name):
        with open(name, "rt") as infile:
            text = infile.read()
            text = text.replace("\r", "")

        # specify newline="" here to prevent open() from messing with our newlines
        with open(name, "wt", newline="") as outfile:
            outfile.write(text)

        console.print("CR characters removed: {}".format(name))
