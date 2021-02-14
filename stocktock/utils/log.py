# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

import logging
import logging.handlers
import os
import sys
from datetime import datetime

__debug = False

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_FOLDER = os.path.abspath('logs')
os.makedirs(LOG_FOLDER, exist_ok=True)

LOG_FORMAT_DETAILS = '%(name)s, %(asctime)s, %(levelname)-8s, %(message)s'


class ConsoleLogFormatter(logging.Formatter):
    def __init__(self):
        # noinspection SpellCheckingInspection
        logging.Formatter.__init__(self,
                                   fmt=LOG_FORMAT_DETAILS, datefmt=DATE_FORMAT)


class FileLogFormatter(logging.Formatter):
    def __init__(self):
        # noinspection SpellCheckingInspection
        logging.Formatter.__init__(self,
                                   fmt=LOG_FORMAT_DETAILS, datefmt=DATE_FORMAT)


def _create_stream_handler(level=logging.INFO):
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(ConsoleLogFormatter())
    return stream_handler


def _create_file_handler(level=logging.DEBUG):
    date = datetime.now().strftime('%Y%m%d')
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(LOG_FOLDER, f'stocktock-{date}.log'),
        encoding='utf-8',
        maxBytes=4 * 1024 * 1024,
        backupCount=2)
    file_handler.setLevel(level)
    file_handler.setFormatter(FileLogFormatter())
    return file_handler


def init(level=logging.INFO):
    logging.basicConfig(datefmt=DATE_FORMAT,
                        level=level)
    root_logger = logging.getLogger()
    root_logger.handlers = [_create_stream_handler(level=level),
                            _create_file_handler(level=level)]
