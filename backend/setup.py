from database import Database
from string import ascii_uppercase
from random import choice, randint, shuffle


def random_string(chars=25):
    return "".join(choice(ascii_uppercase) for _ in range(chars))


def main():
    names = [
        "Alessandro",
        "Lorenzo",
        "Diego",
        "Tommaso",
        "Riccardo",
        "Matteo",
        "Giovanni",
        "Leonardo",
        "Gabriele",
        "Edoardo",
    ]
    surnames = [
        "Rossi",
        "Bianchi",
        "Verdi",
        "Colombo",
        "Fumagalli",
        "Brambilla",
        "Ferrari",
        "Gallo",
        "Russo",
        "Costa",
    ]

    authorizations = {0: 4, 1: 1, 2: 1}

    d = Database()

    d.addRole(2, "admin")
    d.addRole(1, "crew")
    d.addRole(0, "user")

    d.addMachineType(0, "3D printer")
    d.addMachineType(1, "laser cutter")
    d.addMachineType(2, "column drill")
    d.addMachineType(3, "lathe")

    machine_ids = [m.type_id for m in d.listMachineTypes()]
    # machine_names = [m.type_name for m in d.listMachineTypes()]

    for role_id, numbers in authorizations.items():
        for _ in range(numbers):
            name = choice(names)
            surname = choice(surnames)

            user_id = d.addUser(name, surname, role_id)
            d.setUserCardUUID(card_UUID=random_string(), user_id=user_id)
            auth = [x for x in machine_ids]

            if role_id == 0:

                auth_num = randint(1, 3)
                shuffle(auth)

                d.setUserAuthorization(
                    user_id=user_id, authorization_ids=auth[:auth_num]
                )
            else:
                d.setUserAuthorization(user_id=user_id, authorization_ids=auth)

    for _ in range(10):
        machine_type = choice(machine_ids)
        machine_name = random_string(5)
        machine_id = randint(10000, 999999)
        d.addMachine(
            machine_id=machine_id, machine_name=machine_name, machine_type=machine_type
        )

    print(d.listRoles())
    print(d.listMachineTypes())
    print(d.listUsers())
    print(d.listMachines())


if __name__ == "__main__":
    main()
