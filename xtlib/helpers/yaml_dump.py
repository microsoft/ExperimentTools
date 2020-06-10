# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# yaml_dump.py: dump pretty yaml data to text (in style of XT config file)

def inline_yaml_dict_dump(dd):
    text = "{"
    first = True

    for key, value in dd.items():
        if first:
            first = False
        else:
            text += ", "

        if isinstance(value, str):
            value = '"' + value + '"'
        elif isinstance(value, list):
            value = inline_yaml_list_dump(value)
        elif value is None:
            value = "null"

        text += "{}: {}".format(key, value)

    text += "}"
    return text

def perline_yaml_dict_dump(dd):
    text = "{\n"

    for key, value in dd.items():
        if isinstance(value, str):
            value = '"' + value + '"'
        elif isinstance(value, list):
            value = inline_yaml_list_dump(value)
        elif value is None:
            value = "null"

        text += "        {}: {},\n".format(key, value)

    text += "    }"
    return text

def inline_yaml_list_dump(items):
    text = "["
    line = ""

    for value in items:
        if len(line) > 100:
            # start a new line
            text += line + ",\n        "
            line = ""

        if line:
            line += ", "

        if isinstance(value, str):
            value = '"' + value + '"'
        line += str(value)

    text += line+ "]"
    return text

def pretty_yaml_dump(dd, read_only_text=True):
    '''
    dump the data dict "dd" as XT config style yaml text
    '''
    if read_only_text:
        text = '''#-------------------------------------------------------------------------------------------------------------------
# DO NOT EDIT:
#   - a new version of this file is released with each XTLib version; it will overwrite this file without warning.
#   - to change a subset of these properties, use the "xt config" to create a LOCAL (current directory) config file.
#-------------------------------------------------------------------------------------------------------------------
# default_config.yaml: default configuration file for XT.  (READONLY)
#    The contents of this file contain the default settings that define how XT operates.  Many of the settings can be 
#    overridden by the various XT command  options (see "xt help commands" for more details). Detailed instructions 
#    for getting started with this config file are available in the "XT Config File" help topic.
#-------------------------------------------------------------------------------------------------------------------

'''
    else:
        text = ''

    for key, value in dd.items():
        text += "{}:\n".format(key)

        # if key == "providers":
        #     print("asdf")

        if isinstance(value, list):
            # if value:
            #     text += inline_yaml_list_dump(value)
            # else:
            #     text += "    []\n"
            text += "    " + str(value) + "\n"
        else:
            # write dict as key: value 
            for k, v in value.items():
                if isinstance(v, dict):
                    if key == "providers":
                        text += "\n"
                        v_str = perline_yaml_dict_dump(v)
                    else:
                        v_str = inline_yaml_dict_dump(v)
                elif isinstance(v, list):
                    v_str = inline_yaml_list_dump(v)
                elif isinstance(v, str):
                    v_str = '"' + v +   '"'
                elif v is None:
                    v_str = "null"
                else:
                    v_str = v

                text += "    {}: {}\n".format(k, v_str)
        
        text += "\n"

    return text


