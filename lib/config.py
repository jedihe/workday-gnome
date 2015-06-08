import os
import json

class Config:
    def __init__(self, filePath = None):
        if (filePath != None and os.path.isfile(filePath)):
            self._filePath = filePath
            self.load()
        else:
            raise Exception("filePath is required")

    def load(self):
        # Check for file ~/.workday, load if exists, else raise exception
        if (os.path.isfile(self._filePath)):
            self._config = json.load(open(self._filePath, 'r'))
            return True
        else:
            raise Exception("Config file {} missing".format(self._filePath))

    def save(self):
        # Check integrity, raise exception on error
        json.dump(self._config, open(self._filePath, 'w'), sort_keys=True, indent=4)

    def get(self, key):
        # Check if setting exists, return value on success, raise exception on error
        if key in self._config:
            return self._config[key]
        else:
            raise Exception("No key with name {} in config".format(key))
        pass

    def set(self, key, value):
        # Do some check for integrity?
        self._config[key] = value
        pass

    def delete(self, key):
        if key in self._config:
            del self._config[key]
            return True
        else:
            raise Exception("Config key {} does not exist".format(key))

