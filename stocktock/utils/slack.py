from __future__ import annotations

# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

import logging
import socket
import threading
import time
from dataclasses import dataclass
from typing import *

from slack_sdk import WebClient

logger = logging.getLogger('notification')
logger.setLevel(logging.INFO)

STR_TS = 'ts'
enable = True

logging.getLogger('slack_sdk.web.base_client').setLevel(logging.ERROR)
logging.getLogger('slack_sdk.web.slack_response').setLevel(logging.ERROR)


class Sendable:
    pass


@dataclass
class Message(Sendable):
    text: str


@dataclass
class File(Sendable):
    comment: str
    path: str


class SlackApp:
    def __init__(self, token, channel):
        self.token = token
        self.client = WebClient(token=token)
        self.channel = channel
        self.queue = []

    def send(self, sendable: Sendable, ts=None):
        if isinstance(sendable, Message):
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=sendable.text,
                thread_ts=ts)
        elif isinstance(sendable, File):
            response = self.client.files_upload(
                channels=self.channel,
                initial_comment=sendable.comment,
                file=sendable.path,
                thread_ts=ts,
            )
        else:
            raise RuntimeError(f'Not supported sendable type: {type(sendable)}')

        assert response.status_code == 200, f'Failed to send a message to {self.channel}\n{response}'
        return response.data.get('ts')


class Warren(SlackApp):

    def __init__(self):
        super().__init__(token='xoxb-1605364850897-1622524239648-QxvKygr0ynO4cZQXhUkGUN01',
                         channel='#control-tower')


class WarrenSession(Warren):

    def __init__(self, title):
        super().__init__()
        self.queue: List[Sendable] = []
        hostname = socket.gethostname()
        host = socket.gethostbyname(hostname)

        initial_msg = '\n'.join([
            f'`SESSION CONNECTED - {hostname}({host})`',
            f':brain: *{title}*'
        ])

        self.ts = super(WarrenSession, self).send(Message(initial_msg))
        threading.Thread(target=self.start_consuming, daemon=True).start()

    def start_consuming(self):
        sup = super(WarrenSession, self)
        while True:
            while self.queue:
                sup.send(self.queue.pop(0), self.ts)

            time.sleep(1)

    def send(self, sendable: Sendable, ts=None):
        self.queue.append(sendable)
