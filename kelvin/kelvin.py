from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QMainWindow, QGridLayout, QHBoxLayout, QPushButton
from PyQt5.QtGui import QFont, QDoubleValidator, QValidator
from PyQt5.QtCore import Qt

import json
import os

class TextBox(QWidget):
    """This widget provides a label above a LineEdit for design reasons"""
    def __init__(self, hint: str, text: str):
        super().__init__()

        label = QLabel(hint)

        font = label.font() #type: QFont
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

    def __init__(self):
        super().__init__()

        base_dir = os.path.dirname(__file__)
        config_path = os.path.join(base_dir, 'temperature.config.json')

        with open(config_path, 'r') as fil:
            self.DEVICES = json.load(fil)

        self.setWindowTitle('Kelvin')

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        grid = QGridLayout()
        layout.addLayout(grid)
        layout.addStretch()

        hbox = QHBoxLayout()
        hbox.addStretch()

        button = QPushButton('apply')
        button.pressed.connect(self.apply)

        hbox.addWidget(button)
        layout.addLayout(hbox)

        for index, device in enumerate(self.DEVICES):
            temperature_input = TextBox('Temperature (K)', '20.0')
            temperature_input.set_validator(QDoubleValidator())

            rate_input = TextBox('Rate (K / min)', '2.0')
            rate_input.set_validator(QDoubleValidator())

            device['temperature_input'] = temperature_input
            device['rate_input'] = rate_input

            label = QLabel(device['long_name'] + '\n')
            label.setAlignment(Qt.AlignRight | Qt.AlignBottom)

            grid.addWidget(label, index, 0)
            grid.addWidget(temperature_input, index, 1)
            grid.addWidget(rate_input, index, 2)

    def apply(self):
        result_dict = {}
        for device in self.DEVICES:
            temperature = float(device['temperature_input'].text)
            rate = float(device['rate_input'].text)

            result_dict[device['short_name']] = {'T': temperature, 'rate': rate}

        print(result_dict)


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    from sys import argv
    
    app = QApplication(argv)

    text_box = MainApp()

    text_box.show()

    exit(app.exec_())
