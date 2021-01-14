import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'stocktock')))

from creon.events import EventBroker


def main():
    event_broker = EventBroker()
    event_broker.subscribe(lambda evts: print(evts))
    event_broker.start()


if __name__ == '__main__':
    main()
