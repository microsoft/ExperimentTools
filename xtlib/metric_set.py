#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# metric_set.py: a data structure used by storing and transforming reported metric values
'''
a MetricSet is similiar to a simple DataFrame: it contains a list of dict records, 
where the columns are the keys and values in each record.
'''
from xtlib import errors

class MetricSet():
    def __init__(self, keys, records):
        self.keys = keys
        self.initial_keys = list(keys)
        self.records = records

    def add_column(self, col_name, col_values):
        if col_name in self.keys:
            errors.internal_error("col_name '{}' already in MetricSet".format(col_name))

        if not isinstance(col_values, (list, tuple)):
            # convert single value to a list
            col_values = col_values * len(self.records)

        if len(col_values) != list(self.records):
            errors.internal_error("count of values for col_name '{}' is {}, but count of values in MetricSet is {}".format(col_name, len(col_values), len(self.records)))

        # add to keys
        self.keys.append(col_name)

        # add each value
        for record, value in zip(self.records, col_values):
            record[col_name] in value

    def get_values(self, col_name):
        if not col_name in self.keys:
            errors.internal_error("col_name '{}' not in MetricSet".format(col_name))

        values = [rec[col_name] for rec in self.records]
        return values

    def get_grouped_values(self, col_name, group_by):
        if not col_name in self.keys:
            errors.internal_error("col_name '{}' not in MetricSet".format(col_name))

        values = [rec[col_name] for rec in self.records]
        return values

    def smooth_values(self, col_name, group_by, smooth_func):
        presmooth_values = self.get_grouped_values(col_name, group_by)

        smooth_values = smooth_func(values)



