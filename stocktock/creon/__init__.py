import ctypes
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import jsons
from bson import json_util
from pywinauto import application
import logging

from . import com

CONFIG_PATH = os.path.join(Path.home(), '.creon.config')


@dataclass
class Configuration:
    exe_path: str
    id: str
    pw: str
    cert_pw: str

    def save(self):
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(jsons.dump(self, default=json_util.default), f, indent=2)

    @classmethod
    def load(cls):
        if not os.path.isfile(CONFIG_PATH):
            logging.warning(f'{CONFIG_PATH} not exists.')
            return

        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return jsons.loads(f.read(), Configuration)


config = Configuration.load()


def start_client():
    app = application.Application()
    app.start(f'{config.exe_path} /prj:cp /id:{config.id} /pwd:{config.pw} /pwdcert:{config.cert_pw} /autostart')


def kill_client():
    os.system('taskkill /IM coStarter* /F /T')
    os.system('taskkill /IM CpStart* /F /T')
    os.system('taskkill /IM DibServer* /F /T')
    os.system('wmic process where "name like \'%coStarter%\'" call terminate')
    os.system('wmic process where "name like \'%CpStart%\'" call terminate')
    os.system('wmic process where "name like \'%DibServer%\'" call terminate')


def disconnect():
    if com.cybos().IsConnect:
        com.cybos().PlusDisconnect()


def connect():
    if not com.cybos().IsConnect:
        disconnect()
        kill_client()
        start_client()

    for _ in range(300):
        if com.cybos().IsConnect:
            return
        else:
            time.sleep(1)

    raise RuntimeError('Auto-startup failure')


if not com.cybos().IsConnect:
    connect()

# todo: 실전투자에서 자동 로그인 활성화

assert com.cybos().IsConnect, 'Disconnected'
assert ctypes.windll.shell32.IsUserAnAdmin(), 'Not administrator'

from . import traders, events, com, stocks

# http://cybosplus.github.io/
