#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# xtConfig.py: reads and writes the config.yaml file, used to persist user settings for XT

import os
import yaml
import shutil
import logging
import tempfile
import importlib
import pkg_resources

from io import StringIO
from xtlib import utils
from xtlib import errors
from xtlib import constants
from xtlib import pc_utils
from xtlib import file_utils
from xtlib.console import console
from xtlib.helpers.dot_dict import DotDict
from xtlib.helpers.validator import Validator
from xtlib.helpers.yaml_dump import pretty_yaml_dump

logger = logging.getLogger(__name__)


class XTConfig():

    def __init__(self, fn=None, create_if_needed=False, config_dict=None):
        self.create_if_needed = create_if_needed
        if config_dict is not None:
            self.data = config_dict
        else:
            self.data = self.read_config(fn)
        self.explicit_options = {}
        self.vault = None
        self.mini_mode = False

    def name_exists(self, group, name):
        return group in self.data and name in self.data[group]

    def warning(self, *msg_args):
        msg = "WARNING: xt_config file -"
        for arg in msg_args:
            msg += " " + str(arg)
        if self.get("internal", "raise", suppress_warning=True):
            errors.config_error(msg)
        else:
            console.print(msg)

    def get_explicit_option(self, name):
        return self.explicit_options[name] if name in self.explicit_options else None

    def get_groups(self):
        return self.data

    def get_group_properties(self, group):
        return self.data[group]

    def set_explicit_option(self, name, value):
        self.explicit_options[name] = value

    # use "*" to require dict_key and default_value to be a named arguments
    def get(self, group, name=None, dict_key=None, default_value=None, suppress_warning=False, group_error=None, 
        prop_error=None, key_error=None):
        
        value = default_value

        if group in self.data:
            value = self.data[group]
            if name:
                if name in value:
                    value = value[name]
                    if dict_key:
                        if dict_key in value:
                            value = value[dict_key]
                        else:
                            if key_error:
                                errors.config_error(key_error)
                            if not suppress_warning:
                                self.warning("GET option dict_key not found: ", group, name, dict_key, default_value)
                            value = default_value
                else:
                    if prop_error:
                        errors.config_error(prop_error)
                    if not suppress_warning:
                        self.warning("GET option not found: ",  group, name, dict_key, default_value)
                    value = default_value
        else:
            if group_error:
                errors.config_error(group_error)
            if not suppress_warning:
                self.warning("GET option GROUP not found: ", group, name, dict_key, default_value)
            value = default_value

        # expand values containing a "$" id
        if isinstance(value, str) and "$" in value:
            value = self.expand_system_symbols(value, group, name)
        elif isinstance(value, dict):
            for key, val in value.items():
                if isinstance(val, str) and "$" in val:
                    val = self.expand_system_symbols(val, name, key)
                    value[key] = val

        return value

    # use "*" to require dict_key and value to be a named arguments
    def set(self, group, name, *, dict_key=None, value=None, suppress_warning=False):
        if group in self.data:
            gv = self.data[group]
            if name in gv:
                if dict_key:
                    obj = gv[name]
                    if not dict_key in obj:
                        if not suppress_warning:
                            self.warning("SET option dict_key not found: ", group, name, dict_key, value)
                    #console.print("set: obj=", obj, ", dict_key=", dict_key, ", value=", value)
                    obj[dict_key] = value
                    #console.print("set: post obj=", obj)
                else:
                    gv[name] = value
            else:
                if not suppress_warning:
                    self.warning("SET option name not found: ", group, name, dict_key, value)
                gv[name] = value
        else:
            raise Exception("SET option group not found: ", group, name, dict_key, value)
        
    def get_vault_key(self, name):
        self.create_vault_if_needed()
        return self.vault.get_secret(name)
        
    def create_vault_if_needed(self):
        if not self.vault:
            console.diag("before vault login")
            from xtlib import xt_vault 

            # create our vault manager
            vault_url = self.get_vault_url()
            team_name = self.get("general", "xt-team-name")

            azure_tenant_id = self.get("general", "azure-tenant-id")
            self.vault = xt_vault.XTVault(
                vault_url, team_name, azure_tenant_id=azure_tenant_id)

            authentication = self.get("general", "authentication")
            self.vault.init_creds(authentication)

            console.diag("after vault login")

    def expand_system_symbols(self, text, section=None, prop_name=None):
        if text == "$vault":
            if not self.vault:
                # create on-demand
                self.create_vault_if_needed()

            assert section and prop_name
            text = self.vault.get_secret(section)

        if "$username" in text:
            ev_user = "USERNAME" if pc_utils.is_windows() else "USER"
            username = os.getenv(ev_user, os.getenv("XT_USERNAME"))
            username = username if username else ""
            text = text.replace("$username", username)

        if "$current_conda_env" in text:
            conda = os.getenv("CONDA_DEFAULT_ENV")
            if conda:
                text = text.replace("$current_conda_env", conda)

        return text

    def read_config(self, fn=None):
        if fn is None:
            fn = get_default_config_path()
        self.fn = fn

        if not os.path.exists(fn):
            errors.internal_error("missing default_config file: " + fn)

        # read config file
        try:
            with open(fn, "rt") as file:
                config = yaml.safe_load(file)  # , Loader=yaml.FullLoader)
        except BaseException as ex:
            logger.exception("Error in read_config, ex={}".format(ex))
            raise Exception ("The config file '{}' is not valid YAML, error: {}".format(fn, ex))

        return config

    def get_box_def(self, box_name):
        box_def = self.get("boxes", box_name, suppress_warning=True)
        if not box_def:
            if box_name == pc_utils.get_hostname():
                # try "local"
                box_def = self.get("boxes", "local", suppress_warning=True)

        return box_def

    def get_setup_from_box(self, box_name):
        setup_def = None

        box_def = self.get_box_def(box_name)
        if box_def and "setup" in box_def:
            setup_name = box_def["setup"]
            setup_def = self.get("setups", setup_name, suppress_warning=True)

        return setup_def

    def get_setup_from_target_def(self, target_def):
        setup_def = None

        if target_def and "setup" in target_def:
            setup_name = target_def["setup"]
            setup_def = self.get("setups", setup_name, suppress_warning=True)

        return setup_def

    def get_targets(self):
        targets = self.get("compute-targets")
        targets = list(targets.keys())
        return targets

    def get_service(self, service_name):
        service = self.get("external-services", service_name, suppress_warning=True)
        if not service:
            errors.config_error("'{}' must be defined in the [external-services] section of XT config file".format(service_name))

        service["name"] = service_name
        #self.expand_symbols_in_creds(service, service_name)
        return service

    def get_compute_def(self, target_name): 
        target = self.get("compute-targets", target_name, suppress_warning=True)

        if not target:
            # is this target a box name?
            box_info = self.get("boxes", target_name, suppress_warning=True)
            if not box_info:
                errors.config_error("target '{}' must be defined in the [compute-targets] section of XT config file (or be box name)".format(target_name))
            # make box look like a target
            target = {"service": "pool", "boxes": [target_name]}

            # use setup from first box 
            if "setup" in box_info:
                target["setup"] = box_info["setup"]

        target["name"] = target_name
        #self.expand_symbols_in_creds(target, target_name)
        return target        

    def get_external_service_from_target(self, target_name):
        target = self.get_compute_def(target_name)
        
        if not "service" in target:
                errors.config_error("'service' property must be defined for target={} in the XT config file".format(target))
        service_name = target["service"]

        service = self.get_service(service_name)
        #self.expand_symbols_in_creds(service, service_name)
        return service

    # def expand_symbols_in_creds(self, creds, creds_name):
    #     for key, value in creds.items():
    #         if "$" in value:
    #             value = self.expand_system_symbols(value, creds_name, key)
    #             creds[key] = value

    def get_storage_creds(self):
        # validate STORAGE service
        storage_name = self.get("xt-services", "storage", suppress_warning=True)
        if not storage_name:
            errors.config_error("'storage' must be set in [xt-services] section of XT config file")

        # validate STORAGE_NAME credentials
        storage_creds = self.get("external-services", storage_name, suppress_warning=True)
        if not storage_creds:
            errors.config_error("'{}' must be specified in [external-services] section of XT config file".format(storage_name))

        #self.expand_symbols_in_creds(storage_creds, storage_name)
        storage_creds["name"] = storage_name
        return storage_creds

    def get_mongo_creds(self):
        # validate MONGO service
        mongo_name = self.get("xt-services", "mongo", suppress_warning=True)
        if not mongo_name:
            errors.config_error("'mongo' must be set in [xt-services] section of XT config file")

        # validate MONGO credentials
        mongo_creds = self.get("external-services", mongo_name, suppress_warning=True)
        if not mongo_creds:
            errors.config_error("'{}' must be specified in [external-services] section of XT config file".format(mongo_name))

        #self.expand_symbols_in_creds(mongo_creds, mongo_name)
        return mongo_creds, mongo_name

    def get_vault_url(self):
        # validate VAULT service
        vault_name = self.get("xt-services", "vault", suppress_warning=True)
        if not vault_name:
            errors.config_error("'vault' property must be set in [xt-services] section of XT config file")

        # validate VAULT credentials
        vault_creds = self.get("external-services", vault_name, suppress_warning=True)
        if not vault_creds:
            errors.config_error("'{}' must be specified in [external-services] section of XT config file".format(vault_name))

        if not "url" in vault_creds:
            errors.config_error("URL not specified for '{}' in [external-services] section of XT config file".format(vault_name))

        url = vault_creds["url"]
        return url

    def get_storage_type(self):
        return "azure-store"

    def get_service_type(self, service_name):
        if service_name == "pool":
            service_type = "pool"
        else:
            service = self.get("external-services", service_name, suppress_warning=True)
            if not service:
                errors.config_error("'{}' must be defined in the [external-services] section of XT config file".format(service_name))
                
            if not "type" in service:
                errors.config_error("'type' must be defined for the '{}' service in the XT config file".format(service_name))

            service_type = service["type"]

        return service_type

    def get_required_service_property(self, creds, prop_name, service_name):
        value = utils.safe_value(creds, prop_name)
        if not value:
            errors.config_error("Missing '{}' property for service '{}' defined in [external-services] section of the XT config file".format(prop_name, service_name))

        return value

    def get_docker_def(self, name): 
        environemnt_def = self.get("dockers", name, suppress_warning=True)
        return environemnt_def        

    def get_storage_provider_code_path(self, storage_creds):
        # get the provider_code_path
        provider_name = storage_creds["provider"]
        providers = self.get("providers", "storage")
        if not provider_name in providers:
            errors.config_error("{} provider='{}' not registered in XT config file".format("storage", provider_name))

        code_path = providers[provider_name]
        return code_path

    def get_provider_class_ctr(self, provider_type, name):
        '''
        return the class constructor method for the specified provider.
        '''
        providers = self.get("providers", provider_type)

        if not name in providers:
            errors.config_error("{} not registered in XT config file".format(name))

        code_path = providers[name]
        return utils.get_class_ctr(code_path)

    # def get_regularized_compute_def(self, compute, opt_names, explicit, args):
    #     compute_def = self.get_compute_def(compute)  
    #     if compute_def:
    #         for name in opt_names:
    #             under_name = name.replace("-", "_")

    #             if name in explicit:
    #                 sd[name] = args[under_name]
    #             elif name in sd:
    #                 args[under_name] = sd[name]

    #     return compute_def

