from __future__ import annotations

# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

import logging
from dataclasses import dataclass

from slack_sdk import WebClient

logger = logging.getLogger('notification')
logger.setLevel(logging.INFO)

STR_TS = 'ts'


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
    def __init__(self, token, channels):
        self.token = token
        self.client = WebClient(token=token)
        self.channels = channels

    def send(self, *sendables: Sendable):
        """
        Send some sendables to all channels
        """
        for channel in self.channels:
            response = self._send_to(channel=channel, sendable=sendables[0])
            ts = response.data.get(STR_TS)
            if len(sendables) > 1:
                for sendable in sendables[1:]:
                    self._send_to(channel=channel,
                                  sendable=sendable,
                                  ts=ts)

    def _send_to(self, channel: str, sendable: Sendable, ts=None):
        if isinstance(sendable, Message):
            response = self.client.chat_postMessage(
                channel=channel,
                text=sendable.text,
                thread_ts=ts)
        elif isinstance(sendable, File):
            response = self.client.files_upload(
                channels=channel,
                initial_comment=sendable.comment,
                file=sendable.path,
                thread_ts=ts,
            )
        else:
            raise RuntimeError(f'Not supported sendable type: {type(sendable)}')

        assert response.status_code == 200, f'Failed to send a message to {channel}\n{response}'
        return response

class _Warren(SlackApp):
    DEFAULT_CHANNELS = ['#control-tower']

    def __init__(self, channels: list = None):
        if not channels:
            channels = self.DEFAULT_CHANNELS
        super().__init__(token='xoxb-1605364850897-1622524239648-QxvKygr0ynO4cZQXhUkGUN01',
                         channels=channels)


warren = _Warren()
