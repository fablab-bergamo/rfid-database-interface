import unittest

from string import ascii_uppercase
from random import choices, randint, random

from database import Database, DuplicatedIdException, InvalidQueryValueException


def random_string(k=16):
    return "".join(choices(ascii_uppercase, k=k))


def random_between(a, b):
    return random() * (b - a) + 1


class TestDB(unittest.TestCase):
    def initDatabase(self):
        d = Database("test_settings.toml")
        d.dropDatabase()
        return Database("test_settings.toml")

    def test_connection(self):
        _ = Database("test_settings.toml")

    def test_drop(self):
        d = Database("test_settings.toml")
        d.dropDatabase()
        self.assertEqual(len(d.listMachines()), 0)
        self.assertEqual(len(d.listMachineTypes()), 0)
        self.assertEqual(len(d.listMaintenances()), 0)
        self.assertEqual(len(d.listMachines()), 0)
        self.assertEqual(len(d.listUsers()), 0)

    def test_simple_add_roles(self):
        d = self.initDatabase()

        role_names = ["user", "power user", "moderator", "crew", "admin", "super admin"]

        for i, r in enumerate(role_names):
            d.addRole(i, r)

        # check if roles were added
        self.assertEqual(len(role_names), len(d.listRoles()))

        # check if role parameters are real
        for i, r in enumerate(d.listRoles()):
            self.assertEqual(r.role_id, i)
            self.assertEqual(r.role_name, role_names[i])

        # edit a role name
        new_name = "TEST ROLE WOW"
        d.editRoleName(0, new_name)
        self.assertEqual(d.getRole(0).role_name, new_name)
        self.assertEqual(len(d.listRoles()), len(role_names))

        # create a new role
        new_role = "ÜBER ADMIN"
        d.addRole(len(role_names) + 1, new_role)
        self.assertEqual(len(d.listRoles()), len(role_names) + 1)
        self.assertEqual(d.getRole(len(d.listRoles())).role_name, new_role)

        # remove a role
        d.removeRole(0)
        self.assertEqual(len(d.listRoles()), len(role_names))
        # add a new role
        d.addRole("ÜBERÜBER ADMIN", 1000)
        self.assertEqual(len(d.listRoles()), len(role_names) + 1)

        # add a duplicate role and catch exception
        d.addRole("0", "aaa")
        with self.assertRaises(DuplicatedIdException):
            d.addRole("0", "duplicate")
            self.assertEqual(len(d.listRoles()), 1)

    def test_simple_add_types(self):
        d = self.initDatabase()
        type_names = ["3d printer", "laser cutter", "vertical drill", "saw"]

        for i, t in enumerate(type_names):
            d.addMachineType(i, t)

        # check if types were added
        self.assertEqual(len(d.listMachineTypes()), len(type_names))

        # rename a machine type
        new_name = "TEST TYPE WOW"
        d.editMachineTypeName(0, new_name)
        self.assertEqual(d.getMachineType(0).type_name, new_name)

        # add a new type
        new_type = "ÜBER TYPE"
        d.addMachineType(len(type_names) + 1, new_type)
        self.assertEqual(len(d.listMachineTypes()), len(type_names) + 1)
        self.assertEqual(d.getMachineType(len(type_names) + 1).type_name, new_type)

        # remove a type
        d.removeMachineType(0)
        self.assertEqual(len(d.listMachineTypes()), len(type_names))
        # add a new type
        d.addMachineType("ÜBERÜBER TYPE", 1000)
        self.assertEqual(len(d.listMachineTypes()), len(type_names) + 1)

        # add a duplicated type and catch the exception
        d.addMachineType("0", "aaa")
        with self.assertRaises(DuplicatedIdException):
            d.addMachineType("0", "duplicate")
            self.assertEqual(len(d.listMachineTypes()), 1)

    def test_simple_add_users(self):
        d = self.initDatabase()

        names = ["Alessandro", "Lorenzo", "Diego", "Tommaso", "Riccardo"]
        surnames = [
            "Rossi",
            "Bianchi",
            "Verdi",
            "Colombo",
            "Fumagalli",
        ]

        # just to make sure
        self.assertEqual(len(names), len(surnames))

        ids = []
        # add roles
        for n, s in zip(names, surnames):
            user_id = d.addUser(n, s)
            self.assertIsNotNone(user_id)
            ids.append(user_id)

        # check if roles were added
        self.assertEqual(len(d.listUsers()), len(names))
        # check that every role is unique
        self.assertEqual(len(ids), len(set(ids)))

        # set a new ID
        for x in range(len(names)):
            d.setUserId(x, 1000 + x)
        # check that the ids are equal
        ids = [u.user_id for u in d.listUsers()]
        self.assertListEqual(list(x + 1000 for x in range(len(names))), ids)

        # get a user from name
        n, s = names[0], surnames[0]
        u = d.getUser(user_name=n, user_surname=s)
        self.assertEqual(u.name, n)
        self.assertEqual(u.surname, s)

        # get a user from id
        p = d.getUser(u.user_id)
        self.assertEqual(p.user_id, u.user_id)

        # set a user card
        UUID = random_string()
        d.setUserCardUUID(u.user_id, UUID)
        self.assertEqual(UUID, d.getUserCardUUID(u.user_id))

    def test_long_add_users(self):
        d = self.initDatabase()
        name = "Mario"
        surname = "Rossi"
        USERS = 100

        for _ in range(USERS):
            d.addUser(name, surname)
        self.assertEqual(len(d.listUsers()), USERS)

    def test_simple_add_machines(self):
        d = self.initDatabase()

        TYPES = 10
        MACHINES = 10
        current_id = 0

        # create machines for each type
        for i in range(TYPES):
            NAME = random_string(10)
            d.addMachineType(type_id=i, type_name=NAME)
            self.assertEqual(len(d.listMachineTypes()), i + 1)
            for _ in range(MACHINES):
                name = random_string(6)
                d.addMachine(current_id, name, i)
                current_id += 1

        # test that they have been added
        self.assertEqual(MACHINES * TYPES, len(d.listMachines()))

        for current_id in range(MACHINES * TYPES):
            # test rename
            NAME = random_string(10)
            d.setMachineName(current_id, NAME)
            self.assertEqual(d.getMachineName(current_id), NAME)
            # test new type
            NEW_TYPE = randint(0, TYPES - 1)
            d.setMachineMachineType(current_id, NEW_TYPE)
            self.assertEqual(NEW_TYPE, d.getMachineMachineType(current_id))

            d.removeMachine(current_id)
            # test delete
            self.assertEqual(MACHINES * TYPES - current_id - 1, len(d.listMachines()))

        # test delete
        self.assertEqual(0, len(d.listMachines()))

    def test_simple_maintenance(self):
        d = self.initDatabase()

        MAINTENANCES = 100

        for x in range(MAINTENANCES):
            hours_between = random_between(5, 10)
            description = random_string(50)
            new_id = d.addMaintenance(hours_between, description)
            # check if the new id is the same as the index
            self.assertEqual(x, new_id)
            # check getters and setters
            self.assertEqual(d.getMaintenanceHoursBetween(new_id), hours_between)
            self.assertEqual(d.getMaintenanceDescription(new_id), description)

            hours_between = random_between(5, 10)
            description = random_string(50)
            d.setMaintenanceHoursBetween(x, hours_between)
            d.setMaintenanceDescription(x, description)
            self.assertEqual(d.getMaintenanceHoursBetween(new_id), hours_between)
            self.assertEqual(d.getMaintenanceDescription(new_id), description)

        # check removal
        for x in range(MAINTENANCES):
            d.removeMaintenance(x)
            self.assertEqual(MAINTENANCES - x - 1, len(d.listMaintenances()))
            d.removeMaintenance(x)
            self.assertEqual(MAINTENANCES - x - 1, len(d.listMaintenances()))

        self.assertEqual(len(d.listMaintenances()), 0)

        # check double add
        d.addMaintenance(maintenance_id=0, description="WHAT", hours_between=10)
        with self.assertRaises(DuplicatedIdException):
            d.addMaintenance(
                maintenance_id=0, description="YOU AGAIN", hours_between=10
            )

    def test_machine_maintenance_interaction(self):
        d = self.initDatabase()

        MACHINE_TYPE = "drill"
        MACHINES = 3
        # create simple machine types
        d.addMachineType(type_id=0, type_name=MACHINE_TYPE)

        # create simple machine
        for x in range(MACHINES):
            d.addMachine(x, f"TEST{x}", 0, 0)

        # create simple maintenances
        MAINTENANCES_DESC = ["change oil", "clean mirror", "empty bin"]
        for i, m in enumerate(MAINTENANCES_DESC):
            d.addMaintenance(maintenance_id=i, description=m, hours_between=10)
            d.addMachineMaintenance(i, i)
            self.assertEqual(len(d.getMachineMaintenances(i)), 1)
            self.assertEqual(d.getMachineMaintenances(i)[0].maintenance_id, i)
            self.assertEqual(
                d.getMachineMaintenances(i)[0].description, MAINTENANCES_DESC[i]
            )

        # remove maintenances from machines
        for x in range(MACHINES):
            d.removeMachineMaintenance(x, x)
            self.assertEqual(len(d.getMachineMaintenances(x)), 0)

        # remove maintenances
        for i in range(len(MAINTENANCES_DESC)):
            d.removeMaintenance(i)
            self.assertEqual(len(d.listMaintenances()), len(MAINTENANCES_DESC) - i - 1)
        # check that everything was removed
        self.assertEqual(len(d.listMaintenances()), 0)

    def test_missing_query(self):
        d = self.initDatabase()

        with self.assertRaises(InvalidQueryValueException):
            d.getUser(user_id=0)

        with self.assertRaises(InvalidQueryValueException):
            d.getMachineType(type_id=0)

        with self.assertRaises(InvalidQueryValueException):
            d.getRole(role_id=0)

        with self.assertRaises(InvalidQueryValueException):
            d.getMaintenance(maintenance_id=0)

        with self.assertRaises(InvalidQueryValueException):
            d.getMachine(machine_id=0)


if __name__ == "__main__":
    unittest.main()
