import win32serviceutil
import win32service
import servicemanager
import sys

from time import sleep

from DbMySql import *


class ZabAgent:
    def __init__(self):
        self._running = False
        self.db = DbMysql()

    def stop(self):
        self._running = False
        self.db.close()

    def start(self):
        self._running = True
        self.db.connect()

    def main(self):

        while self._running:
            sleep(3)
            ret = self.db.speed_check()
            print(f"Result of speed check {ret}")


class ZabAgentFrame(win32serviceutil.ServiceFramework):
    _svc_name_ = "ZabAgent"
    _svc_display_name_ = "VMS zabbix agent"
    _svc_description_ = "VMS - Zabbix agent sends metrics on VMS software to Zabbix"

    def __init__(self,args):
        win32serviceutil.ServiceFramework.__init__(self,args)

        self._impl = ZabAgent()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._impl.stop()
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STOPPED,
                              (self._svc_name_, ''))
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcDoRun(self):
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self._impl.start()
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        self._impl.main()


if __name__ == '__main__':
    if len(sys.argv) == 1:
        # servicemanager.Initialize()
        # servicemanager.PrepareToHostSingle(ZabAgentFrame)
        # servicemanager.StartServiceCtrlDispatcher()
        _impl = ZabAgent()
        _impl.start()
        _impl.main()
    else:
        win32serviceutil.HandleCommandLine(ZabAgentFrame)

