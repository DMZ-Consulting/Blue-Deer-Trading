from sqlalchemy.types import TypeDecorator, String
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum

Base = declarative_base()

class EnumType(TypeDecorator):
    impl = String
    cache_ok = True  # Set this flag to True

    def __init__(self, enum_class, *args, **kwargs):
        self.enum_class = enum_class
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return value.value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return self.enum_class(value)