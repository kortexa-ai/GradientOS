from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QLineEdit,
    QMessageBox, QGroupBox, QGridLayout, QCheckBox
)


class CalibrationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        layout = QVBoxLayout()

        label = QLabel("Calibration Tools")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        warning_label = QLabel("Warning: Use with caution! Backup configurations before proceeding.")
        warning_label.setProperty("role", "warning")
        layout.addWidget(warning_label)

        # Calibration
        calib_hbox = QHBoxLayout()
        calib_label = QLabel("CALIBRATE id")
        self.calib_input = QLineEdit("10")
        calib_btn = QPushButton("Calibrate")
        calib_btn.clicked.connect(self.send_calibrate)
        calib_hbox.addWidget(calib_label)
        calib_hbox.addWidget(self.calib_input)
        calib_hbox.addWidget(calib_btn)
        layout.addLayout(calib_hbox)

        # Set Zero
        set_zero_hbox = QHBoxLayout()
        set_zero_label = QLabel("SET_ZERO joint#")
        self.set_zero_input = QLineEdit("1")
        self.set_zero_input.setToolTip("Enter 1-6 for arm joints, 7 for the gripper.")
        set_zero_btn = QPushButton("Set Zero")
        set_zero_btn.clicked.connect(self.send_set_zero)
        set_zero_hbox.addWidget(set_zero_label)
        set_zero_hbox.addWidget(self.set_zero_input)
        set_zero_hbox.addWidget(set_zero_btn)
        layout.addLayout(set_zero_hbox)

        # Factory Reset
        factory_reset_hbox = QHBoxLayout()
        factory_reset_label = QLabel("FACTORY_RESET id")
        self.factory_reset_input = QLineEdit("10")
        factory_reset_btn = QPushButton("Factory Reset")
        factory_reset_btn.clicked.connect(self.send_factory_reset)
        factory_reset_hbox.addWidget(factory_reset_label)
        factory_reset_hbox.addWidget(self.factory_reset_input)
        factory_reset_hbox.addWidget(factory_reset_btn)
        layout.addLayout(factory_reset_hbox)

        # PID Tuning Section
        pid_group = QGroupBox("PID Tuning (Open-Loop)")
        pid_layout = QGridLayout()
        # Per-joint tuning inputs
        pid_layout.addWidget(QLabel("Joint (1-6):"), 0, 0)
        self.tune_joint_input = QLineEdit("1")
        pid_layout.addWidget(self.tune_joint_input, 0, 1)
        pid_layout.addWidget(QLabel("Amplitude (deg):"), 0, 2)
        self.tune_amp_input = QLineEdit("10.0")
        pid_layout.addWidget(self.tune_amp_input, 0, 3)
        pid_layout.addWidget(QLabel("Freq (Hz):"), 1, 0)
        self.tune_freq_input = QLineEdit("100")
        pid_layout.addWidget(self.tune_freq_input, 1, 1)
        pid_layout.addWidget(QLabel("Duration (s):"), 1, 2)
        self.tune_dur_input = QLineEdit("3.0")
        pid_layout.addWidget(self.tune_dur_input, 1, 3)
        self.tune_move_zero_chk = QCheckBox("Move to zero before test")
        self.tune_move_zero_chk.setChecked(True)
        pid_layout.addWidget(self.tune_move_zero_chk, 2, 0, 1, 2)
        tune_joint_btn = QPushButton("Tune Selected Joint")
        tune_joint_btn.clicked.connect(self.send_tune_pid_joint)
        pid_layout.addWidget(tune_joint_btn, 2, 2, 1, 2)

        # All joints tuning
        pid_layout.addWidget(QLabel("All Joints:"), 3, 0)
        self.tune_all_amp = QLineEdit("10.0")
        pid_layout.addWidget(self.tune_all_amp, 3, 1)
        self.tune_all_freq = QLineEdit("100")
        pid_layout.addWidget(self.tune_all_freq, 3, 2)
        self.tune_all_dur = QLineEdit("3.0")
        pid_layout.addWidget(self.tune_all_dur, 3, 3)
        self.tune_all_move_zero_chk = QCheckBox("Zero before each joint")
        self.tune_all_move_zero_chk.setChecked(True)
        pid_layout.addWidget(self.tune_all_move_zero_chk, 4, 0, 1, 2)
        tune_all_btn = QPushButton("Tune All Joints")
        tune_all_btn.clicked.connect(self.send_tune_pid_all)
        pid_layout.addWidget(tune_all_btn, 4, 2, 1, 2)

        pid_group.setLayout(pid_layout)
        layout.addWidget(pid_group)

        self.setLayout(layout)

    def log_message(self, msg: str):
        try:
            self.parent.status_label_footer.setText(msg)
        except Exception:
            pass

    def send_calibrate(self):
        id_str = self.calib_input.text()
        self.parent.send_command(f"CALIBRATE,{id_str}")

    def send_set_zero(self):
        joint = self.set_zero_input.text()
        self.parent.send_command(f"SET_ZERO,{joint}")

    def send_factory_reset(self):
        id_str = self.factory_reset_input.text()
        reply = QMessageBox.question(self, 'Confirm Factory Reset', 'Are you sure? This resets the servo to factory defaults.', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.parent.send_command(f"FACTORY_RESET,{id_str}")

    def send_tune_pid_joint(self):
        try:
            def _p_float(s: str, default: float) -> float:
                try:
                    return float(s.strip())
                except Exception:
                    return default
            def _p_int(s: str, default: int) -> int:
                try:
                    return int(float(s.strip()))
                except Exception:
                    return default

            j = _p_int(self.tune_joint_input.text(), 1)
            if j < 1: j = 1
            if j > 6: j = 6
            amp = _p_float(self.tune_amp_input.text(), 10.0)
            freq = _p_float(self.tune_freq_input.text(), 100.0)
            if freq <= 0: freq = 100.0
            dur = _p_float(self.tune_dur_input.text(), 3.0)
            if dur <= 0: dur = 3.0
            move_zero = self.tune_move_zero_chk.isChecked()
            cmd = f"TUNE_PID_JOINT,{j},{amp},{freq},{dur},{str(move_zero).lower()}"
            self.parent.send_command(cmd)
            try:
                self.parent.status_label_footer.setText(f"Sent: {cmd}")
            except Exception:
                pass
        except Exception as e:
            QMessageBox.warning(self, "Input Error", f"Invalid PID tuning inputs for joint.\n{e}")

    def send_tune_pid_all(self):
        try:
            def _p_float(s: str, default: float) -> float:
                try:
                    return float(s.strip())
                except Exception:
                    return default
            amp = _p_float(self.tune_all_amp.text(), 10.0)
            freq = _p_float(self.tune_all_freq.text(), 100.0)
            if freq <= 0: freq = 100.0
            dur = _p_float(self.tune_all_dur.text(), 3.0)
            if dur <= 0: dur = 3.0
            move_zero_each = self.tune_all_move_zero_chk.isChecked()
            cmd = f"TUNE_PID_ALL,{amp},{freq},{dur},{str(move_zero_each).lower()}"
            self.parent.send_command(cmd)
            try:
                self.parent.status_label_footer.setText(f"Sent: {cmd}")
            except Exception:
                pass
        except Exception as e:
            QMessageBox.warning(self, "Input Error", f"Invalid PID tuning inputs for all joints.\n{e}")


