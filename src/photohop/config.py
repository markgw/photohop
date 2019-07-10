import copy
import json
import os

from appdirs import user_config_dir

from photohop import __version__

CONFIG_DEFAULTS = {
    "file_manager_cmd": "nemo {image}",
    "history_path": os.path.join(os.getcwd(), "viewing_history.txt"),
}


class Config(object):
    def __init__(self, config_dict, path):
        self.path = path
        self.config_dict = copy.deepcopy(CONFIG_DEFAULTS)
        self.config_dict.update(config_dict)

    @staticmethod
    def load():
        config_dir = user_config_dir(appname="photohop", appauthor="markgw", version=__version__)
        config_path = os.path.join(config_dir, "photohop.json")
        return Config.load_from_path(config_path)

    @staticmethod
    def load_from_path(path):
        if os.path.exists(path):
            with open(path, "r") as f:
                config_dict = json.load(f)
        else:
            # Use defaults
            config_dict = {}
        return Config(config_dict, path)

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.config_dict, self.path)

    def __getitem__(self, item):
        if item in self.config_dict:
            return self.config_dict[item]
        else:
            raise KeyError("unknown config key '{}'".format(item))

    def __setitem__(self, key, value):
        if key in CONFIG_DEFAULTS:
            self.config_dict[key] = value
        else:
            raise KeyError("unknown config key '{}'".format(key))

    def __delitem__(self, key):
        # Revert to default
        if key in CONFIG_DEFAULTS:
            self.config_dict[key] = CONFIG_DEFAULTS[key]
        else:
            raise KeyError("unknown config key '{}'".format(key))
