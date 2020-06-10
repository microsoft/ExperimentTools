#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# errors.py: functions related to error handling
import os
import sys
import logging
import traceback

from xtlib import utils
from .console import console

logger = logging.getLogger(__name__)

def exception_msg(ex):
    parts = str(ex).split("\n")
    return parts[0]

def user_exit(msg):
    raise Exception(msg)

def early_exit_without_error(msg=None):
    '''
    This is not an error; just information that request terminated early.
    '''
    if msg:
        console.print(msg)
    sys.exit(0)

def syntax_error_exit():
    # use "os._exit" to prevent exception from being thrown
    os._exit(1)

def report_exception(ex, operation=None):
    #console.print("Error: " + exception_msg(ex))
    raise ex

def process_exception(ex_type, ex_value, ex_traceback, exit_app=True):
    msg = str(ex_value)

    if issubclass(ex_type, XTUserException):
        # user-related exception: don't show stack trace
        console.print()
        console.print("Exception: " + msg)
       
        if issubclass(ex_type, SyntaxError):
            # show syntax/args for command
            from .qfe import current_dispatcher
            current_dispatcher.show_current_command_syntax()

        # for debugging print stack track
        #traceback.print_exc()
    else:
        # XT or other exception that requires stack trace
        # show stack trace and exit
        if exit_app:
            # this will show stack trace and exit
            raise ex_value
        else:
            # for use in REPL command: just show stack trace but do not exit
            traceback.print_exception(ex_type, ex_value, ex_traceback)

    if exit_app:
        # use "os._exit" to prevent a 2nd exception from being thrown
        os._exit(1)

# all XT exceptions subclass this
class XTBaseException(Exception): pass

# user-related XT exceptions subclass this
# for this, we do *not* show a stack trace
class XTUserException(XTBaseException): pass

class UserError(XTUserException): pass
class SyntaxError(XTUserException): pass
class ComboError(XTUserException): pass
class ConfigError(XTUserException): pass
class EnvError(XTUserException): pass
class CredentialsError(XTUserException): pass
class GeneralError(XTUserException): pass

class InternalError(XTBaseException): pass
class StoreError(XTBaseException): pass
class ServiceError(XTBaseException): pass
class APIError(XTBaseException): pass

class ControllerNotYetRunning(XTBaseException): pass

# following functions handle the different classes of errors

def internal_error(msg):
    raise InternalError(msg)

def syntax_error(msg):    
    raise SyntaxError(msg)

def creds_error(msg):    
    raise CredentialsError(msg)

def combo_error(msg):    
    raise ComboError(msg)

def env_error(msg):    
    raise EnvError(msg)

def config_error(msg):    
    raise ConfigError(msg)

def store_error(msg):    
    raise StoreError(msg)

def service_error(msg):    
    raise ServiceError(msg)

def general_error(msg):
    raise GeneralError(msg)

def api_error(msg):
    raise APIError(msg)

def controller_not_yet_running(msg):
    raise ControllerNotYetRunning(msg)

def argument_error(arg_type, token):
    if token.startswith("-"):
        token2 = "-" + token
    else:
        token2 = "--" + token
    #syntax_error("expected {}, but found '{}'.  Did you mean '{}'?".format(arg_type, token, token2))    
    syntax_error("unrecognized argument: {}?".format(token))
