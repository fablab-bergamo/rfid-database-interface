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
    """Class handling the connection from and to the database"""

    def __init__(self, settings_path="settings.toml") -> None:
        """Creates instance of Database

        Args:
            settings_path (str, optional): TOML file settings. Defaults to "settings.toml".
        """
        self._settings_path = settings_path

        self._client = None
        self._db = None

        self._loadSettings()
        self._connect()
        self._initCollections()

    def _loadSettings(self) -> None:
        """Loads settings from TOML file"""
        self._settings = toml.load(self._settings_path)
        self._url = self._settings["database"]["url"]
        self._name = self._settings["database"]["name"]

    def _connect(self) -> None:
        """Connects to MongoDB server"""
        self._client = MongoClient(self._url)
        self._db = self._client[self._name]

    def _initCollections(self) -> None:
        """Initializes the collections in the database"""
        collections = self._db.list_collection_names()

        if "roles" not in collections:
            self._db["roles"].create_index("role_id", unique=True)

        if "machine_types" not in collections:
            self._db["machine_types"].create_index("type_id", unique=True)

        if "users" not in collections:
            self._db["users"].create_index("user_id", unique=True)

        if "machines" not in collections:
            self._db["machines"].create_index("machine_id", unique=True)

        if "maintenances" not in collections:
            self._db["maintenances"].create_index("maintenance_id", unique=True)

    def _queryCollection(self, collection_name: str) -> list[dict]:
        """Queries a collection and return the dict without the MongoDB mandatory _id

        Args:
            collection_name (str): name of the collection

        Returns:
            list[dict]: list of dicts as returned from MongoDB
        """
        collection = self._db[collection_name]
        return list(collection.find(projection={"_id": 0}))

    def dropDatabase(self) -> None:
        """Drop all colletions in database. Needless to say that this is pretty dangerous"""
        for c in self._db.list_collection_names():
            self._db.drop_collection(c)

    def addRole(self, role_id: int, role_name: str) -> None:
        """Adds a role to the database

        Args:
            role_id (int): id of the role
            role_name (str): name of the role
        """
        collection = self._db["roles"]
        r = Role(role_id, role_name)

        try:
            collection.insert_one(r.serialize())
        except DuplicateKeyError:
            raise DuplicatedIdException("role", role_id)

    def getRole(self, role_id: int) -> Role:
        """Returns role by its id

        Args:
            role_id (int): id of the role

        Returns:
            Role
        """
        collection = self._db["roles"]

        result = collection.find_one(
            {"role_id": role_id}, projection={"_id": 0, "role_id": 1}
        )

        if not result:
            return None

        for r in self.listRoles():
            if r.role_id == result["role_id"]:
                return r

    def editRoleName(self, role_id: int, new_role_name: str) -> None:
        """Changes the name of a role

        Args:
            role_id (int): id of the role
            new_role_name (str): new name of the role
        """
        r = Role(role_id, new_role_name)
        collection = self._db["roles"]
        collection.update_one(
            {"role_id": role_id}, {"$set": {"role_name": r.role_name}}
        )

    def removeRole(self, role_id: int) -> None:
        """Removes a role from the database

        Args:
            role_id (int): id of the role
        """
        collection = self._db["roles"]
        collection.delete_one({"role_id": role_id})

    def listRoles(self) -> list[Role]:
        """List all roles in the database

        Returns:
            list[Role]: list of all roles
        """
        return [Role.from_dict(r) for r in self._queryCollection("roles")]

    def addMachineType(self, type_id: int, type_name: str) -> None:
        """Adds a machine type to the database

        Args:
            type_id (int): id of the machine type
            type_name (str): name of the machine type
        """
        collection = self._db["machine_types"]
        t = MachineType(type_id, type_name)

        try:
            collection.insert_one(t.serialize())
        except DuplicateKeyError:
            raise DuplicatedIdException("type", type_id)

    def getMachineType(self, type_id: int) -> MachineType:
        """Returns role by its id

        Args:
            type_id (int): id of the type

        Returns:
            MachineType
        """
        collection = self._db["machine_types"]

        result = collection.find_one(
            {"type_id": type_id}, projection={"_id": 0, "type_id": 1}
        )

        if not result:
            return None

        for t in self.listMachineTypes():
            if t.type_id == result["type_id"]:
                return t

    def editMachineTypeName(self, type_id: int, new_type_name: str) -> None:
        """Changes the name of a machine type

        Args:
            type_id (int): id of the machine type
            new_type_name (str): new name of the type
        """
        t = MachineType(type_id, new_type_name)
        collection = self._db["machine_types"]
        collection.update_one(
            {"type_id": type_id}, {"$set": {"type_name": t.type_name}}
        )

    def removeMachineType(self, type_id: int) -> None:
        """Removes a machine type from the database

        Args:
            type_id (int): id of the machine type
        """
        collection = self._db["machine_types"]
        collection.delete_one({"type_id": type_id})

    def listMachineTypes(self) -> list[MachineType]:
        """List all machine types in the database

        Returns:
            list[MachineType]: list of all machine types
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
        """Adds a user to the database

        Args:
            name (str): Name of the user
            surname (str): Surname of the user
            user_id (int, optional): id of the user, optional. Will be assigned automatically.
            role_id (int, optional): id of the role.
            card_UUID (str, optional): UUID of the RFID card.

        Returns:
            int: id of the user
        """
        if role_id is not None and all(r.role_id != role_id for r in self.listRoles()):
            raise InvalidIdException("role", role_id)

        collection = self._db["users"]

        if user_id is None:
            if collection.count_documents({}) == 0:
                user_id = 0
            else:
                # find the highest user id and add 1
                last = list(collection.find({}).sort("user_id", DESCENDING).limit(1))[0]
                user_id = last["user_id"] + 1

        u = User(user_id, name, surname, role_id=role_id, card_UUID=card_UUID)

        try:
            collection.insert_one(u.serialize())
            return user_id
        except DuplicateKeyError:
            raise DuplicatedIdException("user", user_id)

    def listUsers(self) -> list[User]:
        """Returns all users in database

        Returns:
            list[User]: list of users
        """
        return [User.from_dict(u) for u in self._queryCollection("users")]

    def getUser(
        self, user_id: int = None, user_name: str = None, user_surname: str = None
    ) -> User:
        """Returns a user from its user_id or its combination of name and surname

        Args:
            user_id (int, optional): id of the user. Not necessary if name and surnames are provided
            user_name (str, optional): name of the user. Must be passed along the surname. \
            Not necessary if id is provided.
            user_surname (str, optional): surname of the user. Must be passed along the name. \
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

        if result:
            return User.from_dict(result)

        return None

    def setUserRole(
        self,
        user_id: int,
        role_id: int,
    ) -> None:
        """Sets the role of a user

        Args:
            user_id (int): id of the user
            role_id (int): id of the role
        """
        if all(r.role_id != role_id for r in self.listRoles()):
            raise InvalidIdException("role", role_id)

        collection = self._db["users"]
        collection.update_one({"user_id": user_id}, {"$set": {"role_id": role_id}})

    def getUserRole(self, user_id: int) -> Role:
        """Returns the role of a user

        Args:
            user_id (int): id of the user

        Returns:
            Role
        """
        collection = self._db["users"]

        result = collection.find_one(
            {"user_id": user_id}, projection={"_id": 0, "role_id": 1}
        )

        if not result:
            return None

        for r in self.listRoles():
            if r.role_id == result["role_id"]:
                return r

    def setUserId(
        self,
        user_id: int,
        new_id: int,
    ) -> None:
        """Sets the id of a user

        Args:
            user_id (int): id of the user
            new_id (int): new id of the user
        """
        collection = self._db["users"]
        collection.update_one({"user_id": user_id}, {"$set": {"user_id": new_id}})

    def getUserId(self, user_name: str = None, user_surname: str = None) -> int:
        """_summary_

        Args:
            user_name (str): Name of the user.
            user_surname (str): Surname of the user

        Returns:
            int: User id
        """
        if user_name is None or user_surname is None:
            raise MissingQueryValueException("name and surname", "user")

        user = self.getUser(user_name=user_name, user_surname=user_surname)

        if user:
            return user.user_id

        return None

    def setUserAuthorization(
        self,
        user_id: int,
        authorization_ids: list[int],
    ) -> None:
        """Sets the authorization for an user

        Args:
            user_id (int): id of the user
            authorization_ids (list[int]): machine types that the user is authorized to use
        """

        if not isinstance(authorization_ids, list):
            raise InvalidQueryValueException("authorization ids", authorization_ids)

        machine_types = [m.type_id for m in self.listMachineTypes()]
        for i in authorization_ids:
            if not isinstance(i, int):
                raise InvalidQueryValueException("authorization id", i)

            if i not in machine_types:
                raise InvalidIdException("machine type", i)

        collection = self._db["users"]
        collection.update_one(
            {"user_id": user_id}, {"$set": {"authorization_ids": authorization_ids}}
        )

    def getUserAuthorization(self, user_id: int) -> list[MachineType]:
        """Returns the authorization of a user

        Args:
            user_id (int): id of the user

        Returns:
            list[MachineType]: list of machine types the user is authorized to use
        """
        collection = self._db["users"]

        result = collection.find_one(
            {"user_id": user_id}, projection={"_id": 0, "authorization_ids": 1}
        )

        if not result:
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
        """Set the UUID of the RFID card for a user

        Args:
            user_id (int): id of the user
            card_UUID (str): UUID of the RFID card
        """

        collection = self._db["users"]
        collection.update_one({"user_id": user_id}, {"$set": {"card_UUID": card_UUID}})

    def getUserCardUUID(self, user_id: int) -> str:
        """Get the UUID of the card of a user

        Args:
            user_id (int): id of the user

        Returns:
            str: UUID of the RFID card
        """
        collection = self._db["users"]

        result = collection.find_one(
            {"user_id": user_id}, projection={"_id": 0, "card_UUID": 1}
        )

        if not result:
            return None

        return result["card_UUID"]

    def addMachine(
        self,
        machine_id: int,
        machine_name: str,
        machine_type: str,
        machine_hours: float = 0,
    ) -> None:
        """Adds a machine to the database

        Args:
            machine_id (int): id of the machine
            machine_name (str): name of the machine
            machine_type (str): type of the machine
            machine_hours (float, optional): Hours the machine has been used. Defaults to 0.
        """
        collection = self._db["machines"]

        m = Machine(machine_id, machine_name, machine_type, machine_hours=machine_hours)

        try:
            collection.insert_one(m.serialize())
        except DuplicateKeyError:
            raise DuplicatedIdException("machine", machine_id)

    def removeMachine(self, machine_id: int) -> None:
        """Removes a machine from the database

        Args:
            machine_id (int): id of the machine
        """
        collection = self._db["machines"]
        collection.delete_one({"machine_id": machine_id})

    def listMachines(self) -> list[Machine]:
        """List all the machines in the database

        Returns:
            list[Machine]
        """
        return [Machine.from_dict(m) for m in self._queryCollection("machines")]

    def getMachineHours(self, machine_id: int) -> float:
        """Get the machine hours of a certain machine

        Args:
            machine_id (int): the id of the machine

        Returns:
            float: machine hours
        """
        collection = self._db["machines"]
        result = collection.find_one({"machine_id": machine_id})

        if result:
            return result["hours_used"]

        return None

    def setMachinesHours(self, machine_id: int, machine_hours: float) -> None:
        """Set the machine hours of a particular machine

        Args:
            machine_id (int): id of the machine
            machine_hours (float): hours the machine has run
        """
        collection = self._db["machines"]
        collection.update_one(
            {"machine_id": machine_id}, {"$set": {"hours_used": machine_hours}}
        )

    def getTypeOfMachine(self, machine_id: int) -> int:
        """Get the type of the machine

        Args:
            machine_id (int): machine id

        Returns:
            int: machine type id
        """
        collection = self._db["machines"]
        result = collection.find_one({"machine_id": machine_id})

        if result:
            return result["machine_type"]

        return None

    def setMachineType(self, machine_id: int, machine_type: int) -> None:
        """Set the type of a machine

        Args:
            machine_id (int): id of the machine
            machine_type (int): machine type id
        """
        if machine_type not in [t.type_id for t in self.listMachineTypes()]:
            return

        collection = self._db["machines"]
        collection.update_one(
            {"machine_id": machine_id}, {"$set": {"machine_type": machine_type}}
        )

    def getMachineName(self, machine_id: int) -> str:
        """Returns the name of a machine

        Args:
            machine_id (int): id of the machine

        Returns:
            str: name of the machine
        """
        collection = self._db["machines"]
        result = collection.find_one({"machine_id": machine_id})

        if result:
            return result["machine_name"]

        return None

    def addMachineMaintenance(self, machine_id: int, maintenance_id: int) -> None:
        if all(maintenance_id != m.maintenance_id for m in self.listMaintenances()):
            return

        collection = self._db["machines"]
        result = collection.find_one({"machine_id": machine_id})

        if result:
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

        return None

    def getMachineMaintenances(self, machine_id: int) -> list[Maintenance]:
        collection = self._db["machines"]
        result = collection.find_one({"machine_id": machine_id})

        if not result:
            return

        if not result["maintenances"]:
            return []

        return [
            m
            for m in self.listMaintenances()
            if m.maintenance_id in result["maintenances"]
        ]

    def setMachineName(self, machine_id: int, machine_new_name: str) -> None:
        """Sets the name of the machine

        Args:
            machine_id (int): id of the machine
            machine_new_name (str): new name of the machine
        """
        collection = self._db["machines"]
        collection.update_one(
            {"machine_id": machine_id}, {"$set": {"machine_name": machine_new_name}}
        )

    def addMaintenance(
        self, hours_between: float, description: str = None, maintenance_id: int = None
    ) -> int:
        collection = self._db["maintenances"]

        if maintenance_id is None:
            if collection.count_documents({}) == 0:
                maintenance_id = 0
            else:
                # find the highest user id and add 1
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
            raise DuplicatedIdException("maintenance", maintenance_id)

        return maintenance_id

    def removeMaintenance(self, maintenance_id: int = None) -> None:
        collection = self._db["maintenances"]
        collection.delete_one({"maintenance_id": maintenance_id})

    def listMaintenances(self) -> list[Maintenance]:
        return [Maintenance.from_dict(m) for m in self._queryCollection("maintenances")]
