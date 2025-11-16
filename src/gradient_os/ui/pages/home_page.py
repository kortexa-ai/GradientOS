from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QPushButton, QGroupBox, QHBoxLayout, QLineEdit, QMessageBox

from gradient_os.ui.widgets import set_label_text


class HomePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(main_layout)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(5)
        title_label = QLabel("Industrial Robot Controller")
        title_label.setObjectName("TitleMain")
        title_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title_label)
        robot_label = QLabel("Robot: Gradient Zero")
        robot_label.setObjectName("TitleRobot")
        robot_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(robot_label)
        main_layout.addLayout(title_layout)

        main_layout.addSpacing(30)

        button_grid = QGridLayout()
        button_grid.setSpacing(15)
        control_btn = QPushButton("Joint Control")
        control_btn.clicked.connect(self.parent.switch_to_control)
        real_control_btn = QPushButton("Real Robot Control")
        real_control_btn.clicked.connect(self.parent.switch_to_real_control)
        calib_btn = QPushButton("Calibration")
        calib_btn.clicked.connect(self.parent.switch_to_calibration)
        tut_btn = QPushButton("Tutorials & Docs")
        tut_btn.clicked.connect(self.parent.switch_to_tutorials)
        button_grid.addWidget(control_btn, 0, 0)
        button_grid.addWidget(real_control_btn, 0, 1)
        button_grid.addWidget(calib_btn, 1, 0)
        button_grid.addWidget(tut_btn, 1, 1)
        main_layout.addLayout(button_grid)

        ip_group = QGroupBox("Robot Connection")
        ip_layout = QHBoxLayout()
        ip_label = QLabel("IP/Hostname:")
        self.ip_input = QLineEdit(self.parent.PI_IP)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_ip_from_input)
        self.current_ip_label = QLabel(f"Current target: {self.parent.PI_IP}")
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_input)
        ip_layout.addWidget(save_btn)
        ip_layout.addWidget(self.current_ip_label)
        ip_group.setLayout(ip_layout)
        main_layout.addWidget(ip_group)

    def save_ip_from_input(self):
        new_ip = self.ip_input.text().strip()
        if not new_ip:
            QMessageBox.warning(self, "Invalid Address", "Please enter a valid IP address or hostname.")
            return
        self.parent.update_pi_ip(new_ip)
        set_label_text(self.current_ip_label, f"Current target: {self.parent.PI_IP}")


