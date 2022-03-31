from dataclasses import dataclass
from typing import Dict
from ujson import loads


class Serializer:
    def serialize(self) -> Dict:
        return self.__dict__

    @classmethod
    def deserialize(cls, str_data: str) -> object:
        params = loads(str_data.replace("'", '"'))
        return cls(**params)

    @classmethod
    def from_dict(cls, dict_data: dict) -> object:
        return cls(**dict_data)


@dataclass
class Role(Serializer):
    role_id: int
    role_name: str


@dataclass
class MachineType(Serializer):
    type_id: int
    type_name: str


@dataclass
class User(Serializer):
    user_id: int
    name: str
    surname: str
    role_id: int = None
    authorization_ids: list[int] = None
    card_UUID: str = None


@dataclass
class Maintenance(Serializer):
    maintenance_id: int
    description: str
    frequency: float


@dataclass
class Intervention(Serializer):
    timestamp: float
    intervention_id: int
    user_id: int


@dataclass
class Machine(Serializer):
    machine_id: int
    machine_name: str
    machine_type: int
    machine_hours: float = 0
    maintenances_needed: list[Maintenance] = None
    interventions: list[Intervention] = None


@dataclass
class Usage(Serializer):
    user_id: int
    machine_id: int
    started_timestamp: float
    ended_timestamp: float
    duration: float
