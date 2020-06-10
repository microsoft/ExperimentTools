#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# notebook_builder.py: builds a Jypyter Notebook
import sys
import json

from xtlib import utils

class NotebookBuilder():
    def __init__(self, kernel_name, kernel_display_name):
        self.kernel_name = kernel_name
        self.kernel_display_name = kernel_display_name
        self.cells = []
        self.metadata = {}
        self.build_metadata()
        
    def build_metadata(self):
        self.metadata = \
        {
            "kernelspec": 
            {
                "display_name": self.kernel_display_name,
                "language": "python",
                "name": self.kernel_name.lower()
            },
            "language_info": 
            {
                "codemirror_mode": 
                {
                    "name": "ipython",
                    "version": 3
                },
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                #"version": "3.6.8"
            }
        }

    def add_code_cell(self, code_lines):
        cell = \
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": code_lines
        }
        self.cells.append(cell)

    def save_to_file(self, fn):
        nb = {"cells": self.cells, "metadata": self.metadata, 
            "nbformat": 4, "nbformat_minor": 2}

        text = json.dumps(nb)
        file_utils.ensure_dir_exists(file=fn)

        with open(fn, "wt") as outfile:
            outfile.write(text)