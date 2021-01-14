from __future__ import annotations

# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

import json
from typing import *

T = TypeVar('T')


class JsonSerializable:

    def __init_subclass__(cls, **kwargs):
        for n in cls.__annotations__:
            assert hasattr(cls, n), 'An attribute must have a default value for ' + n
        for n in cls.__dict__:
            assert hasattr(cls, n), 'The type of an attribute must be specified for ' + n

    def serialize(self):
        return json.dumps(self,
                          default=self._mapper,
                          indent=2).encode(encoding='utf-8')

    @classmethod
    def _marshall(cls,
                  source: any,
                  target: Type[T]) -> T:
        if isinstance(source, list):
            result = []
            for element in source:  # marshall each element
                result.append(
                    JsonSerializable._marshall(element, target.__args__[0] if hasattr(target, '__args__') else any))
        elif isinstance(source, dict):
            # noinspection PyBroadException
            result = target()  # create an instance of target type
            try:
                for n, t in target.__annotations__.items():  # marshall each item
                    if n in source.keys():
                        result.__setattr__(n, JsonSerializable._marshall(source.get(n), t))
            except:
                result = source
        else:
            result = source

        return result

    @classmethod
    def _mapper(cls, o):
        if isinstance(o, JsonSerializable):
            return o.__dict__
        elif isinstance(o, set):
            return list(o)


def deserialize(raw: Union[str, bytes, dict],
                target_type: Type[T]) -> T:
    return JsonSerializable._marshall(source=raw if isinstance(raw, dict) else json.loads(raw),
                                      target=target_type)
