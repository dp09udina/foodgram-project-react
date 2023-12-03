from enum import Enum
from typing import Literal


class UserRoles(Enum):
    guest = "guest"
    user = "user"
    admin = "admin"

    @classmethod
    def choice(cls) -> tuple[tuple[Literal['guest', 'user', 'admin'], Literal['guest', 'user', 'admin']], ...]:
        return tuple((choices.name, choices.value) for choices in cls)
