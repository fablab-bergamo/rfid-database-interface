from mqtt import MQTTInterface
from database import DatabaseInterface
from time import sleep, time


class Backend:
    def __init__(self):
        self._m = MQTTInterface()
        self._m.setMachineAliveCallback(self.machineAlive)
        self._m.isMachicineAuthorizedCallback(self.isMachineAuthorized)

        self._db = DatabaseInterface()
        self._last_alive = {}

    def machineAlive(self, machine_id: str):
        self._last_alive[machine_id] = time()

    def isMachineAuthorized(self, machine_id: str):
        pass

    def connect(self):
        self._m.connect()

    def disconnect(self):
        self._m.disconnect()


def main():
    b = Backend()
    b.connect()

    while True:
        sleep(1)


if __name__ == "__main__":
    main()
