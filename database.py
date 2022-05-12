"""This is the class handling the Database. More to come."""

from entities import User, Role, MachineType, Machine, Maintenance, Intervention, Use
from exceptions import (
    DuplicatedIdException,
    InvalidIdException,
    InvalidQueryException,
)

from time import time
from pymongo import MongoClient, DESCENDING
from pymongo.errors import DuplicateKeyError

import toml


class DatabaseBackend:
    """Class handling the connection from and to the database."""

    def __init__(self, settings_path="settings.toml") -> None:
        """Create instance of Database.

        Args:
            settings_path (str, optional): TOML file settings. Defaults to "settings.toml".
        """
        self._settings_path = settings_path

        self._client = None
        self._db = None

        # dict of collections and its relative unique index
        self._collections = {
            "roles": "role_id",
            "machine_types": "type_id",
            "users": "user_id",
            "machines": "machine_id",
            "maintenances": "maintenance_id",
            "interventions": "intervention_id",
            "uses": "use_id",
        }

        self._loadSettings()
        self._connect()
        self._initCollections()

    def _loadSettings(self) -> None:
        """Load settings from TOML file."""
        self._settings = toml.load(self._settings_path)
        self._url = self._settings["database"]["url"]
        self._name = self._settings["database"]["name"]

    def _connect(self) -> None:
        """Connect to MongoDB server."""
        self._client = MongoClient(self._url)
        self._db = self._client[self._name]

    def _initCollections(self) -> None:
        """Initialize the collections in the database."""
        collections = self._db.list_collection_names()

        for c, i in self._collections.items():
            if c not in collections:
                self._db[c].create_index(i, unique=True)

    def _queryCollection(self, collection_name: str) -> list[dict]:
        """Query a collection and return the dict without the MongoDB mandatory _id.

        Args:
            collection_name (str): name of the collection

        Returns:
            list[dict]: list of dicts as returned from MongoDB
        """
        collection = self._db[collection_name]
        return list(collection.find(projection={"_id": 0}))

    def _getUserIdFromCard(self, card_UUID: str = None) -> int:
        collection = self._db["users"]
        result = collection.find_one({"card_UUID": card_UUID})
        return result["user_id"]

    def _validateRole(self, role_id: int) -> bool:
        collection = self._db["roles"]
        return collection.count_documents({"role_id": role_id}) == 1

    def _validateMachineType(self, type_id: int) -> bool:
        collection = self._db["machine_types"]
        return collection.count_documents({"type_id": type_id}) == 1

    def _validateUser(self, user_id: int) -> bool:
        collection = self._db["users"]
        return collection.count_documents({"user_id": user_id}) == 1

    def _validateMachine(self, machine_id: int) -> bool:
        collection = self._db["machines"]
        return collection.count_documents({"machine_id": machine_id}) == 1

    def _validateMaintenance(self, maintenance_id: int) -> bool:
        collection = self._db["maintenances"]
        return collection.count_documents({"maintenance_id": maintenance_id}) == 1

    def _isUserCurrentlyUsing(self, machine_id: int, user_id: int) -> bool:
        collection = self._db["uses"]
        return (
            collection.count_documents(
                {"user_id": user_id, "machine_id": machine_id, "end_timestamp": None}
            )
            > 0
        )


