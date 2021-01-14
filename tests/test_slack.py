import unittest

import slack


class MyTestCase(unittest.TestCase):
    def test_something(self):
        warren = slack._Warren()
        warren.send(slack.Message('hello'))


if __name__ == '__main__':
    unittest.main()
