import abc
from typing import *

T = TypeVar('T')


class Table(Generic[T], metaclass=abc.ABCMeta):

    def __init__(self):
        self.rows: List[T] = []
        self.fields = []

    @abc.abstractmethod
    def create(self) -> T: ...

    @abc.abstractmethod
    def find(self) -> T: ...

    @abc.abstractmethod
    def find_all(self) -> List[T]: ...

    @abc.abstractmethod
    def update(self) -> T: ...

    @abc.abstractmethod
    def delete(self) -> T: ...