# flat functions

def load_yaml(fn): 
    with open(fn, "rt") as file:
        data = yaml.safe_load(file) #, Loader=yaml.FullLoader)
    return data

def merge_configs(config, overrides):
    # note: a simple dict "update()" is too blunt; we need a fine-grained key/value update
    config_data = config.data

    # MERGE local config with default config
    for section_name, section_value in overrides.data.items():
        if not section_name in config_data:
            config_data[section_name] = {}

        # section_value could be a dict or an array
        if isinstance(section_value, list):
            # just replace list as a single value
            config_data[section_name] = section_value
        else:
            # process dict
            for key, value in section_value.items():
                if isinstance(value, dict):
                    # handle [section.subsection] 
                    if not key in config_data[section_name]:
                        config_data[section_name][key] = {}
                    for inner_key, inner_value in value.items():
                        #console.print("overridding: [{}.{}] {} = {}".format(section_name, key, inner_key, inner_value))
                        config_data[section_name][key][inner_key] = inner_value
                else:
                    # handle [section]
                    #console.print("overridding: [{}] {} = {}".format(section_name, key, value))
                    config_data[section_name][key] = value    

def get_merged_config(create_if_needed=True, local_overrides_path=None, suppress_warning=False, mini=False):

    fn_default = get_default_config_path()
    config = load_and_validate_config(fn_default, validate_as_default=True)

    # apply local override file, if present
    fn_overrides = local_overrides_path if local_overrides_path else constants.FN_CONFIG_FILE
    fn_overrides = os.path.realpath(fn_overrides)
    
    sc = os.getenv("XT_STORE_CREDS")
    mc = os.getenv("XT_MONGO_CONN_STR")
    if sc and mc:
        # we are running on compute node (launched by script)
        console.print("XT: detected run on compute node; setting mini_mode=False")
        config.mini_mode = False
    else:
        # get mini_mode value from default config (modified further below)
        config.mini_mode = not config.get("general", "advanced-mode")
        if config.mini_mode:
            suppress_warning = True

    if os.path.exists(fn_overrides):
        overrides = load_and_validate_config(fn_overrides, validate_as_default=False)

        if not overrides.data:
            console.warning("local xt_config.yaml file contains no properties")
        else:
            # allow overrides to override the mini_mode flag
            if not (sc and mc):
                config.mini_mode = not overrides.get("general", "advanced-mode", suppress_warning=True)

            # hardcoded MINI options (can be overwritten by local confile file)
            if config.mini_mode:
                # single workspace
                config.data["general"]["workspace"] = "txt"

                # single target
                config.data["xt-services"]["target"] = "batch"

            # merge the overrides config with the default config
            merge_configs(config, overrides)
           
    else:
        if not suppress_warning:
            console.print("warning: no local config file found")
    
    console.detail("after loading/validation of merged config files")
    
    return config

