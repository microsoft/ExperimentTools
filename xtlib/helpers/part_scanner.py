#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# part_scanner.py: works like a scanner for a list of parts

class PartScanner():
    def __init__(self, parts):
        self.parts = parts
        self.index = 0
        self.part = None

    def scan(self):
        if self.parts:
            if self.index < len(self.parts):
                self.part = self.parts[self.index]
                self.index += 1
            else:
                self.part = None

        return self.part
    
    def peek(self):
        part = None

        if self.parts:
            if self.index < len(self.parts):
                part = self.parts[self.index]

        return part