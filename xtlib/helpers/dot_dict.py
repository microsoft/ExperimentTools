#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# dotDict.py: dict wrapper class to enable read/write of values by both keys and attributes.

class DotDict(dict):
    '''
    Reminder: this is based on the DICT class, so it's self.__dict__ is an empty {}.
    '''
    def __init__(self, dict):
        super(DotDict, self).__init__(dict)

    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError("Unknown attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    