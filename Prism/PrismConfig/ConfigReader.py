import os
import json

class ConfigReader:
    def __init__(self):
        self.base_dir = os.path.abspath(os.path.dirname(__file__))
        self.base_paths = os.path.join(self.base_dir, "ConfigPaths.json")

    def replace_keywords(self, str_with_kw):
        clean_str = str_with_kw
        clean_str = clean_str.replace("{config}", self.base_dir)

        # TODO: While str contains {keyword} replace with value from config
        # TODO: use regex

        # Return Cross OS path
        return clean_str.replace('/', os.sep)

    def get_sub_config_path(self, sub_config):
        data_file = open(self.base_paths, 'r')
        data = json.load(data_file)
        data_file.close()
        return self.replace_keywords(data[sub_config]).encode("utf-8")

    def get_data(self, sub_config, key=None):
        config_path = self.get_sub_config_path(sub_config)
        data_file = open(config_path, 'r')
        data = json.load(data_file)
        data_file.close()

        if key:
            return data[key]

        return data