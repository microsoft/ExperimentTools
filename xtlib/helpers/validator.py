#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# validator.py: validates XT CONFIG yaml files (default and local)

import os
import time

from xtlib import file_utils
from xtlib import errors

class Validator():
    '''
    Our main entry point/method is **validate()**.  Its basic job is to verify 
    that an actual dictionary matches one of the available templates, and 
    to support recursion, so we can match values that are themselves dictionaries.

    Templates supported:
        1. {key: value, key: value, ..., $opt: {okey: value, okey: value, ...}}
        2. $repeat: {$str: value}
        3. $select: {$select_key: str, $select_records: {}}

    Basic algorithm:
        - we use "s_value" to refern to a schema value, and "c_value" to refer to a config value (a value of the thing being validated)

        1. for type 1 template:
            - ensure all c_keys are known (match an s_key or optional s_key)
            - ensure all c_values match the corresponding s_values
            - ensure all required s_keys are present in the c_value

        2. for type 2 template:
            - ensure all c_values match the s_value

        3. for type 3 template:
            - use the $select_key to extract a key value from c_value
            - use that key to select a new s_value from $select_records
            - validate c_value against new s_value (recursive call)

    - predefined keys: $record-types, $repeat, $opt, $select, $select-key, $select-records
    - predefined values: $str, $bool, $int, $num, $str-list, $rec
    '''

    def __init__(self):
        self.record_types = None
        self.mv_count = 0           # debugging
        self.config_fn = None
        self.schema_fn = None

    def schema_error(self, msg):
        full_msg = "Error in schema definition: {} (schema: {})".format(msg, self.schema_fn)
        errors.internal_error(full_msg)

    def config_error(self, msg):
        full_msg = "Error in XT config file: {} (config: {})".format(msg, self.config_fn)
        errors.syntax_error(full_msg)

    def join(self, path, name):
        return path + "." + name if path else name

    def value_mismatch(self, must_be, c_value, c_path):
        self.config_error("config file value must be a {}: {}.{}".format(must_be, c_path, c_value))

    def match_values(self, key, s_value, c_value, as_default, level, s_path, c_path):
        ''' this is the core method that triggers recursion '''
        sk_path = self.join(s_path, key)
        ck_path = self.join(c_path, key)

        self.mv_count += 1

        #print("match_values (#{}): key={}, s_value={:.30s}, c_value={:.30s}".format(self.mv_count, key, str(s_value), str(c_value)))

        if isinstance(s_value, dict):
            # recursion call
            self.match_dict(s_value, c_value, as_default, level+1, sk_path, ck_path)
        elif isinstance(s_value, list):
            # list of literal string values
            if not c_value in s_value:
                self.config_error("expected config value={} to be one of these keywords: {}".format(c_value, s_value))
        elif not isinstance(s_value, str):
            self.schema_error("schema value must be a dict or a str: {}".format(s_value))
        else:
            # s_value is a string
            if s_value == c_value:
                pass
            elif s_value == "$str":
                # allow strings to be specified as null (which translate to python None)
                if not isinstance(c_value, str) and c_value is not  None:
                    self.value_mismatch("string", c_value, ck_path)
            elif s_value == "$bool":
                if not isinstance(c_value, bool):
                    if not c_value in ["true", "false"]:
                        self.value_mismatch("bool", c_value, ck_path)
            elif s_value == "$int":
                if not isinstance(c_value, int) and c_value is not  None:
                    self.value_mismatch("int", c_value, ck_path)
                if c_value == -1:
                    cvaule = None
            elif s_value == "$num":
                if not isinstance(c_value, (int, float)) and c_value is not  None:
                    self.value_mismatch("num", c_value, ck_path)
                if c_value == -1:
                    cvaule = None
            elif s_value == "$str-list":
                if not isinstance(c_value, (list, tuple)):
                    self.value_mismatch("str-list", c_value, ck_path)

            elif s_value.startswith("$rec"):

                if s_value == "$rec":
                    # untyped dictionary
                    pass
                else:
                    #-- $rec_xxx --
                    s_key = s_value[1:]   # drop the "$"
                    if not s_key in self.record_types:
                        self.schema_error("schema is missing definition of record type: {}".format(s_key))
                    rec_def = self.record_types[s_key]
                    self.match_dict(rec_def, c_value, as_default, level+1, sk_path, ck_path)

            elif s_value.startswith("$"):
                self.schema_error("schema contains unexpected s_value={}".format(s_value))
            else:
                self.config_error("literal values don't match: schema={}, actual={}".format(s_value, c_value))

    def match_repeat_template(self, s_rec, c_rec, as_default, level, sk_path, ck_path):
        s_keys = list(s_rec.keys())
        c_keys = list(c_rec.keys())

        if len(s_keys) > 1:
            self.schema_error("$repeat must be the only key in the dictionary: {}".format(s_rec))

        t_keys = list(s_rec.keys())
        if len(t_keys) != 1:
            self.schema_error("$repeat value can only be a single key dictionary: {}".format(s_rec))

        t_key = t_keys[0]
        if t_key != "$str":
            self.schema_error("$repeat dictionary key only supports $str, but found: {}".format(tkey))

        value_templ = s_rec[t_key]

        for c_key, c_value in c_rec.items():
            self.match_values(c_key, value_templ, c_value, as_default, level, sk_path, ck_path)
    
    def match_select_template(self, s_rec, c_rec, as_default, level, sk_path, ck_path):
        s_keys = list(s_rec.keys())
        c_keys = list(c_rec.keys())

        if not "$select-key" in s_keys or not "$select-records" in s_keys or len(s_keys) != 2:
            self.schema_error("$select dictionary define exactly 2 keys ($select-key, $select-records): {}".format(s_rec))

        select_key = s_rec["$select-key"]
        select_records = s_rec["$select-records"]

        if not isinstance(c_rec, dict):
            self.value_mismatch("dict", c_rec, ck_path)

        key = c_rec[select_key]
        s_value = select_records[key]

        #self.match_dict(s_value, c_rec, as_default, level+1, sk_path, ck_path)
        # use match_values to expand s_value, as needed
        self.match_values("", s_value, c_rec, as_default, level, sk_path, ck_path)

    def match_dict_template(self, s_rec, c_rec, as_default, level, s_path, c_path):
        # extract optional fields, if present

        # make a copy of s_rec since we modify it locally
        s_rec = dict(s_rec)

        if "$opt" in s_rec:
            s_opt = s_rec["$opt"] 
            del s_rec["$opt"]
        else:
            s_opt = []

        # 1: ensure all config keys are known to schema
        for name in c_rec:
            if not name in s_rec and not name in s_opt:
                self.config_error("property name '{}.{}' not found in schema".format(c_path, name))

        # 2: ensure required s_keys are present in config
        # we do this check if we are validating the default config file or if
        # we are validating a level 2 dict (or higher)
        if as_default or level > 1:
            for name in s_rec:
                if not name in c_rec:
                    self.config_error("missing required property name '{}.{}'".format(s_path, name))
        
        # 3. validate each c_value against its associated s_value
        for key, c_value in c_rec.items():
            s_value = s_rec[key] if key in s_rec else s_opt[key]

            self.match_values(key, s_value, c_value, as_default, level, s_path, c_path)

    def match_dict(self, s_rec, c_rec, as_default, level, s_path, c_path):
        ''' this is the reentry method for recursion '''
        repeat_templ = s_rec["$repeat"] if "$repeat" in s_rec else None
        select_templ = s_rec["$select"] if "$select" in s_rec else None

        # if level== 1:
        #     print("validating section: {}".format(c_rec))

        if repeat_templ:
            self.match_repeat_template(repeat_templ, c_rec, as_default, level, s_path, c_path)
        elif select_templ:
            self.match_select_template(select_templ, c_rec, as_default, level, s_path, c_path)
        else:
            self.match_dict_template(s_rec, c_rec, as_default, level, s_path, c_path)

    def validate(self, schema, schema_fn, config, config_fn, as_default, msg=None):
        #print("validating: {}".format(msg))

        self.schema_fn = schema_fn
        self.config_fn = config_fn

        if "$record-types" in schema:
            self.record_types = schema["$record-types"] 

            # make a copy for local modification
            schema = dict(schema)
            del schema["$record-types"]

        self.match_dict(schema, config, as_default, 0, "", "")