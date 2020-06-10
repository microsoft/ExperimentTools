#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# reportt_builder.py: builds the report shown in "list jobs", "list runs", etc. cmds
import os
import json
import time
import arrow
import datetime
import logging
from fnmatch import fnmatch
from collections import OrderedDict

from .console import console

from xtlib import qfe
from xtlib import utils
from xtlib import errors
from xtlib import constants

class ReportBuilder():
    def __init__(self, config, store, client):
        self.config = config
        self.store = store
        self.client = client
        self.user_col_args = {}

    def wildcard_matches_in_list(self, wc_name, name_list, omits):
        matches = []

        if name_list:
            matches = [name for name in name_list if fnmatch(name, wc_name) and not name in omits]
            
        return matches

    def default_user_name(self, col_name):
        user_name = col_name

        if col_name.startswith("hparams."):
            user_name = col_name[8:]
        elif col_name.startswith("metrics."):
            user_name = col_name[8:]
        else:
            user_name = col_name

        return user_name

    def get_requested_cols(self, user_col_args, avail_list):
        actual_cols = []
        new_col_args = {}
        
        for key, value in user_col_args.items():
            # if the requested key is available, include it
            if "*" in key:
                # wildcard match
                 matches = self.wildcard_matches_in_list(key, avail_list, ["metrics." + constants.STEP_NAME, "metrics.$step_name"])
                 actual_cols += matches

                 # replace our wilcard in request_list with matches
                 for match in matches:
                    user_name = self.default_user_name(match)
                    new_value = {"user_name": user_name, "user_fmt": None}
                    new_col_args[match] = new_value

            elif key in avail_list:
                actual_cols.append(key)
                new_col_args[key] = value
        
        return actual_cols, new_col_args

    def sort_records(self, records, sort_col, reverse):
        if reverse is None:
            reverse = 0

        console.diag("after reportbuilder SORT")
        console.diag("sort_col={}".format(sort_col))

        # normal sort
        records.sort(key=lambda r: r[sort_col] if sort_col in r and r[sort_col] else 0, reverse=reverse)

        console.diag("after reportbuilder SORT")

    def expand_special_symbols(self, value):
        value = value.strip()

        if value == "$none":
            value = {"$type": 10}
        elif value == "empty":
            value = ""
        elif value == "$true":
            value = True
        elif value == "$false":
            value = False
        elif value == "$exists":
            value = {"$exists": True}

        return value

    def process_filter_list(self, filter_dict, filter_exp_list, report2filter):
        '''
        used to filter records for following expressions of form:
            - <prop name> <relational operator> <value>

        special values:
            - $exists   (does property exist)
            - $none     (None, useful for matching properties with no value)
            - $empty    (empty string)
            - $true     (True)
            - $false    (False)
        '''
        for filter_exp in filter_exp_list:
            prop = filter_exp["prop"]
            op = filter_exp["op"]
            raw_value = filter_exp["value"]
            
            #print("prop=", prop, ", op=", op, ", raw_value=", raw_value)

            value = self.expand_special_symbols(raw_value)

            # translate name, if needed
            if prop in report2filter:
                prop = report2filter[prop]

            value = utils.make_numeric_if_possible(value)
            #console.print("prop, op, value=", prop, op, value)

            if op in ["=", "=="]:
                filter_dict[prop] = value
            elif op == "<":
                filter_dict[prop] = {"$lt": value}
            elif op == "<=":
                filter_dict[prop] = {"$lte": value}
            elif op == ">":
                filter_dict[prop] = {"$gt": value}
            elif op == ">=":
                filter_dict[prop] = {"$gte": value}
            elif op in ["!=", "<>"]:
                filter_dict[prop] = {"$ne": value}
            elif op == ":regex:":
                filter_dict[prop] = {"$regex" : value}
            elif op == ":exists:":
                filter_dict[prop] = {"$exists" : value}
            elif op == ":mongo:":
                # raw filter dict, but we need to translate quotes and load as json
                value = value.replace("`", "\"")
                value = json.loads(value)
                filter_dict[prop] = value
            else:
                errors.syntax_error("filter operator not recognized/supported: {}".format(op))
        
    def available_cols_report(self, report_type, std_list, std_cols_desc, hparams_list=None, metrics_list=None, tags_list=None):
        lines = []

        std_list.sort()

        lines.append("")
        lines.append("Standard {} columns:".format(report_type))
        for col in std_list:
            if col in ["hparams", "metrics", "tags"]:
                continue

            if not col in std_cols_desc:
                console.print("internal error: missing description for std col: " + col)
                desc = ""
            else:
                desc = std_cols_desc[col]

            lines.append("  {:<14s}: {}".format(col, desc))

        if hparams_list:
            hparams_list.sort()
            lines.append("")
            lines.append("Logged hyperparameters:")
            for col in hparams_list:
                lines.append("  {}".format(col))

        if metrics_list:
            metrics_list.sort()
            lines.append("")
            lines.append("Logged metrics:")
            for col in metrics_list:
                lines.append("  {}".format(col))

        if tags_list:
            tag_list.sort()
            lines.append("")
            lines.append("Tags:")
            for col in tag_list:
                lines.append("  {}".format(col))

        return lines

    def build_avail_list(self, col_dict, record, prefix=""):
        subs = ["metrics", "hparams", "tags"]

        for key in record.keys():
            if key in subs:
                self.build_avail_list(col_dict, record[key], prefix=key + ".")
            else:
                col_dict[prefix + key] = 1

    def flatten_records(self, records, sort_col, args):
        '''
        pull out the cols specified by user, flattening nested props to their dotted names.
        '''
         # build avail col list based on final set of filtered records

        actual_cols, user_col_args  = self.get_actual_and_user_cols(records, args)

        # flatten each record's nested columns
        records = [self.extract_actual_cols(rec, actual_cols) for rec in records if rec]
        return records

    def extract_actual_cols(self, record, actual_cols):
        '''
        pull out the cols specified in actual_cols, flattening nested props to their dotted names.
        '''
        new_record = {}

        for actual_key in actual_cols:
            if not actual_key:
                continue

            empty_value = constants.EMPTY_TAG_CHAR if actual_key.startswith("tags.") else None

            if "." in actual_key:
                # its a NESTED reference
                outer_key, inner_key = actual_key.split(".")

                if outer_key in record:
                    inner_record = record[outer_key]
                    if inner_record and inner_key in inner_record:
                        value = inner_record[inner_key]
                        new_record[actual_key] = value if value is not None else empty_value
            else:
                # its a FLAT reference
                if actual_key in record:
                    value = record[actual_key]
                    new_record[actual_key] = value if value is not None else empty_value
    
        return new_record

    def translate_record(self, record, actual_to_user):
        '''
        pull out the cols specified in actual_to_user, translating from storage names to user names.
        '''
        new_record = {}

        for actual_key, user_key in actual_to_user.items():
            if not actual_key:
                continue

            if actual_key in record:
                value = record[actual_key]
                new_record[user_key] = value 
    
        return new_record

    def get_first_last(self, args):
        first = utils.safe_value(args, "first")
        last = utils.safe_value(args, "last")
        show_all = utils.safe_value(args, "all")

        explict = qfe.get_explicit_options()

        # explict overrides default for all/first/last
        if "all" in explict:
            first = None
            last = None
        elif "first" in explict:
            show_all = None
            last = None
        elif "last" in explict:
            show_all = None
            first = None
        else:
            # priority if no explict options set
            if show_all:
                first = None
                last = None

        return first, last

    def get_mongo_records(self, mongo, filter_dict, workspace, which, actual_to_user, 
            col_dict=None, args=None):

        first, last = self.get_first_last(args)

        if last:
            using_default_last = True
        else:
            using_default_last = False

        reverse = utils.safe_value(args, "reverse")
        # use MONGO to do all of the work (query, sort, first/last)
        sort_col = utils.safe_value(args, "sort", "name")

        if sort_col == "name":
            # special sorting needed; we have created "run_num" field just for this purpose
            sort_col = "run_num" if which == "runs" else "job_num"
        elif not "." in sort_col:
            # translate name of std col from user-friendly version to logged version
            user_to_actual = {value: key for key, value in actual_to_user.items()}

            if not sort_col in user_to_actual:
                errors.general_error("unknown standard property: {} (did you mean metrics.{}, hparams.{}, or tags.{}?)". \
                    format(sort_col, sort_col, sort_col, sort_col))

            sort_col = user_to_actual[sort_col]

        # this is a TRICK to avoid having to call for the exists_count for calculation of skip count
        # it works fine, since we re-sort records on the xt client anyway
        sort_dir = -1 if reverse else 1
        if last:
            sort_dir = -sort_dir
            first = last

        # ensure we only ask for records where sort_col exists, or else we MIGHT end up with less than LIMIT records
        if not sort_dir in filter_dict:
            filter_dict[sort_col] = { "$exists": True}

        container = workspace if which == "runs" else "__jobs__"

        orig_col_dict =  col_dict
        if not col_dict:
            col_dict = {"log_records": 0}

        # put our mongo operations together in a retry-compatible function
        def fetch():
            cursor = mongo.mongo_db[container].find(filter_dict, col_dict)
            cursor = cursor.sort(sort_col, 1 if not last else -1)
            if first:
                cursor = cursor.limit(first)
            return cursor

        # here is where MONGO does all the hard work for us
        cursor = mongo.mongo_with_retries("get_mongo_records", fetch)
        records = list(cursor)

        console.diag("after full records retreival, len(records)={}".format(len(records)))

        if not orig_col_dict:
            # pull out standard cols, translating from actual to user-friendly names
            records = [self.translate_record(rec, actual_to_user) for rec in records if rec]

            # pull out requested cols, flattening nested values to their dotted names
            records = self.flatten_records(records, sort_col, args)

        if last:
            # we had to reverse the sort done by mongo, so correct it here
            records.reverse()
            #self.sort_records(records, sort_col, reverse)

        return records, using_default_last, last

    def get_user_columns(self, args):
        requested_list = args["columns"]
        add_cols = utils.safe_value(args, "add_columns")
        if add_cols:
            requested_list += add_cols

        return requested_list

    def get_actual_and_user_cols(self, records, args):
        col_dict = OrderedDict()
        for sr in records:
            if "metric_names" in sr:
                # seed col_dict with ordered list of metrics reported
                for name in sr["metric_names"]:
                    col_dict["metrics." + name] = 1

            # build from log records
            self.build_avail_list(col_dict, sr)

        avail_list = list(col_dict.keys())

        # get list of user-requested columns
        user_columns = self.get_user_columns(args)

        # parse out the custom column NAMES and FORMATS provided by the user
        user_col_args = self.build_user_col_args(user_columns)

        actual_cols, user_col_args = self.get_requested_cols(user_col_args, avail_list)
        return actual_cols, user_col_args

    def build_report(self, records, report_type, args):
        ''' build a tabular report of the records, or export to a table, as per args.  
        values in each record must have been flattened with a dotted key (e.g., hparams.lr).
        records must be in final sort order.
        '''
        row_count = 0
        was_exported = False

        avail_list, user_col_args  = self.get_actual_and_user_cols(records, args)

        # store for later use
        self.user_col_args = user_col_args

        fn_export = args["export"]
        if fn_export:
            fn_ext = os.path.splitext(fn_export)[1]
            sep_char = "," if fn_ext == ".csv" else "\t"

            col_list = user_col_args.keys()
            count = self.export_records(fn_export, records, col_list, sep_char)
            row_count = count - 1
            line = "report exported to: {} ({} rows)".format(fn_export, row_count)
            lines = [line]
            was_exported = True
        else:
            group_by = args["group"] if "group" in args else None
            number_groups = args["number_groups"] if "number_groups" in args else False
            actual_cols = list(user_col_args.keys())

            text, row_count = self.build_formatted_table(records, avail_cols=avail_list, col_list=actual_cols, 
                report_type=report_type, group_by=group_by, number_groups=number_groups)
            lines = text.split("\n")

        return lines, row_count, was_exported

    def export_records(self, fn_report, records, col_list, sep_char):

        lines = []

        # write column header
        header = ""
        for col in col_list:
            header += col + sep_char
        lines.append(header)

        # write value rows
        for record in records:
            line = ""

            for col in col_list:
                value = record[col] if col in record else ""
                if value is None:
                    value = ""
                line += str(value) + sep_char
    
            lines.append(line)

        with open(fn_report, "wt") as outfile:
            text = "\n".join(lines)
            outfile.write(text)

        return len(lines)

    def build_user_col_args(self, requested_list):

        user_col_args = {}

        for col_spec in requested_list:
            col_name = col_spec
            user_fmt = None

            if "." in col_name:
                prefix, col_name = col_name.split(".", 1)
            else:
                prefix = None

            if "=" in col_name:
                # CUSTOM NAME
                col_name, user_name = col_name.split("=")
                if ":" in user_name:
                    # CUSTOM FORMAT
                    user_name, user_fmt = user_name.split(":")
                    user_fmt = "{:" + user_fmt + "}"
            else:
                if ":" in col_name:
                    # CUSTOM FORMAT
                    col_name, user_fmt = col_name.split(":")
                    
                    user_fmt = "{:" + user_fmt + "}"
                user_name = col_name

            # rebuild prefix_name (must be prefix + col_name)
            prefix_name = prefix + "." + col_name if prefix else col_name

            user_col_args[prefix_name] = {"user_name": user_name, "user_fmt": user_fmt}

        return user_col_args

    def xt_custom_format(self, fmt, value):
        blank_zero_fmt = "{:$bz}"
        date_only = "{:$do}"
        time_only = "{:$to}"

        if fmt == blank_zero_fmt:
            # blank if zero
            value = "" if value == 0 else str(value)
        elif fmt == date_only:
            # extract date portion of datetime string
            value, _ = value.split(" ")
        elif fmt == time_only:
            # extract time portion of datetime string
            _, value = value.split(" ")
        
        return value

    def build_formatted_table(self, records, avail_cols, col_list=None, max_col_width=None, 
        report_type="run-reports", group_by=None, number_groups=False):
        '''
        builds a nicely formatted text table from a set of records.

        'records' - a list of dict entries containing data to format
        'avail_cols' - list of columns (unique dict keys found in records)
        'actual_cols' - list of columns to be used for report (strict subset of 'avail_cols')
        '''

        time_col_names = ["created", "started", "ended"]
        duration_col_names = ["duration", "queued"]

        #console.print("self.user_col_args=", self.user_col_args)

        if not max_col_width:
            max_col_width = int(self.config.get(report_type, "max-width"))    
            
        precision = self.config.get(report_type, "precision")
        uppercase_hdr_cols = self.config.get(report_type, "uppercase-hdr")
        right_align_num_cols = self.config.get(report_type, "right-align-numeric")
        truncate_with_ellipses = self.config.get(report_type, "truncate-with-ellipses")

        if not col_list:
            col_list = avail_cols

        col_space = 2               # spacing between columns
        col_infos = []              # {width: xxx, value_type: int/float/str, is_numeric: true/false}
        header_line = None

        # formatting strings with unspecified width and alignment
        int_fmt = "{:d}"
        str_fmt = "{:s}"
        #console.print("float_fmt=", float_fmt)

        # build COL_INFO for each col (will calcuate col WIDTH, formatting, etc.)
        for i, col in enumerate(col_list):

            # examine all records for determining max col_widths
            if self.user_col_args:
                user_args = self.user_col_args[col]
                user_col = user_args["user_name"]
                user_fmt = user_args["user_fmt"] 
            else:
                user_col = col
                user_fmt = None

            float_fmt = "{:." + str(precision) + "f}"

            col_width = len(user_col)
            #console.print("col=", col, ", col_width=", col_width)
            value_type = str
            is_numeric = False
            first_value = True

            for record in records:

                if not col in record:
                    # not all columns are defined in all records
                    continue

                value = record[col]

                # special formatting for time values
                if col in duration_col_names:
                    value = float(value)   # in case its a string
                    value = str(datetime.timedelta(seconds=value))
                    index = value.find(".")
                    if index > -1:
                        value = value[:index]
                elif col in time_col_names:
                    if isinstance(value, str):
                        value = arrow.get(value)
                    value = value.format('YYYY-MM-DD @HH:mm:ss')

                if user_fmt:
                    # user provided explict format for this column
                    if "$" in user_fmt:
                        value_str = self.xt_custom_format(user_fmt, value)
                    else:
                        value_str = user_fmt.format(value)
                elif isinstance(value, float):
                    value_str = float_fmt.format(value)
                    if value_type == str:
                        value_type = float
                        is_numeric = True
                elif isinstance(value, bool):
                    value_str = str(value)
                    value_type = bool
                    is_numeric = False
                elif isinstance(value, int):
                    value_str = int_fmt.format(value)
                    if value_type == str:
                        value_type = int
                        is_numeric = True
                elif value is not None:
                    # don't let None values influence the type of field
                    # assume value found is string-like
                    
                    # ensure value is a string
                    value = str(value)

                    value_str = str_fmt.format(value) if value else ""
                    if first_value:
                        is_numeric = utils.str_is_float(value)
                else:
                    value_str = ""

                # set width as max of all column values seen so far
                col_width = max(col_width, len(value_str))
                #console.print("name=", record["name"], ", col=", col, ", value_str=", value_str, ", col_width=", col_width)

            # finish this col
            if is_numeric and not precision:
                precision = 3

            col_width = min(max_col_width, col_width)
            col_info = {"name": col, "user_name": user_col, "col_width": col_width, "value_type": value_type, "is_numeric": is_numeric, "precision": precision, "user_fmt": user_fmt, "value_padding": None}
            col_infos.append(col_info)
            #console.print(col_info)

        if group_by:
            # GROUPED REPORT
            text = ""
            row_count = 0
            group_count = 0

            grouped_records = self.group_by(records, group_by)
            for i, (group, grecords) in enumerate(grouped_records.items()):

                if number_groups:
                    text += "\n{}. {}:\n".format(i+1, group)
                else:
                    text += "\n{}:\n".format(group)

                txt, rc = self.generate_report(col_infos, grecords, right_align_num_cols, uppercase_hdr_cols, truncate_with_ellipses, 
                    col_space, duration_col_names, time_col_names)

                # indent report
                txt = "  " + txt.replace("\n", "\n  ")
                text += txt
                row_count += rc
                group_count += 1

            text += "\ntotal groups: {}\n".format(group_count)
        else:
            # UNGROUPED REPORT
            text, row_count = self.generate_report(col_infos, records, right_align_num_cols, uppercase_hdr_cols, truncate_with_ellipses, 
                col_space, duration_col_names, time_col_names)

        return text, row_count

    def generate_report(self, col_infos, records, right_align_num_cols, uppercase_hdr_cols, truncate_with_ellipses, 
        col_space, duration_col_names, time_col_names):

        # process COLUMN HEADERS
        text = ""
        first_col = True

        for col_info in col_infos:
            if first_col:
                first_col = False
            else:
                text += " " * col_space

            user_fmt = col_info["user_fmt"] 
            right_align = right_align_num_cols and (col_info["is_numeric"] or user_fmt)
            col_width = col_info["col_width"]
            col_name = col_info["user_name"].upper() if uppercase_hdr_cols else col_info["user_name"]

            if truncate_with_ellipses and len(col_name) > col_width:
                col_text = col_name[0:col_width-3] + "..."
            elif right_align:
                fmt = ":>{}.{}s".format(col_width, col_width)
                fmt = "{" + fmt + "}"
                col_text = fmt.format(col_name)
            else:
                fmt = ":<{}.{}s".format(col_width, col_width)
                fmt = "{" + fmt + "}"
                col_text = fmt.format(col_name)

            text += col_text

        header_line = text
        text += "\n\n"
        row_count = 0

        # process VALUE ROWS
        for row_num, record in enumerate(records):
            first_col = True

            if row_num % 500 == 0:
                console.diag("build_formatted_table: processing row: {}".format(row_num))

            for col_info in col_infos:
                if first_col:
                    first_col = False
                else:
                    text += " " * col_space

                user_fmt = col_info["user_fmt"] 
                right_align = right_align_num_cols and (col_info["is_numeric"] or user_fmt or col_info["value_type"] == bool)
                col_width = col_info["col_width"]
                col = col_info["name"]
                align = ">" if right_align else "<"

                if not col in record:
                    # not all records define all columns
                    str_fmt = "{:" + align + str(col_width)  + "." + str(col_width) + "s}"
                    text += str_fmt.format("")
                else:
                    value = record[col]

                    #console.print("col=", col, ", value=", value, ", type(value)=", type(value))

                    # special formatting for time values
                    if col in duration_col_names:
                        value = float(value)   # in case its a string
                        value = str(datetime.timedelta(seconds=value))
                        index = value.find(".")
                        if index > -1:
                            value = value[:index]
                    elif col in time_col_names:
                        if isinstance(value, str):
                            value = arrow.get(value)
                        value = value.format('YYYY-MM-DD @HH:mm:ss')

                    if user_fmt:
                        # user provided explict format for this column
                        if "$" in user_fmt:
                            # custom XT formatting
                            value = self.xt_custom_format(user_fmt, value)
                        else:
                            value = user_fmt.format(value)   

                        # now treat as string that must fit into col_width
                        str_fmt = "{:" + align + str(col_width)  + "." + str(col_width) + "s}"
                        #value = value if value else ""
                        value = "" if value is None else value
                        text += str_fmt.format(value)
                    elif isinstance(value, float):
                        precision = col_info["precision"] if "precision" in col_info else float_precision
                        float_fmt = "{:" + align + str(col_width) + "." + str(precision) + "f}"
                        text += float_fmt.format(value)
                    elif isinstance(value, bool):
                        bool_fmt = "{!r:" + align + str(col_width) + "}"
                        text += bool_fmt.format(value)
                    elif isinstance(value, int):
                        int_fmt = "{:" + align + str(col_width) + "d}"
                        text += int_fmt.format(value)
                    else:
                        # ensure value is a string
                        value = str(value)
                        
                        str_fmt = "{:" + align + str(col_width)  + "." + str(col_width) + "s}"
                        #value = value if value else ""
                        value = "" if value is None else value
                        text += str_fmt.format(value)
            text += "\n"
            row_count += 1
        
        # all records processed
        if row_count > 5:
            # console.print header and run count
            text += "\n" + header_line + "\n"
    
        return text, row_count

    def group_by(self, records, group_col):
        groups = {}
        for rec in records:
            if not group_col in rec:
                continue

            group = rec[group_col]

            if not group in groups:
                groups[group] = []

            groups[group].append(rec)

        return groups