from config import Config
import os

class WorkdayConfig(Config):
    def __init__(self):
        self.cfgFilePath = os.path.expanduser("~") + "/.workday"
        if (not os.path.exists(self.cfgFilePath)):
            # config file does not exist, create it
            f = open(self.cfgFilePath, 'w')
            f.write('{}')
            f.close()
        #super(Config, self).__init__(self.cfgFilePath)
        Config.__init__(self, self.cfgFilePath)

    def getSessions(self):
        if 'sessions' in self._config:
            return self._config['sessions']
        else:
            self._config['sessions'] = {}
            return {}

    def getSession(self, key):
        if key in self._config['sessions']:
            return self._config['sessions'][key]
        else:
            return False

    def setSession(self, key, data):
        if 'sessions' not in self._config:
            self._config['sessions'] = {}
        self._config['sessions'][key] = data

    def delSession(self, key):
        if key in self._config['sessions']:
            del self._config['sessions'][key]

