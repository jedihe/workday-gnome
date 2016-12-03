import time
import os

class WorkdaySession:
    SESSION_NOT_STARTED = 1000
    SESSION_STARTED = 1001
    SESSION_PAUSED = 1002
    SESSION_ENDED = 1003

    def __init__(self, workdayConfig, name = None):
        self._name = name
        self._duration = 0
        self._started = False
        self._cfg = workdayConfig
        self._status = self.SESSION_NOT_STARTED

    def start(self):
        if self._name == None or self._name == '':
            self._name = time.strftime('%Y-%m-%d-%H-%M-%S')
        self._dirPath = os.path.expanduser("~") + "/Videos/workday/" + self._name
        self._status = self.SESSION_STARTED
        if not os.path.exists(self._dirPath):
            os.makedirs(self._dirPath)
        # Init recording?
        self.save()
        pass

    def stop(self):
        self._status = self.SESSION_PAUSED
        self.save()
        pass

    def resume(self):
        self._status = self.SESSION_STARTED
        pass

    def close(self):
        self._cfg.delSession(self._name)
        self._cfg.save()

    def getStatus(self):
        return self._status

    def getName(self):
        return self._name

    def setName(self, newName):
        if self._status == self.SESSION_NOT_STARTED:
            self._name = newName
            self._dirPath = os.path.expanduser("~") + "/Videos/workday/" + self._name
            return True
        else:
            return False

    def getDuration(self):
        return self._duration

    def setDuration(self, duration):
        self._duration = duration

    def increaseDuration(self, delta):
        self._duration += delta

    def getDirPath(self):
        return self._dirPath

    def getDirPathShellQuoted(self):
        return "'" + self._dirPath.replace("'", "'\\''") + "'"

    def _dumpSession(self):
        return {
            'duration': self._duration,
            'dirPath': self._dirPath,
            'started': self._started,
            'status': self._status
            }

    def save(self):
        self._cfg.setSession(self._name, self._dumpSession())
        self._cfg.save()

    def loadFromConfig(self, name):
        loadedSession = self._cfg.getSession(name)
        if loadedSession != False:
            self._name = name
            self._duration = loadedSession['duration']
            self._dirPath = loadedSession['dirPath']
            self._started = loadedSession['started']
            return True
        else:
            return False
