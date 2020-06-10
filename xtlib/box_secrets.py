#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# box_secrets.py: keeps a list of box secrets for this user's pool machines
import os
import json

from xtlib import console
from xtlib import pc_utils
from xtlib import file_utils

FN_SECRETS = os.path.expanduser("~/.xt/info/box_secrets.json")

def correct_name(name):
    if name in ["local", "localhost"]:
        name = pc_utils.get_hostname()

    return name

def set_secret(name, value):
    name = correct_name(name)
    console.diag("set_secret: name={}, value={}".format(name, value))

    file_utils.ensure_dir_exists(file=FN_SECRETS)

    secrets = {}

    # read existing secrets, if any
    if os.path.exists(FN_SECRETS):
        text = file_utils.read_text_file(FN_SECRETS)
        secrets = json.loads(text)

    secrets[name] = value

    # write updates secrets
    text = json.dumps(secrets)
    file_utils.write_text_file(FN_SECRETS, text)

def get_secret(name):
    name = correct_name(name)
    secrets = {}

    if os.path.exists(FN_SECRETS):
        text = file_utils.read_text_file(FN_SECRETS)
        secrets = json.loads(text)

    value = secrets[name] if name in secrets else None
    console.diag("get_secret: name={}, value={}".format(name, value))
    return value



