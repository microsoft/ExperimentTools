#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# bag.py: simple object that we can add attributes to using dot notation 

class Bag:     # for quick attribute objects
    def __str__(self):
        text = "{"
        for name, value in self.__dict__.items():
            if not text == "{":
                text += ", "
            text += name + "=" + str(value)

        text += "}"
        return text 

    def __repl__(self):
        return self.__str__()

    def get_dict(self):
        return self.__dict__

