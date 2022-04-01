"""This module contains all the entities used in the database."""

from dataclasses import dataclass
from typing import Dict


class Serializer:
    """Interface to serialized and deserialize data."""

    def serialize(self) -> Dict:
        """Serialize data and return a Dict.

        Returns:
            Dict
        """
        return self.__dict__

    @classmethod
    def from_dict(cls, dict_data: dict) -> object:
        """Deserialize data from Dictionary.

        Args:
            dict_data (dict): dictionary data

        Returns:
            object: appropriate object type
        """
        return cls(**dict_data)


@dataclass
class Role(Serializer):
    """Dataclass handling a role."""

    role_id: int
    role_name: str
    authorize_all: bool = False


@dataclass
class MachineType(Serializer):
    """Dataclass handling a machine type."""

    type_id: int
    type_name: str


@dataclass
class User(Serializer):
    """Dataclass handling a user."""

    user_id: int
    name: str
    surname: str
    role_id: int = None
    authorization_ids: list[int] = None
    card_UUID: str = None


@dataclass
class Maintenance(Serializer):
    """Dataclass handling a maintenance."""

    maintenance_id: int
    hours_between: float
    description: str = None


@dataclass
class Intervention(Serializer):
    """Dataclass handling an intervention."""

    intervention_id: int
    maintenance_id: int
    machine_id: int
    user_id: int
    timestamp: float


@dataclass
class Machine(Serializer):
    """Dataclass handling a machine."""

    machine_id: int
    machine_name: str
    machine_type: int
    machine_hours: float = 0
    maintenances: list[Maintenance] = None
    interventions: list[Intervention] = None


@dataclass
class Use(Serializer):
    """Dataclass handling machine use."""

    use_id: int
    user_id: int
    machine_id: int
    start_timestamp: float
    end_timestamp: float = None
