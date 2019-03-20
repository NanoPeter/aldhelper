from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QSystemTrayIcon,
    QStyle,
    QMenu,
    QAction,
    qApp
)
from PyQt5.QtGui import QFont, QDoubleValidator, QValidator, QIcon
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

class StateWidget(QWidget):

    def __init__(self):
        super().__init__()
        layout = QGridLayout()
        self.setLayout(layout)
        
        self._tsp_label = QLabel()
        font = self._tsp_label.font()
        font.setPointSize(10)
        self._tsp_label.setFont(font)
        
        self._wsp_label = QLabel()
        self._wsp_label.setFont(font)
        
        self._power_label = QLabel()
        self._power_label.setFont(font)

        self._temperature_label = QLabel()
        self._temperature_label.setFont(font)
        
        layout.addWidget(self._tsp_label, 0, 0)
        layout.addWidget(self._wsp_label, 1, 0)
        layout.addWidget(self._power_label, 0, 1)
        layout.addWidget(self._temperature_label, 1, 1)
        
        
    def set_tsp(self, value):
        self._tsp_label.setText('T:{value:0.1f} °C'.format(value=value))
        
    def set_wsp(self, value):
        self._wsp_label.setText('W:{value:0.1f} °C'.format(value=value))
        
    def set_power(self, value):
        self._power_label.setText('{value:0.1f} %'.format(value=value))
        
    def set_temperature(self, value):
        self._temperature_label.setText('C:{value:0.1f} °C'.format(value=value))


class MainApp(QMainWindow):

    TEMPERATURE_STRING = 'Temperature (K)'
    TEMPERATURE_DEFAULT = '20.0'

    RATE_STRING = 'Rate (K / min)'
    RATE_DEFAULT = '2.0'

    CONFIG_FILE_NAME = 'temperature.config.json'
    ICON_FILE_NAME = 'temperature_symbol.png'
    CREDENTIALS_FILE_NAME = 'credentials.json'

    TOPIC_SET_T = 'ald/temperature/set/temperature'
    TOPIC_GET_T = 'ald/temperature/+'
    
    WINDOW_TITLE = "Kelvin"

    def __init__(self):
        super().__init__()

        self._init_system_tray()
        self._init_gui()
        self._load_devices()
        self._connect_to_mqtt()

    def get_path(self, file_name):
        base_dir = os.path.dirname(__file__)
        path = os.path.join(base_dir, file_name)

        return path        

    def _init_system_tray(self):
        
        icon_path = self.get_path(self.ICON_FILE_NAME)

        icon = QIcon(icon_path)

        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
    
        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(qApp.quit)
    
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(icon)
        
        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self._tray.setContextMenu(tray_menu)
        
        self._tray.show()
        

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self._tray.showMessage(
            self.WINDOW_TITLE,
            "Application was minimized to Tray",
            QSystemTrayIcon.Information,
            2000
        )
    

    def _connect_to_mqtt(self):
        credentials_path = self.get_path(self.CREDENTIALS_FILE_NAME)

        if not os.path.exists(credentials_path):
            self._button.setDisabled(True)
            return

        with open(credentials_path, 'r') as fil:
            credentials = json.load(fil)

        self._mqtt = MQTTClient()
        self._mqtt.on_connect = self.mqtt_connected
        self._mqtt.username_pw_set(credentials['user'], credentials['password'])
        self._mqtt.connect(credentials['host'], credentials['port'], 60)

        self._mqtt.loop_start()


    def _init_gui(self):
        self.setWindowTitle(self.WINDOW_TITLE)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        self._grid = QGridLayout()
        layout.addLayout(self._grid)

        layout.addStretch()

        hbox = QHBoxLayout()
        hbox.addStretch()

        self._button = QPushButton("apply")
        self._button.pressed.connect(self.apply)

        hbox.addWidget(self._button)
        layout.addLayout(hbox)

    def _load_devices(self):
        config_path = self.get_path(self.CONFIG_FILE_NAME)

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
            
            detail_widget = StateWidget()
            device['detail_widget'] = detail_widget
            
            self._grid.addWidget(label, index, 0)
            self._grid.addWidget(temperature_input, index, 1)
            self._grid.addWidget(rate_input, index, 2)
            self._grid.addWidget(detail_widget, index, 3)

    def mqtt_connected(self, client, *args, **kwargs):
        client.subscribe(self.TOPIC_GET_T)
        client.message_callback_add(self.TOPIC_GET_T, self.temperature_received)


    def temperature_received(self, client, userdata, msg):
        sensor = msg.topic.split('/')[-1]
        data = json.loads(msg.payload.decode('utf-8'))
        
        for device in self.DEVICES:
            if device['short_name'] == sensor:
                device['detail_widget'].set_tsp(data['tsp'])
                device['detail_widget'].set_wsp(data['wsp'])
                device['detail_widget'].set_power(data['power'])
                device['detail_widget'].set_temperature(data['temperature'])
                
                break
        
        #print(sensor, data)



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
