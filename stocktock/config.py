import json
import logging
import os
from dataclasses import dataclass

import jsons
from bson import json_util

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '.config.json')


@dataclass
class CreonConfig:
    exe: str
    id: str
    pw: str
    cert_pw: str


@dataclass
class DatabaseConfig:
    scheme: str
    user: str
    pw: str
    host: str
    port: str

    def get_url(self, dbname: str):
        return f'{self.scheme}{self.user}:{self.pw}@{self.host}:{self.port}/{dbname}'


@dataclass
class Configuration:
    creon: CreonConfig
    database: DatabaseConfig

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
