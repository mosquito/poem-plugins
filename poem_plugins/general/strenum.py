from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self._value_
