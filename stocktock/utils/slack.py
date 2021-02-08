from __future__ import annotations

# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

import logging
import socket
import threading
from dataclasses import dataclass

from slack_sdk import WebClient

logger = logging.getLogger('notification')
logger.setLevel(logging.INFO)

STR_TS = 'ts'
enable = True


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

    def consume_message(self):
        while True:
            if self.queue:
                sendable = self.queue.pop()

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
        hostname = socket.gethostname()
        host = socket.gethostbyname(hostname)

        initial_msg = '\n'.join([
            f'SESSION CONNECTED - {hostname}({host})',
            title
        ])

        self.ts = super(WarrenSession, self).send(Message(initial_msg))

    def send(self, sendable: Sendable, ts=None):
        super(WarrenSession, self).send(sendable, self.ts)
