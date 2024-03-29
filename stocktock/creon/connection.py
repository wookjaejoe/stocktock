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

from .exceptions import CreonError
from . import com
import time

CONFIG_PATH = os.path.join(Path.home(), '.creon.config')

assert ctypes.windll.shell32.IsUserAnAdmin(), 'Not administrator'
assert application  # Keep importing pywinauto


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


class CreonConnector:
    reconnecting = False

    @classmethod
    def _start_client(cls):
        # app = application.Application()
        os.system(f'{config.exe_path} /prj:cp /id:{config.id} /pwd:{config.pw} /pwdcert:{config.cert_pw} /autostart')
        # app.start(f'{config.exe_path} /prj:cp /id:{config.id} /pwd:{config.pw} /pwdcert:{config.cert_pw} /autostart')

    @classmethod
    def _kill_client(cls):
        os.system('taskkill /IM coStarter* /F /T')
        os.system('taskkill /IM CpStart* /F /T')
        os.system('taskkill /IM DibServer* /F /T')
        os.system('wmic process where "name like \'%coStarter%\'" call terminate')
        os.system('wmic process where "name like \'%CpStart%\'" call terminate')
        os.system('wmic process where "name like \'%DibServer%\'" call terminate')

    @classmethod
    def _disconnect(cls):
        if com.cybos().IsConnect:
            com.cybos().PlusDisconnect()

    @classmethod
    def connect(cls):
        if com.cybos().IsConnect:
            return

        if cls.reconnecting:
            logging.info('Already connecting to CreonPlus.')
            cls.wait_connection()
        else:
            try:
                cls.reconnecting = True
                logging.info('Disconnect with CreonPlus...')
                cls._disconnect()
                logging.info('Killing CreonPlus...')
                cls._kill_client()
                time.sleep(10)
                logging.info('Starting CreonPlus...')
                cls._start_client()
                cls.wait_connection()
                logging.info('CreonPlus Started Successfully')
            finally:
                cls.reconnecting = False

    @classmethod
    def wait_connection(cls, timeout=60):
        for _ in range(timeout):
            if com.cybos().IsConnect:
                return

            time.sleep(1)

        raise CreonError('Connection timeout')


connector = CreonConnector
