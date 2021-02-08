import logging

from utils import log
from database import dailycharts

log.init(logging.DEBUG)
logger = logging.getLogger('test')


def main():
    dailycharts.update()


if __name__ == '__main__':
    main()
