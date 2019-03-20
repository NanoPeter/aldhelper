from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
)
from PyQt5.QtGui import QFont, QDoubleValidator, QValidator
from PyQt5.QtCore import Qt

from paho.mqtt.client import Client as MQTTClient

import json
import os


class TextBox(QWidget):
    """This widget provides a label above a LineEdit for design reasons"""

    def __init__(self, hint: str, text: str):
        super().__init__()

        label = QLabel(hint)

        font = label.font()  # type: QFont
        font.setPointSize(10)

        label.setFont(font)

        self._line_edit = QLineEdit()
        self._line_edit.setText(text)

        layout = QVBoxLayout()

        layout.addWidget(label)
        layout.addWidget(self._line_edit)
        layout.addStretch()

        self.setLayout(layout)

    @property
    def text(self):
        return self._line_edit.text()

    def set_validator(self, validator: QValidator):
        self._line_edit.setValidator(validator)


class MainApp(QMainWindow):

    TEMPERATURE_STRING = 'Temperature (K)'
    TEMPERATURE_DEFAULT = '20.0'

    RATE_STRING = 'Rate (K / min)'
    RATE_DEFAULT = '2.0'

    CONFIG_FILE_NAME = 'temperature.config.json'

    CREDENTIALS_FILE_NAME = 'credentials.json'

    TOPIC_SET_T = 'ald/temperature/set/temperature'
    TOPIC_GET_T = 'ald/temperature/+'

    def __init__(self):
        super().__init__()

        self._init_gui()
        self._load_devices()
        self._connect_to_mqtt()

    def _connect_to_mqtt(self):
        base_dir = os.path.dirname(__file__)
        config_path = os.path.join(base_dir, self.CREDENTIALS_FILE_NAME)

        with open(config_path, 'r') as fil:
            credentials = json.load(fil)

        self._mqtt = MQTTClient()
        self._mqtt.on_connect = self.mqtt_connected
        self._mqtt.username_pw_set(credentials['user'], credentials['password'])
        self._mqtt.connect(credentials['host'], credentials['port'], 60)

        self._mqtt.loop_start()


    def _init_gui(self):
        self.setWindowTitle("Kelvin")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        self._grid = QGridLayout()
        layout.addLayout(self._grid)

        layout.addStretch()

        hbox = QHBoxLayout()
        hbox.addStretch()

        button = QPushButton("apply")
        button.pressed.connect(self.apply)

        hbox.addWidget(button)
        layout.addLayout(hbox)

    def _load_devices(self):

        base_dir = os.path.dirname(__file__)
        config_path = os.path.join(base_dir, self.CONFIG_FILE_NAME)

        with open(config_path, 'r') as fil:
            self.DEVICES = json.load(fil)

        for index, device in enumerate(self.DEVICES):
            temperature_input = TextBox(self.TEMPERATURE_STRING, self.TEMPERATURE_DEFAULT)
            temperature_validator = QDoubleValidator(0, device['maximum_temperature'], 1)
            temperature_input.set_validator(temperature_validator)

            rate_input = TextBox(self.RATE_STRING, self.RATE_DEFAULT)
            rate_validator = QDoubleValidator(0, device['maximum_rate'], 1)
            rate_input.set_validator(rate_validator)

            device["temperature_input"] = temperature_input
            device["rate_input"] = rate_input

            label = QLabel(device["long_name"] + "\n")
            label.setAlignment(Qt.AlignRight | Qt.AlignBottom)

            self._grid.addWidget(label, index, 0)
            self._grid.addWidget(temperature_input, index, 1)
            self._grid.addWidget(rate_input, index, 2)

    def mqtt_connected(self, client, *args, **kwargs):
        client.subscribe(self.TOPIC_GET_T)
        client.message_callback_add(self.TOPIC_GET_T, self.temperature_received)


    def temperature_received(self, client, userdata, msg):
        print(msg)


    def apply(self):
        result_dict = {}
        for device in self.DEVICES:
            temperature = float(device["temperature_input"].text)
            rate = float(device["rate_input"].text)

            result_dict[device["short_name"]] = {"T": temperature, "rate": rate}

        self._mqtt.publish(self.TOPIC_SET_T, json.dumps(result_dict))


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from sys import argv

    app = QApplication(argv)

    text_box = MainApp()

    text_box.show()

    exit(app.exec_())
