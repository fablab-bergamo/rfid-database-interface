import unittest
from database import Database, DuplicatedIdException


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
        UUID = "AAAAAAAAA-BBBBBBBBBBB-C"
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
        # TODO


if __name__ == "__main__":
    unittest.main()
