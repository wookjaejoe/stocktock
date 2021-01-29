import ctypes
import os
import time

from pywinauto import application

from . import com, stocks

# http://cybosplus.github.io/


CREON_PATH = 'C:\CREON\STARTER\coStarter.exe'
CREON_ID = 'WJJO'
PWD = 'dnrwo1!'
PWD_CERT = 'Whdnrwo1!!'


def start_client():
    app = application.Application()
    app.start(f'{CREON_PATH} /prj:cp /id:{CREON_ID} /pwd:{PWD} /pwdcert:{PWD_CERT} /autostart')


def kill_client():
    os.system('taskkill /IM coStarter* /F /T')
    os.system('taskkill /IM CpStart* /F /T')
    os.system('taskkill /IM DibServer* /F /T')
    os.system('wmic process where "name like \'%coStarter%\'" call terminate')
    os.system('wmic process where "name like \'%CpStart%\'" call terminate')
    os.system('wmic process where "name like \'%DibServer%\'" call terminate')


def disconnect():
    if com.cybos.IsConnect:
        com.cybos.PlusDisconnect()


def connect():
    if not com.cybos.IsConnect:
        disconnect()
        kill_client()
        start_client()

    for _ in range(300):
        if com.cybos.IsConnect:
            return
        else:
            time.sleep(1)

    raise RuntimeError('Auto-startup failure')


# todo: 실전 투자에서 활성화
if not com.cybos.IsConnect:
    connect()

assert com.cybos.IsConnect, 'Disconnected'
assert ctypes.windll.shell32.IsUserAnAdmin(), 'Not administrator'