class DatabaseHelper(DatabaseBackend):
    def __init__(self, settings_path="settings.toml") -> None:
        super().__init__(settings_path)

    def getUserUses(self, user_id: int = None, card_UUID: str = None) -> list[Use]:
        """Return uses from a certain user.

        Args:
            user_id (int, optional): id of a User. Not necessary if card_UUID is passed
            card_UUID (str, optional): card_UUID of a User. Not necessary if user_id is passed

        Returns:
            list[Use]
        """
        if not user_id:
            user_id = self._getUserIdFromCard(card_UUID=card_UUID)

        if not self._validateUser(user_id=user_id):
            raise InvalidIdException("User", user_id)

        collection = self._db["uses"]
        results = collection.find({"user_id": user_id}, projection={"_id": 0})

        return [Use.from_dict(r) for r in results]

    def isMachineCurrentlyUsed(self, machine_id: int) -> bool:
        """Return True if the machine is currently being used, False otherwise.

        Args:
            machine_id (int): id of the Machine

        Returns:
            bool
        """
        if not self._validateMachine(machine_id=machine_id):
            raise InvalidIdException("Machine", machine_id)

        collection = self._db["uses"]
        return (
            collection.count_documents(
                {"machine_id": machine_id, "end_timestamp": None}
            )
            == 1
        )

    def getCurrentlyUsedMachines(self) -> list[Machine]:
        """Get a list of the Machine that are being used in this moment.

        Returns:
            list[Machine]
        """
        collection = self._db["uses"]
        results = collection.find({"end_timestamp": None}, projection={"_id": 0})
        return [Machine.from_dict(r["machine_id"]) for r in results]

    def getUserTotalTime(self, user_id: int) -> float:
        """Return total time the User has used the machines.

        Args:
            user_id (int): id of the User

        Returns:
            float: User time in seconds
        """
        if not self._validateUser(user_id=user_id):
            raise InvalidIdException("User", user_id)

        collection = self._db["uses"]
        uses = collection.find(
            {"user_id": user_id, "end_timestamp": {"$exists": True, "$ne": None}}
        )
        total = 0
        for u in uses:
            total += u["end_timestamp"] - u["start_timestamp"]
        return total

    def isUserAuthroizedForMachine(
        self, machine_id: int, user_id: int = None, card_UUID: str = None
    ) -> bool:
        """Return True if a User is authorized to use a Machine.

        Args:
            machine_id (int): id of the Machine
            user_id (int, optional): id of a User. Not necessary if card_UUID is passed
            card_UUID (str, optional): card_UUID of a User. Not necessary if user_id is passed

        Returns:
            bool
        """
        if user_id is None and card_UUID is None:
            raise InvalidQueryException("User", "user id or card UUID")

        if not self._validateMachine(machine_id=machine_id):
            raise InvalidIdException("Machine id", machine_id)

        if user_id is None:
            user_id = self.getUserFromCardUUID(card_UUID=card_UUID).user_id

        if not self._validateUser(user_id=user_id):
            raise InvalidIdException("User id", user_id)

        role = self.getUserRole(user_id)
        if role.authorize_all:
            return True

        machine_type = self.getMachineMachineType(machine_id)
        authorizations = self.getUserAuthorization(user_id)

        return any(a.type_id == machine_type for a in authorizations)

    def getUserFromCardUUID(self, card_UUID: str) -> User:
        """Return user from the UUID of its card.

        Args:
            card_UUID (str): UUID of the card

        Returns:
            User
        """
        collection = self._db["users"]
        result = collection.find_one({"card_UUID": card_UUID}, projection={"_id": 0})

        if not result:
            raise InvalidQueryException("Card UUID", card_UUID)

        return User.from_dict(result)


