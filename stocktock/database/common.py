from __future__ import annotations

from typing import *

import sqlalchemy
from sqlalchemy import MetaData, Column, Table
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.orm import sessionmaker, mapper

T = TypeVar('T')


class AbstractDynamicTable(Generic[T]):

    def __init__(
            self,
            engine,
            entity_type: type,
            name: str,
            columns: List[Column]
    ):
        self.engine = engine
        self.inspector = Inspector.from_engine(self.engine)
        self.entity_type = entity_type
        self.name = name
        self.columns = columns

        self.proxy = None
        self.table = None
        self.session = None
        self.conn = None
        self.mapper = None

    def __enter__(self):
        return self.open()

    def open(self):
        meta = MetaData()
        self.proxy = type('TableProxy_' + self.name, (self.entity_type,), {})

        # Create table class
        self.table = Table(
            self.name,
            meta,
            *self.columns
        )

        # Create table if not exists
        if self.name not in self.inspector.get_table_names():
            meta.create_all(bind=self.engine, tables=[self.table])

        # Create session
        self.session = sessionmaker(bind=self.engine)()

        # Connect
        self.conn = self.engine.connect()

        # Map table with entity class
        self.mapper = mapper(self.proxy, self.table)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.conn.close()
        self.session.close()

    def query(self):
        """
        Return query of the session
        """
        return self.session.query(self.proxy)

    def all(self) -> List[T]:
        """
        Return all records
        """
        return self.query().all()

    def exists(self, **kwargs):
        """
        Return True if exists, otherwise False
        """
        return self.query().filter_by(**kwargs).count() > 0

    def insert(self, record: T):
        """
        Add and commit a record
        """
        # noinspection PyArgumentList
        self.session.add(self.proxy(**record.__dict__))
        self.session.commit()

    def insert_all(self, records: List[T]):
        """
        Add and commit multiple records
        """
        for record in records:
            # noinspection PyArgumentList
            self.session.add(self.proxy(**record.__dict__))

        self.session.commit()


# noinspection PyAbstractClass
class StringEnum(sqlalchemy.TypeDecorator):
    impl = sqlalchemy.String

    def __init__(self, enumtype, *args, **kwargs):
        super(StringEnum, self).__init__(*args, **kwargs)
        self._enumtype = enumtype

    def process_bind_param(self, value, dialect):
        return value.name

    def process_result_value(self, value, dialect):
        for item in self._enumtype:
            if item.name == value:
                return item

        raise RuntimeError(f'Not supported type: {value}')
