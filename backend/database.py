"""This is the class handling the Database. More to come."""

from entities import User, Role, MachineType, Machine, Maintenance
from exceptions import (
    DuplicatedIdException,
    InvalidIdException,
    MissingQueryValueException,
    InvalidQueryValueException,
)

from pymongo import MongoClient, DESCENDING
from pymongo.errors import DuplicateKeyError

import toml


class Database:
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

    def dropDatabase(self) -> None:
        """Drop all colletions in database. Needless to say that this is pretty dangerous."""
        for c in self._db.list_collection_names():
            self._db.drop_collection(c)

    def addRole(self, role_id: int, role_name: str) -> None:
        """Add a Role to the database.

        Args:
            role_id (int): id of the Role
            role_name (str): name of the Role
        """
        collection = self._db["roles"]
        r = Role(role_id, role_name)

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
            raise InvalidQueryValueException("Role id", role_id)

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
        t = MachineType(type_id, type_name)

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
            raise InvalidQueryValueException("MachineType id", type_id)

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
        user_id: int = None,
        role_id: int = None,
        card_UUID: str = None,
    ) -> int:
        """Add a User to the database.

        Args:
            name (str): Name of the User
            surname (str): Surname of the User
            user_id (int, optional): id of the User, optional. Will be assigned automatically.
            role_id (int, optional): id of the Role.
            card_UUID (str, optional): UUID of the RFID card.

        Returns:
            int: id of the User
        """
        if role_id is not None and all(
            r.role_id != role_id for r in self.listMachines()
        ):
            raise InvalidIdException("Role id", role_id)

        collection = self._db["users"]

        if user_id is None:
            if collection.count_documents({}) == 0:
                user_id = 0
            else:
                # find the highest User id and add 1
                last = list(collection.find({}).sort("user_id", DESCENDING).limit(1))[0]
                user_id = last["user_id"] + 1

        u = User(user_id, name, surname, role_id=role_id, card_UUID=card_UUID)

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
            raise InvalidQueryValueException("User id", user_id)

        return User.from_dict(result)

        return None

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
        if all(r.role_id != role_id for r in self.listMachines()):
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
            return None

        for r in self.listMachines():
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

    def getUserId(self, user_name: str = None, user_surname: str = None) -> int:
        """Get a User id from its name and surname.

        Args:
            user_name (str): Name of the User.
            user_surname (str): Surname of the User

        Returns:
            int: User id
        """
        if user_name is None or user_surname is None:
            raise MissingQueryValueException("Name and Surname", None)

        user = self.getUser(user_name=user_name, user_surname=user_surname)

        if user:
            return user.user_id

        return None

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
            raise InvalidQueryValueException("Authorization ids", authorization_ids)

        machine_types = [m.type_id for m in self.listMachineTypes()]
        for i in authorization_ids:
            if not isinstance(i, int):
                raise InvalidQueryValueException("Authorization id", i)

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
            return None

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
            return None

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

        m = Machine(machine_id, machine_name, machine_type, machine_hours=machine_hours)

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
            raise InvalidQueryValueException("Machine id", machine_id)

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
            raise InvalidQueryValueException("Machine id", machine_id)

        return result["hours_used"]

    def setMachinesHours(self, machine_id: int, machine_hours: float) -> None:
        """Set the Machine hours of a particular Machine.

        Args:
            machine_id (int): id of the Machine
            machine_hours (float): hours the Machine has run
        """
        collection = self._db["machines"]
        collection.update_one(
            {"machine_id": machine_id}, {"$set": {"hours_used": machine_hours}}
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
            raise InvalidQueryValueException("Machine id", machine_id)

        return result["machine_type"]

    def setMachineMachineType(self, machine_id: int, machine_type: int) -> None:
        """Set the type of a Machine.

        Args:
            machine_id (int): id of the Machine
            machine_type (int): MachineType id
        """
        if machine_type not in [t.type_id for t in self.listMachineTypes()]:
            raise InvalidQueryValueException("MachineType id", machine_type)

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
            raise InvalidQueryValueException("Machine id", machine_id)

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
        if all(maintenance_id != m.maintenance_id for m in self.listMaintenances()):
            raise InvalidQueryValueException("Maintenance id", maintenance_id)

        collection = self._db["machines"]
        result = collection.find_one({"machine_id": machine_id})

        if result is None:
            raise InvalidQueryValueException("Machine id", machine_id)

        if result["maintenances"] is None:
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
            raise InvalidQueryValueException("Machine id", machine_id)

        if not result["maintenances"]:
            return []

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
        if all(maintenance_id != m.maintenance_id for m in self.listMaintenances()):
            raise InvalidQueryValueException("Maintenance id", maintenance_id)

        collection = self._db["machines"]
        result = collection.find_one({"machine_id": machine_id})

        if result is None:
            raise InvalidQueryValueException("Machine id", machine_id)

        if result["maintenances"] is None:
            raise InvalidQueryValueException("Machine", "maintenances")
        else:
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
            projection={"_id": 0, "maintenance_id": 1},
        )

        if result is None:
            raise InvalidQueryValueException("Maintenance id", maintenance_id)

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
        result = collection.find_one({"maintenance_id": maintenance_id})

        if result is None:
            raise InvalidQueryValueException("Maintenance id", maintenance_id)

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
        result = collection.find_one({"maintenance_id": maintenance_id})

        if result is None:
            raise InvalidQueryValueException("Maintenance id", maintenance_id)

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
