import copy
import json
import os

from pathlib import Path

from appdirs import user_config_dir

from photohop import __version__


CONFIG_DEFAULTS = {
    "file_manager_cmd": "dolphin --select {image}",
    "history_path": os.path.join(os.getcwd(), "viewing_history.txt"),
}
config_dir = Path(user_config_dir(appname="photohop", appauthor="markgw"))

if not config_dir.exists():
    config_dir.mkdir(parents=True, exist_ok=True)


class Config(object):
    def __init__(self, config_dict, path : Path):
        self.config_dir = config_dir
        self.path = path
        self.config_dict = copy.deepcopy(CONFIG_DEFAULTS)
        self.config_dict.update(config_dict)

    @staticmethod
    def load():
        config_path = config_dir / "photohop.json"
        return Config.load_from_path(config_path)

    @staticmethod
    def load_from_path(path : Path):
        if path.exists():
            with open(path, "r") as f:
                config_dict = json.load(f)
        else:
            # Use defaults
            config_dict = {}
        return Config(config_dict, path)

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.config_dict, f)

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
