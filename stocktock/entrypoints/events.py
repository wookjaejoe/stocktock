from creon.events import EventBroker


def main():
    event_broker = EventBroker()
    event_broker.subscribe(lambda evts: print(evts))
    event_broker.start()


if __name__ == '__main__':
    main()
