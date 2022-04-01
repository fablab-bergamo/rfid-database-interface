import unittest

from time import time
from string import ascii_uppercase
from random import choices, randint, random

from database import (
    Database,
    DuplicatedIdException,
    InvalidIdException,
    InvalidQueryException,
)


def random_string(k=16):
    return "".join(choices(ascii_uppercase, k=k))


def random_between(a, b):
    return random() * (b - a) + 1


class TestDB(unittest.TestCase):
    def initDatabase(self):
        d = Database("test_settings.toml")
        d.dropDatabase()
        return Database("test_settings.toml")

    def populateSimpleDatabase(self, ids=0, timestamp=2000000000.0000):
        d = Database("test_settings.toml")
        d.dropDatabase()
        d = Database("test_settings.toml")

        d.addMachineType(type_id=ids, type_name="drill")
        d.addRole(role_id=ids, role_name="admin")
        d.addUser(name="Mario", surname="Rossi", role_id=ids)
        d.addMachine(machine_id=0, machine_name="DRILL0", machine_type=ids)
        d.addMaintenance(
            maintenance_id=ids, hours_between=10, description="replace engine"
        )
        d.addMaintenance(
            maintenance_id=ids + 1, hours_between=10, description="replace brushes"
        )
        d.addIntervention(
            maintenance_id=ids,
            user_id=ids,
            machine_id=ids,
            timestamp=timestamp,
        )
        return d

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

    def test_types(self):
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

        # test get machine type
        with self.assertRaises(InvalidIdException):
            d.getMachineType(10)

    def test_users(self):
        d = self.initDatabase()
        d.addRole(0, "admin")

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
            user_id = d.addUser(n, s, 0)
            self.assertEqual(d.getUserId(n, s), user_id)
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

        # add another user
        d.addUser(name="Andrea", surname="Bianchi", role_id=0, user_id=0)
        # test get id
        user_id = d.getUserId(name="Andrea", surname="Bianchi")
        self.assertEqual(user_id, 0)

        # test  invalid name
        with self.assertRaises(InvalidQueryException):
            d.getUserId(name="Mario", surname="Rossi")

        # test invalid role
        with self.assertRaises(InvalidIdException):
            d.addUser(name="Mario", surname="Rossi", role_id=10)

        # test invalid id
        with self.assertRaises(DuplicatedIdException):
            d.addUser(name="Mario", surname="Rossi", role_id=0, user_id=0)
        with self.assertRaises(InvalidIdException):
            d.getUser(10)
        with self.assertRaises(InvalidIdException):
            d.getUserCardUUID(10)

    def test_roles(self):
        d = self.initDatabase()
        d.addRole(0, "admin")
        d.addRole(1, "user")

        user_id = d.addUser(name="Mario", surname="Rossi", role_id=0)
        d.setUserRole(user_id=user_id, role_id=1)
        self.assertEqual(d.getUserRole(user_id=user_id).role_id, 1)

        with self.assertRaises(InvalidIdException):
            d.setUserRole(user_id=user_id, role_id=4)

        with self.assertRaises(InvalidIdException):
            d.getUserRole(user_id=10)

        with self.assertRaises(InvalidIdException):
            d.getRole(10)

    def test_set_authorizations(self):
        d = self.populateSimpleDatabase()
        d.setUserAuthorization(0, [0])
        authorization_ids = [t.type_id for t in d.getUserAuthorization(0)]
        self.assertListEqual(authorization_ids, [0])

        # test invalid authorization
        with self.assertRaises(InvalidQueryException):
            d.setUserAuthorization(0, 0)
        with self.assertRaises(InvalidIdException):
            d.setUserAuthorization(0, [10, 20])
        # test invalid user id
        with self.assertRaises(InvalidIdException):
            d.getUserAuthorization(10)

    def test_long_add_users(self):
        d = self.initDatabase()

        USERS = 100
        name = "Mario"
        surname = "Rossi"

        d.addRole(0, "admin")

        for _ in range(USERS):
            d.addUser(name, surname, 0)
        self.assertEqual(len(d.listUsers()), USERS)

    def test_machines(self):
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
                d.addMachine(
                    machine_id=current_id,
                    machine_name=name,
                    machine_type=i,
                )
                current_id += 1

        # test that they have been added
        self.assertEqual(MACHINES * TYPES, len(d.listMachines()))

        for current_id in range(MACHINES * TYPES):
            self.assertEqual(d.getMachine(current_id).machine_id, current_id)
            hours = random_between(10, 1000)
            d.setMachinesHours(current_id, hours)
            self.assertEqual(d.getMachineHours(current_id), hours)

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

        # test invalid machine types
        with self.assertRaises(InvalidQueryException):
            d.addMachine(0, "", 10)

        d.addMachine(machine_id=0, machine_name="drill", machine_type=0)
        # test invalid machine id
        with self.assertRaises(DuplicatedIdException):
            d.addMachine(machine_id=0, machine_name="drill", machine_type=0)
        with self.assertRaises(InvalidIdException):
            d.getMachine(machine_id=10)
        with self.assertRaises(InvalidIdException):
            d.getMachineHours(machine_id=10)
        with self.assertRaises(InvalidIdException):
            d.getMachineMachineType(machine_id=10)
        with self.assertRaises(InvalidIdException):
            d.setMachineMachineType(machine_id=10, machine_type=10)
        with self.assertRaises(InvalidIdException):
            d.getMachineName(machine_id=10)

    def test_maintenances(self):
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

        # check get
        self.assertEqual(d.getMaintenance(maintenance_id=0).maintenance_id, 0)

        # check removal
        for x in range(MAINTENANCES):
            d.removeMaintenance(x)
            self.assertEqual(MAINTENANCES - x - 1, len(d.listMaintenances()))
            d.removeMaintenance(x)
            self.assertEqual(MAINTENANCES - x - 1, len(d.listMaintenances()))

        self.assertEqual(len(d.listMaintenances()), 0)

        # check invalid ids
        with self.assertRaises(InvalidIdException):
            d.getMaintenance(maintenance_id=10)
        with self.assertRaises(InvalidIdException):
            d.getMaintenanceDescription(maintenance_id=10)
        with self.assertRaises(InvalidIdException):
            d.getMaintenanceHoursBetween(maintenance_id=10)

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

        d.addMaintenance(hours_between=10, description="test", maintenance_id=0)
        # test invalid ids
        with self.assertRaises(InvalidIdException):
            d.addMachineMaintenance(machine_id=0, maintenance_id=10)
        with self.assertRaises(InvalidIdException):
            d.addMachineMaintenance(machine_id=10, maintenance_id=0)
        with self.assertRaises(InvalidIdException):
            d.getMachineMaintenances(machine_id=10)
        with self.assertRaises(InvalidIdException):
            d.removeMachineMaintenance(machine_id=10, maintenance_id=0)
        with self.assertRaises(InvalidIdException):
            d.removeMachineMaintenance(machine_id=0, maintenance_id=10)

        # test remove maintenance that's nto present
        with self.assertRaises(InvalidIdException):
            d.removeMachineMaintenance(machine_id=0, maintenance_id=0)

    def test_machine_multiple_maintenances(self):
        # test multiple maintenances in machine
        d = self.populateSimpleDatabase()
        d.addMachineMaintenance(0, 0)
        self.assertEqual(len(d.getMachineMaintenances(0)), 1)
        d.addMachineMaintenance(0, 1)
        self.assertEqual(len(d.getMachineMaintenances(0)), 2)
        maintenance_ids = [m.maintenance_id for m in d.getMachineMaintenances(0)]
        self.assertListEqual(maintenance_ids, [0, 1])
        d.removeMachineMaintenance(0, 0)
        self.assertEqual(len(d.getMachineMaintenances(0)), 1)

    def test_interventions(self):
        d = self.populateSimpleDatabase(ids=0, timestamp=time())

        intervention_id = d.addIntervention(maintenance_id=0, user_id=0, machine_id=0)

        # test get set
        self.assertEqual(intervention_id, len(d.listInterventions()) - 1)
        self.assertEqual(d.getInterventionUser(0).user_id, 0)
        self.assertEqual(d.getInterventionMachine(0).machine_id, 0)
        self.assertAlmostEqual(d.getInterventionTimestamp(0), time(), delta=1000)
        self.assertEqual(
            d.getIntervention(intervention_id=intervention_id).intervention_id,
            intervention_id,
        )

        # test invalid ids
        with self.assertRaises(InvalidIdException):
            d.addIntervention(maintenance_id=10, machine_id=0, user_id=0)
        with self.assertRaises(InvalidIdException):
            d.addIntervention(maintenance_id=0, machine_id=10, user_id=0)
        with self.assertRaises(InvalidIdException):
            d.addIntervention(maintenance_id=0, machine_id=0, user_id=10)
        with self.assertRaises(InvalidIdException):
            d.getIntervention(intervention_id=10)
        with self.assertRaises(InvalidIdException):
            d.getInterventionUser(intervention_id=10)
        with self.assertRaises(InvalidIdException):
            d.getInterventionMachine(intervention_id=10)
        with self.assertRaises(InvalidIdException):
            d.getInterventionTimestamp(intervention_id=10)

    def test_entity_deserialize(self):
        pass


if __name__ == "__main__":
    unittest.main()