def get_installed_package_version(pkg_name):
    import pkg_resources
    version = pkg_resources.get_distribution(pkg_name).version
    return version

def get_resource_dir():
    version_str = get_installed_package_version("xtlib")
    res_dir = os.path.abspath(os.path.expanduser("~/.xt/resources/" + version_str))
    return res_dir

def is_default_config_present():
    default_config_file_path = os.path.join(get_resource_dir(), constants.FN_DEFAULT_CONFIG)

    return os.path.exists(default_config_file_path)

def overwrite_default_config():
    default_config_path = os.path.join(get_resource_dir(), constants.FN_DEFAULT_CONFIG)
    if is_default_config_present():
        file_utils.zap_file(default_config_path)

    res_dir = get_resource_dir()
    file_utils.ensure_dir_exists(res_dir)
    fn_source = os.path.join(file_utils.get_xtlib_dir(), "helpers", constants.FN_DEFAULT_CONFIG)
    shutil.copyfile(fn_source, default_config_path)

def get_default_config_path():
    '''
    always call this function to find the "default_config.yaml" file.
    calling this ensures that the file has been copied from its package location.
    '''
    res_dir = get_resource_dir()
    fn = os.path.join(res_dir, constants.FN_DEFAULT_CONFIG)

    if not os.path.exists(fn):
        # copy it from its helpers dir in the installed package (or dev directory)
        file_utils.ensure_dir_exists(res_dir)
        fn_source = os.path.join(file_utils.get_xtlib_dir(), "helpers", constants.FN_DEFAULT_CONFIG)
        shutil.copyfile(fn_source, fn)

        # make file readonly
        file_utils.make_readonly(fn)

    return fn

