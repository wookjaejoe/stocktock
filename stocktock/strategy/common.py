# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

import abc


class Strategy(abc.ABC):

    @abc.abstractmethod
    def check_and_buy(self, *args, **kwargs): ...

    @abc.abstractmethod
    def check_and_sell(self, *args, **kwargs): ...
