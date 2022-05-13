from mqtt import MQTTInterface
from time import sleep


def machineAlive(machine: str):
    print(f"Machine {machine} is still alive")


def machineConnected(machine: str):
    print(f"Machine {machine} is connected")


def main():
    m = MQTTInterface()
    m.setMachineAliveCallback(machineAlive)
    m.setMachineConnectedCallback(machineConnected)

    m.connect()

    while m.connected:
        sleep(0.01)

    m.unsubscribe()
    m.disconnect()


if __name__ == "__main__":
    main()