def get_default_config_template_path():
    return os.path.join(file_utils.get_xtlib_dir(), "helpers", constants.FN_DEFAULT_TEMPLATE)

def load_and_validate_config(fn, validate_as_default):

    # load the config file
    config = XTConfig(fn=fn, create_if_needed=False)

    # load the validation schema
    fn_schema = os.path.join(file_utils.get_xtlib_dir(), "helpers", "xt_config_schema.yaml")
    schema = load_yaml(fn_schema)

    # validate the config file
    validator = Validator()
    validator.validate(schema, fn_schema, config.data, config.fn, validate_as_default)

    return config

def merge_internal_xt_config(internal_config_text):
    '''
    merge the fn_internal_config into the default xt config file.
    '''
    res_dir = get_resource_dir()

    # write the internal config text as file in the resources directory and load/validate
    fn_internal_config = os.path.join(res_dir, constants.FN_INTERNAL_CONFIG)
    file_utils.zap_file(fn_internal_config)
    file_utils.write_text_file(fn_internal_config, internal_config_text)
    file_utils.make_readonly(fn_internal_config)

    internal_config = load_and_validate_config(fn_internal_config, validate_as_default=False)

    # first, see if the "orig" version of the default file is present
    fn_orig_default = os.path.abspath(os.path.join(res_dir, constants.FN_ORIG_DEFAULT))
    fn_default = fn_orig_default

    # if not found, fallback to the normal default version
    if not os.path.exists(fn_default):
        fn_default = get_default_config_path()

        # the default_config.yaml file is required    
        if not os.path.exists(fn_default):
            errors.internal_error("missing default config file: {}".format(fn_default))

        # preserve normal default as "orig" name
        shutil.copyfile(fn_default, fn_orig_default)
        file_utils.make_readonly(fn_orig_default)

    default_config = load_and_validate_config(fn_default, validate_as_default=True)

    # merge internal config into the default config
    merge_configs(default_config, internal_config)

    # remove old default file (fn_default)
    fn_default = get_default_config_path()
    file_utils.zap_file(fn_default)

    # save new merged version (fn_default)
    text = pretty_yaml_dump(default_config.data)
    file_utils.write_text_file(fn_default, text)

    # make file readonly
    file_utils.make_readonly(fn_default)

def get_merged_internal_xt_config_string(internal_config_text):
    '''
    Merge with the packaged default_config.yaml
    '''
    internal_config_dict = yaml.safe_load(internal_config_text)
    internal_config = XTConfig(config_dict=internal_config_dict)

    packaged_default_config_dict =\
        yaml.safe_load(
            pkg_resources.resource_string("xtlib.helpers", "default_config.yaml").decode())
    default_config = XTConfig(config_dict=packaged_default_config_dict)

    # merge internal config into the default config
    merge_configs(default_config, internal_config)


    # Return the text of the merged config
    text = pretty_yaml_dump(default_config.data)
    
    return text
