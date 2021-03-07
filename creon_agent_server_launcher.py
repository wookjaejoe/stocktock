import sys
import os
import time

basedir = os.path.abspath(os.path.dirname(__file__))


def execute(*args):
    cmd = ' '.join([('\"' + arg + '\"' if ' ' in arg else arg) for arg in args])
    print(cmd)
    os.system(cmd)


def main():
    while True:
        execute(sys.executable, os.path.join(basedir, 'creon_agent_server.py'))
        time.sleep(1)


if __name__ == '__main__':
    main()