class Database(DatabaseHelper):
    def __init__(self, settings_path="settings.toml") -> None:
        super().__init__(settings_path)

    def dropCollections(self) -> None:
        """Drop all colletcions in database. Needless to say that this is pretty dangerous."""
        for c in self._db.list_collection_names():
            self._db.drop_collection(c)

    def addRole(
        self, role_id: int, role_name: str, authorize_all: bool = False
    ) -> None:
        """Add a Role to the database.

        Args:
            role_id (int): id of the Role
            role_name (str): name of the Role
        """
        collection = self._db["roles"]
        r = Role(role_id=role_id, role_name=role_name, authorize_all=authorize_all)

        try:
            collection.insert_one(r.serialize())
        except DuplicateKeyError:
            raise DuplicatedIdException("Role", role_id)

    def getRole(self, role_id: int) -> Role:
        """Return Role by its id.

        Args:
            role_id (int): id of the Role

        Returns:
            Role
        """
        collection = self._db["roles"]

        result = collection.find_one(
            {"role_id": role_id}, projection={"_id": 0, "role_id": 1}
        )

        if result is None:
            raise InvalidIdException("Role", role_id)

        for r in self.listRoles():
            if r.role_id == result["role_id"]:
                return r

    def editRoleName(self, role_id: int, new_role_name: str) -> None:
        """Change the name of a Role.

        Args:
            role_id (int): id of the Role
            new_role_name (str): new name of the Role
        """
        r = Role(role_id, new_role_name)
        collection = self._db["roles"]
        collection.update_one(
            {"role_id": role_id}, {"$set": {"role_name": r.role_name}}
        )

    def removeRole(self, role_id: int) -> None:
        """Remove a Role from the database.

        Args:
            role_id (int): id of the Role
        """
        collection = self._db["roles"]
        collection.delete_one({"role_id": role_id})

    def listRoles(self) -> list[Role]:
        """List all Roles in the database.

        Returns:
            list[Role]: list of all Roles
        """
        return [Role.from_dict(r) for r in self._queryCollection("roles")]

    def addMachineType(self, type_id: int, type_name: str) -> None:
        """Add a MachineType to the database.

        Args:
            type_id (int): id of the MachineType
            type_name (str): name of the MachineType
        """
        collection = self._db["machine_types"]
        t = MachineType(type_id=type_id, type_name=type_name)

        try:
            collection.insert_one(t.serialize())
        except DuplicateKeyError:
            raise DuplicatedIdException("Type", type_id)

    def getMachineType(self, type_id: int) -> MachineType:
        """Return MachineType by it id.

        Args:
            type_id (int): id of the MachineType

        Returns:
            MachineType
        """
        collection = self._db["machine_types"]

        result = collection.find_one(
            {"type_id": type_id}, projection={"_id": 0, "type_id": 1}
        )

        if result is None:
            raise InvalidIdException("MachineType", type_id)

        for t in self.listMachineTypes():
            if t.type_id == result["type_id"]:
                return t

    def editMachineTypeName(self, type_id: int, new_type_name: str) -> None:
        """Change the name of a MachineType.

        Args:
            type_id (int): id of the MachineType
            new_type_name (str): new name of the type
        """
        t = MachineType(type_id, new_type_name)
        collection = self._db["machine_types"]
        collection.update_one(
            {"type_id": type_id}, {"$set": {"type_name": t.type_name}}
        )

    def removeMachineType(self, type_id: int) -> None:
        """Remove a MachineType from the database.

        Args:
            type_id (int): id of the MachineType
        """
        collection = self._db["machine_types"]
        collection.delete_one({"type_id": type_id})

    def listMachineTypes(self) -> list[MachineType]:
        """List all Machine types in the database.

        Returns:
            list[MachineType]: list of all Machine types
        """
        return [
            MachineType.from_dict(t) for t in self._queryCollection("machine_types")
        ]

    def addUser(
        self,
        name: str,
        surname: str,
        role_id: int,
        user_id: int = None,
        card_UUID: str = None,
    ) -> int:
        """Add a User to the database.

        Args:
            name (str): Name of the User
            surname (str): Surname of the User
            role_id (int): id of the Role.
            user_id (int, optional): id of the User, optional. Will be assigned automatically.
            card_UUID (str, optional): UUID of the RFID card.

        Returns:
            int: id of the User
        """
        if not self._validateRole(role_id=role_id):
            raise InvalidIdException("Role id", role_id)

        collection = self._db["users"]

        if user_id is None:
            if collection.count_documents({}) == 0:
                user_id = 0
            else:
                # find the highest User id and add 1
                last = list(collection.find({}).sort("user_id", DESCENDING).limit(1))[0]
                user_id = last["user_id"] + 1

        u = User(
            user_id=user_id,
            name=name,
            surname=surname,
            role_id=role_id,
            card_UUID=card_UUID,
        )

        try:
            collection.insert_one(u.serialize())
            return user_id
        except DuplicateKeyError:
            raise DuplicatedIdException("User", user_id)

    def listUsers(self) -> list[User]:
        """Return all User in database.

        Returns:
            list[User]: list of users
        """
        return [User.from_dict(u) for u in self._queryCollection("users")]

    def getUser(
        self, user_id: int = None, user_name: str = None, user_surname: str = None
    ) -> User:
        """Return a User from its user_id or its combination of name and surname.

        Args:
            user_id (int, optional): id of the User. Not necessary if name and surnames are provided
            user_name (str, optional): name of the User. Must be passed along the surname. \
            Not necessary if id is provided.
            user_surname (str, optional): surname of the User. Must be passed along the name. \
            Not necessary if id is provided.

        Returns:
            User
        """
        collection = self._db["users"]
        result = None

        if user_name and user_surname:
            result = collection.find_one(
                {"name": user_name, "surname": user_surname}, projection={"_id": 0}
            )
        elif user_id is not None:
            result = collection.find_one({"user_id": user_id}, projection={"_id": 0})

        if result is None:
            raise InvalidIdException("User", user_id)

        return User.from_dict(result)

    def setUserRole(
        self,
        user_id: int,
        role_id: int,
    ) -> None:
        """Set the Role of a User.

        Args:
            user_id (int): id of the User
            role_id (int): id of the Role
        """
        if not self._validateRole(role_id=role_id):
            raise InvalidIdException("Role id", role_id)

        collection = self._db["users"]
        collection.update_one({"user_id": user_id}, {"$set": {"role_id": role_id}})

    def getUserRole(self, user_id: int) -> Role:
        """Return the Role of a User.

        Args:
            user_id (int): id of the User

        Returns:
            Role
        """
        collection = self._db["users"]

        result = collection.find_one(
            {"user_id": user_id}, projection={"_id": 0, "role_id": 1}
        )

        if result is None:
            raise InvalidIdException("User", user_id)

        for r in self.listRoles():
            if r.role_id == result["role_id"]:
                return r

    def setUserId(
        self,
        user_id: int,
        new_id: int,
    ) -> None:
        """Set the id of a User.

        Args:
            user_id (int): id of the User
            new_id (int): new id of the User
        """
        collection = self._db["users"]
        collection.update_one({"user_id": user_id}, {"$set": {"user_id": new_id}})

    def getUserId(self, name: str, surname: str) -> int:
        """Get a User id from its name and surname.

        Args:
            name (str): Name of the User.
            surname (str): Surname of the User

        Returns:
            int: User id
        """
        collection = self._db["users"]
        result = collection.find_one(
            {"name": name, "surname": surname}, projection={"_id": 0, "user_id": 1}
        )

        if result:
            return result["user_id"]

        raise InvalidQueryException("User name and surname", f"{name} {surname}")

    def setUserAuthorization(
        self,
        user_id: int,
        authorization_ids: list[int],
    ) -> None:
        """Set the authorization for an User.

        Args:
            user_id (int): id of the User
            authorization_ids (list[int]): Machine types that the User is authorized to use
        """
        if not isinstance(authorization_ids, list):
            raise InvalidQueryException("Authorization ids", authorization_ids)

        machine_types = [m.type_id for m in self.listMachineTypes()]
        for i in authorization_ids:
            if i not in machine_types:
                raise InvalidIdException("MachineType", i)

        collection = self._db["users"]
        collection.update_one(
            {"user_id": user_id}, {"$set": {"authorization_ids": authorization_ids}}
        )

    def getUserAuthorization(self, user_id: int) -> list[MachineType]:
        """Return the authorization of a User.

        Args:
            user_id (int): id of the User

        Returns:
            list[MachineType]: list of Machine types the User is authorized to use
        """
        collection = self._db["users"]

        result = collection.find_one(
            {"user_id": user_id}, projection={"_id": 0, "authorization_ids": 1}
        )

        if result is None:
            raise InvalidIdException("User", user_id)

        if not result["authorization_ids"]:
            return []

        authorizations = []
        for t in self.listMachineTypes():
            if t.type_id in result["authorization_ids"]:
                authorizations.append(t)

        return authorizations

    def setUserCardUUID(
        self,
        user_id: int,
        card_UUID: str,
    ):
        """Set the UUID of the RFID card for a User.

        Args:
            user_id (int): id of the User
            card_UUID (str): UUID of the RFID card
        """
        collection = self._db["users"]
        collection.update_one({"user_id": user_id}, {"$set": {"card_UUID": card_UUID}})

    def getUserCardUUID(self, user_id: int) -> str:
        """Get the UUID of the card of a User according to its id.

        Args:
            user_id (int): id of the User

        Returns:
            str: UUID of the RFID card
        """
        collection = self._db["users"]

        result = collection.find_one(
            {"user_id": user_id}, projection={"_id": 0, "card_UUID": 1}
        )

        if result is None:
            raise InvalidIdException("User", user_id)

        return result["card_UUID"]

    def addMachine(
        self,
        machine_id: int,
        machine_name: str,
        machine_type: int,
        machine_hours: float = 0,
    ) -> None:
        """Add a Machine to the database.

        Args:
            machine_id (int): id of the Machine
            machine_name (str): name of the Machine
            machine_type (int): type of the Machine
            machine_hours (float, optional): Hours the Machine has been used. Defaults to 0.
        """
        collection = self._db["machines"]

        if not self._validateMachineType(type_id=machine_type):
            raise InvalidQueryException("Machine type", machine_type)

        m = Machine(
            machine_id=machine_id,
            machine_name=machine_name,
            machine_type=machine_type,
            machine_hours=machine_hours,
        )

        try:
            collection.insert_one(m.serialize())
        except DuplicateKeyError:
            raise DuplicatedIdException("Machine", machine_id)

    def getMachine(self, machine_id: int) -> Machine:
        """Return Machine by its id.

        Args:
            machine_id (int): id of the Machine

        Returns:
            Machine
        """
        collection = self._db["machines"]

        result = collection.find_one(
            {"machine_id": machine_id}, projection={"_id": 0, "machine_id": 1}
        )

        if result is None:
            raise InvalidIdException("Machine", machine_id)

        for m in self.listMachines():
            if m.machine_id == result["machine_id"]:
                return m

    def removeMachine(self, machine_id: int) -> None:
        """Remove a Machine from the database.

        Args:
            machine_id (int): id of the Machine
        """
        collection = self._db["machines"]
        collection.delete_one({"machine_id": machine_id})

    def listMachines(self) -> list[Machine]:
        """List all the machines in the database.

        Returns:
            list[Machine]
        """
        return [Machine.from_dict(m) for m in self._queryCollection("machines")]

    def getMachineHours(self, machine_id: int) -> float:
        """Get the Machine hours of a certain Machine according to its id.

        Args:
            machine_id (int): the id of the Machine

        Returns:
            float: Machine hours
        """
        collection = self._db["machines"]
        result = collection.find_one({"machine_id": machine_id})

        if result is None:
            raise InvalidIdException("Machine", machine_id)

        return result["machine_hours"]

    def setMachinesHours(self, machine_id: int, machine_hours: float) -> None:
        """Set the Machine hours of a particular Machine.

        Args:
            machine_id (int): id of the Machine
            machine_hours (float): hours the Machine has run
        """
        collection = self._db["machines"]
        collection.update_one(
            {"machine_id": machine_id}, {"$set": {"machine_hours": machine_hours}}
        )

    def getMachineMachineType(self, machine_id: int) -> int:
        """Get the type of the Machine according to its id.

        Args:
            machine_id (int): Machine id

        Returns:
            int: MachineType id
        """
        collection = self._db["machines"]
        result = collection.find_one({"machine_id": machine_id})

        if result is None:
            raise InvalidIdException("Machine", machine_id)

        return result["machine_type"]

    def setMachineMachineType(self, machine_id: int, machine_type: int) -> None:
        """Set the type of a Machine.

        Args:
            machine_id (int): id of the Machine
            machine_type (int): MachineType id
        """
        if machine_type not in [t.type_id for t in self.listMachineTypes()]:
            raise InvalidIdException("MachineType", machine_type)

        collection = self._db["machines"]
        collection.update_one(
            {"machine_id": machine_id}, {"$set": {"machine_type": machine_type}}
        )

    def getMachineName(self, machine_id: int) -> str:
        """Return the name of a Machine.

        Args:
            machine_id (int): id of the Machine

        Returns:
            str: name of the Machine
        """
        collection = self._db["machines"]
        result = collection.find_one({"machine_id": machine_id})

        if result is None:
            raise InvalidIdException("Machine", machine_id)

        return result["machine_name"]

    def setMachineName(self, machine_id: int, new_machine_name: str) -> None:
        """Set a new name for a Machine.

        Args:
            machine_id (int): id of the Machine
            new_machine_name (str): new name of the Machine
        """
        collection = self._db["machines"]
        collection.update_one(
            {"machine_id": machine_id}, {"$set": {"machine_name": new_machine_name}}
        )

    def addMachineMaintenance(self, machine_id: int, maintenance_id: int) -> None:
        """Add a Maintenance for a Machine.

        Args:
            machine_id (int): id of the Machine
            maintenance_id (int): id of the Maintenance
        """
        if not self._validateMaintenance(maintenance_id=maintenance_id):
            raise InvalidIdException("Maintenance", maintenance_id)

        if not self._validateMachine(machine_id=machine_id):
            raise InvalidIdException("Machine", machine_id)

        collection = self._db["machines"]
        result = collection.find_one({"machine_id": machine_id})

        if not result["maintenances"]:
            collection.update_one(
                {"machine_id": machine_id},
                {"$set": {"maintenances": [maintenance_id]}},
            )
        else:
            collection.update_one(
                {"machine_id": machine_id},
                {"$push": {"maintenances": maintenance_id}},
            )

    def getMachineMaintenances(self, machine_id: int) -> list[Maintenance]:
        """Get Maintenances for a Machine.

        Args:
            machine_id (int): id of the Machine

        Returns:
            list[Maintenance]: list of Maintenances
        """
        collection = self._db["machines"]
        result = collection.find_one({"machine_id": machine_id})

        if result is None:
            raise InvalidIdException("Machine", machine_id)

        return [
            m
            for m in self.listMaintenances()
            if m.maintenance_id in result["maintenances"]
        ]

    def removeMachineMaintenance(self, machine_id: int, maintenance_id: int) -> None:
        """Remove a Maintenance from a Machine.

        Args:
            machine_id (int): id of the Machine
            maintenance_id (int): id of the Maintenances
        """
        if not self._validateMaintenance(maintenance_id=maintenance_id):
            raise InvalidIdException("Maintenance", maintenance_id)

        if not self._validateMachine(machine_id=machine_id):
            raise InvalidIdException("Machine", machine_id)

        collection = self._db["machines"]
        result = collection.find_one({"machine_id": machine_id})

        if len(result["maintenances"]) == 0:
            raise InvalidIdException("Machine", machine_id)

        collection.update_one(
            {"machine_id": machine_id},
            {"$pull": {"maintenances": maintenance_id}},
        )

    def addMaintenance(
        self, hours_between: float, description: str = None, maintenance_id: int = None
    ) -> int:
        """Add a Maintenance to database and return its IDS.

        Args:
            hours_between (float): hours between consecutive interventions
            description (str, optional): Description of the Maintenance. Defaults to None.
            maintenance_id (int, optional): id of the Maintenance. Automatically assigned if \
                 not passed.

        Returns:
            int: id of the Maintenance
        """
        collection = self._db["maintenances"]

        if maintenance_id is None:
            if collection.count_documents({}) == 0:
                maintenance_id = 0
            else:
                # find the highest User id and add 1
                last = list(
                    collection.find({}).sort("maintenance_id", DESCENDING).limit(1)
                )[0]
                maintenance_id = last["maintenance_id"] + 1

        m = Maintenance(
            maintenance_id=maintenance_id,
            hours_between=hours_between,
            description=description,
        )

        try:
            collection.insert_one(m.serialize())
        except DuplicateKeyError:
            raise DuplicatedIdException("Maintenance", maintenance_id)

        return maintenance_id

    def getMaintenance(self, maintenance_id: int) -> Maintenance:
        """Return Maintenance by its id.

        Args:
            maintenance_id (int): id of the Maintenance

        Returns:
            Role
        """
        collection = self._db["maintenances"]

        result = collection.find_one(
            {"maintenance_id": maintenance_id},
        )

        if result is None:
            raise InvalidIdException("Maintenance", maintenance_id)

        for m in self.listMaintenances():
            if m.maintenance_id == result["maintenance_id"]:
                return m

    def removeMaintenance(self, maintenance_id: int) -> None:
        """Remove a maintenance according to it id.

        Args:
            maintenance_id (int): id of the Maintenance
        """
        collection = self._db["maintenances"]
        collection.delete_one({"maintenance_id": maintenance_id})

    def getMaintenanceDescription(self, maintenance_id: int) -> str:
        """Get a Maintenance description according to its id.

        Args:
            maintenance_id (int): id of the Maintenance

        Returns:
            str: description of the Maintenance
        """
        collection = self._db["maintenances"]
        result = collection.find_one(
            {"maintenance_id": maintenance_id},
        )

        if result is None:
            raise InvalidIdException("Maintenance", maintenance_id)

        return result["description"]

    def setMaintenanceDescription(
        self, maintenance_id: int, new_maintenance_description: str
    ) -> None:
        """Set the description for a Maintenance.

        Args:
            maintenance_id (int): id of the Maintenance
            new_maintenance_description (str): new Maintenance description
        """
        collection = self._db["maintenances"]
        collection.update_one(
            {"maintenance_id": maintenance_id},
            {"$set": {"description": new_maintenance_description}},
        )

    def getMaintenanceHoursBetween(self, maintenance_id: int) -> float:
        """Get hours between a Maintenance.

        Args:
            maintenance_id (int): id of the Maintenance

        Returns:
            float: hours between a Maintenance
        """
        collection = self._db["maintenances"]
        result = collection.find_one(
            {"maintenance_id": maintenance_id},
        )

        if result is None:
            raise InvalidIdException("Maintenance", maintenance_id)

        return result["hours_between"]

    def setMaintenanceHoursBetween(
        self, maintenance_id: int, new_hours_between: float
    ) -> None:
        """Set hours between Maintenances.

        Args:
            maintenance_id (int): id of the Maintenance
            new_hours_between (float): hours between Maintenances
        """
        collection = self._db["maintenances"]
        collection.update_one(
            {"maintenance_id": maintenance_id},
            {"$set": {"hours_between": new_hours_between}},
        )

    def listMaintenances(self) -> list[Maintenance]:
        """List all Maintenances from the database.

        Returns:
            list[Maintenance]: list of Maintenances
        """
        return [Maintenance.from_dict(m) for m in self._queryCollection("maintenances")]

    def addIntervention(
        self,
        maintenance_id: int,
        machine_id: int,
        user_id: int,
        timestamp: float = None,
    ) -> int:
        """Add Intervention to Database.

        Args:
            maintenance_id (int): id of the Maintenance
            machine_id (int): id of the Machine
            user_id (int): id of the User
            timestamp (float, optional): Intervention timestamp. \
                If not provided, current time is used

        Returns:
            int: id of the Intervention
        """
        if not self._validateMaintenance(maintenance_id=maintenance_id):
            raise InvalidIdException("Maintenance", maintenance_id)

        if not self._validateMachine(machine_id=machine_id):
            raise InvalidIdException("Machine", machine_id)

        if not self._validateUser(user_id=user_id):
            raise InvalidIdException("User", user_id)

        if timestamp is None:
            timestamp = time()

        collection = self._db["interventions"]
        if collection.count_documents({}) == 0:
            intervention_id = 0
        else:
            # find the highest User id and add 1
            last = list(
                collection.find({}).sort("intervention_id", DESCENDING).limit(1)
            )[0]
            intervention_id = last["intervention_id"] + 1

        i = Intervention(
            intervention_id=intervention_id,
            maintenance_id=maintenance_id,
            machine_id=machine_id,
            user_id=user_id,
            timestamp=timestamp,
        )

        collection.insert_one(i.serialize())

        return intervention_id

    def getIntervention(self, intervention_id: int) -> Intervention:
        """Get Intervention according to its id.

        Args:
            intervention_id (int): id of the Intervention

        Returns:
            Intervention
        """
        collection = self._db["interventions"]

        result = collection.find_one(
            {"intervention_id": intervention_id},
            projection={"_id": 0, "intervention_id": 1},
        )

        if result is None:
            raise InvalidIdException("Intervention", intervention_id)

        for i in self.listInterventions():
            if i.intervention_id == result["intervention_id"]:
                return i

    def listInterventions(self) -> list[Intervention]:
        """Return the Interventions in the database.

        Returns:
            list[Intervention]: list of interventions
        """
        return [
            Intervention.from_dict(i) for i in self._queryCollection(("interventions"))
        ]

    def getInterventionUser(self, intervention_id: int) -> User:
        """Get User relative to intervention, according to its id.

        Args:
            intervention_id (int): id of the Intervention

        Returns:
            User
        """
        collection = self._db["interventions"]
        result = collection.find_one(
            {"intervention_id": intervention_id},
            projection={"_id": 0, "user_id": 1},
        )

        if result is None:
            raise InvalidIdException("Intervention", intervention_id)

        for u in self.listUsers():
            if u.user_id == result["user_id"]:
                return u

    def getInterventionMachine(self, intervention_id: int) -> Machine:
        """Get Machine relative to interventon, according to its id.

        Args:
            intervention_id (int): id of the Intervention

        Returns:
            Machine
        """
        collection = self._db["interventions"]
        result = collection.find_one(
            {"intervention_id": intervention_id},
            projection={"_id": 0, "machine_id": 1},
        )

        if result is None:
            raise InvalidIdException("Intervention", intervention_id)

        for m in self.listMachines():
            if m.machine_id == result["machine_id"]:
                return m

    def getInterventionTimestamp(self, intervention_id: int) -> float:
        """Get timestamp relative to Intervention according to its id.

        Args:
            intervention_id (int): id of the Intervention

        Returns:
            float: timestamp
        """
        collection = self._db["interventions"]
        result = collection.find_one(
            {"intervention_id": intervention_id},
            projection={"_id": 0, "timestamp": 1},
        )

        if result is None:
            raise InvalidIdException("Intervention", intervention_id)

        return result["timestamp"]

    def startUse(
        self,
        machine_id: int,
        user_id: int = None,
        card_UUID: str = None,
        timestamp: float = None,
    ) -> None:
        """Start use of a Machine for a certain User.

        Args:
            machine_id (int): id of a Machine
            user_id (int, optional): id of a User. Not necessary if card_UUID is passed
            card_UUID (str, optional): card_UUID of a User. Not necessary if user_id is passed
            timestamp (float, optional): start timestamp. If not passed, current time will be used
        """
        if not user_id:
            user_id = self._getUserIdFromCard(card_UUID=card_UUID)

        if not self._validateUser(user_id=user_id):
            raise InvalidIdException("User", user_id)

        if not self._validateMachine(machine_id=machine_id):
            raise InvalidIdException(
                "Machine",
                machine_id,
            )

        if self.isMachineCurrentlyUsed(machine_id=machine_id):
            raise InvalidIdException(
                "Machine",
                machine_id,
            )

        if timestamp is None:
            timestamp = time()

        collection = self._db["uses"]

        if collection.count_documents({}) == 0:
            use_id = 0
        else:
            # find the highest User id and add 1
            last = list(collection.find({}).sort("use_id", DESCENDING).limit(1))[0]
            use_id = last["use_id"] + 1

        u = Use(
            use_id=use_id,
            user_id=user_id,
            machine_id=machine_id,
            start_timestamp=timestamp,
        )

        collection.insert_one(u.serialize())

    def endUse(
        self,
        machine_id: int,
        user_id: int = None,
        card_UUID: str = None,
        timestamp: float = None,
    ) -> float:
        """End a use that was previously started.

        Args:
            machine_id (int): id of the Machine
            user_id (int, optional): id of a User. Not necessary if card_UUID is passed
            card_UUID (str, optional): card_UUID of a User. Not necessary if user_id is passed
            timestamp (float, optional): start timestamp. If not passed, current time will be used

        Returns:
            float: duration of the Use
        """
        if not user_id:
            user_id = self._getUserIdFromCard(card_UUID=card_UUID)

        if not self._validateUser(user_id=user_id):
            raise InvalidIdException("User", user_id)

        if not self._validateMachine(machine_id=machine_id):
            raise InvalidIdException(
                "Machine",
                machine_id,
            )

        if not self._isUserCurrentlyUsing(machine_id=machine_id, user_id=user_id):
            raise InvalidQueryException("User", user_id)

        if timestamp is None:
            timestamp = time()

        collection = self._db["uses"]
        collection.update_one(
            {"user_id": user_id, "machine_id": machine_id, "end_timestamp": None},
            {"$set": {"end_timestamp": timestamp}},
        )

        result = collection.find_one({"end_timestamp": timestamp})
        return timestamp - result["start_timestamp"]
