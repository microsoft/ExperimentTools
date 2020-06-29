import os
import base64

from xtlib.helpers import xt_config


def place_merged_config():
    resources_folder = xt_config.get_resource_dir()
    config_string = base64.b64decode(os.environ.get("ENCODED_BASE_CONFIG")).decode("utf-8")
    os.makedirs(resources_folder)
    default_config_file = open(f"{resources_folder}/default_config.yaml", "w")
    default_config_file.write(config_string)
    default_config_file.close()


if __name__ == "__main__":
    place_merged_config()
