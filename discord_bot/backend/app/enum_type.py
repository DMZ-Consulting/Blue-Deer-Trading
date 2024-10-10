from sqlalchemy.types import TypeDecorator, String
from sqlalchemy.orm import declarative_base
from enum import Enum
from sqlalchemy import types

Base = declarative_base()

class EnumType(TypeDecorator):
    impl = types.String

    def __init__(self, enum_class):
        super().__init__()
        self.enum_class = enum_class

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return value.value if isinstance(value, self.enum_class) else value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return self.enum_class(value)