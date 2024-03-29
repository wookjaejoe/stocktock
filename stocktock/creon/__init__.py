# http://cybosplus.github.io/
import logging
import time

from .connection import connector


def keep_connection():
    while True:
        try:
            connector.connect()
            connector.wait_connection()
            time.sleep(120)
        except Exception as e:
            logging.error('Failed to keep connection with CreonPlus.', exc_info=e)


connector.connect()
connector.wait_connection()

# Thread(target=keep_connection).start()
