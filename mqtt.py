import paho.mqtt.client as mqtt
import toml


class MQTTInterface:
    def __init__(self, path="settings.toml"):
        self._settings_path = path

        self._messageCallback = None
        self._isMachineAuthorizedCallback = None
        self._machineAliveCallback = None
        self._connected = False

        self._awaiting_authorization = set()
        self._machineAlive = {}

        self._loadSettings()

    def _loadSettings(self) -> None:
        settings = toml.load(self._settings_path)["MQTT"]
        self._broker = settings["broker"]
        self._port = settings["port"]
        self._client_id = settings["client_id"]
        self._topic = settings["topic"]
        self._connect_message = settings["connect_message"]
        self._alive_message = settings["alive_message"]

    def _extractMachineFromTopic(self, topic: str) -> str:
        if not topic.startswith(self._topic[:-1]):
            return None

        return topic.split("/")[-1:][0]

    def _onMessage(self, *args):
        topic = args[2].topic
        message = args[2].payload.decode("utf-8")

        if self._messageCallback is not None:
            self._messageCallback(topic, message)

        machine = self._extractMachineFromTopic(topic)
        if not machine:
            return

        match message:
            case self._connect_message:
                self._awaiting_authorization.add(machine)
                if self._isMachineAuthorizedCallback is not None:
                    self._isMachineAuthorizedCallback(machine)

            case self._alive_message:
                if self._machineAliveCallback is not None:
                    self._machineAliveCallback(machine)

    def _onDisconnect(self, *args):
        self._connected = False

    def connect(self):
        self._client = mqtt.Client(self._client_id)
        self._client.on_message = self._onMessage
        self._client.on_disconnect = self._onDisconnect

        self._client.connect(self._broker, port=self._port)
        self._connected = True
        self._client.subscribe(self._topic)
        self._client.loop_start()

    def setMessageCallback(self, callback: callable):
        self._messageCallback = callback

    def isMachineAuthorizedCallback(self, callback: callable):
        self._isMachineAuthorizedCallback = callback

    def setMachineAliveCallback(self, callback: callable):
        self._machineAliveCallback = callback

    def disconnect(self):
        self._client.unsubscribe(self._topic)
        self._client.loop_stop()
        self._client.disconnect()

    @property
    def connected(self):
        return self._connected
