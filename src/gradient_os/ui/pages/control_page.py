from functools import partial
import time
import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QGridLayout,
    QGroupBox, QSlider, QLineEdit, QButtonGroup, QPlainTextEdit, QMessageBox
)

from gradient_os.ui.constants import POS_HOME, POS_REST, JOINT_NAMES, JOINT_JOG_STEPS_DEG
from gradient_os.ui.widgets import set_label_text


class ControlPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        layout = QVBoxLayout()

        label = QLabel("Joint Control")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.status_label = QLabel("ROBOT CONTROL IS LIVE")
        self.status_label.setObjectName("LiveStatus")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.hide()
        self.status_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self.status_label)

        # --- Live Control Buttons ---
        control_button_layout = QHBoxLayout()
        self.activate_btn = QPushButton("ACTIVATE LIVE CONTROL")
        self.activate_btn.setObjectName("ActivateBtn")
        self.activate_btn.clicked.connect(self.activate_live_control)
        control_button_layout.addWidget(self.activate_btn)

        self.deactivate_btn = QPushButton("DEACTIVATE")
        self.deactivate_btn.setObjectName("DeactivateBtn")
        self.deactivate_btn.clicked.connect(self.deactivate_live_control)
        self.deactivate_btn.setEnabled(False)
        control_button_layout.addWidget(self.deactivate_btn)
        layout.addLayout(control_button_layout)

        self.joints = JOINT_NAMES
        self.sliders = {}
        self.value_labels = {}

        # Create a grid to hold all joint controls, two per row
        sliders_grid = QGridLayout()
        sliders_grid.setHorizontalSpacing(15)
        sliders_grid.setVerticalSpacing(0)

        for i, joint_name in enumerate(self.joints):
            joint_group_box = QGroupBox()
            joint_layout = QGridLayout()

            j_label = QLabel(f"J{i+1}: {joint_name}")
            j_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            joint_layout.addWidget(j_label, 0, 1)

            value_label = QLabel("0°")
            value_label.setProperty("emphasis", "bold")
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            joint_layout.addWidget(value_label, 0, 2)
            self.value_labels[joint_name] = value_label
            
            slider = QSlider(Qt.Horizontal)
            if joint_name == "Gripper":
                slider.setRange(0, 180)
            else:
                slider.setRange(-180, 180)
            slider.setValue(0)
            slider.setEnabled(False)
            joint_layout.addWidget(slider, 1, 1, 1, 2)
            self.sliders[joint_name] = slider

            slider.valueChanged.connect(partial(self._handle_slider_change, joint_name=joint_name))
            
            jog_minus_btn = QPushButton("-")
            jog_minus_btn.setObjectName("JogButton")
            joint_layout.addWidget(jog_minus_btn, 0, 0, 2, 1)
            jog_minus_btn.clicked.connect(partial(self.jog_joint, joint_name, -1))

            jog_plus_btn = QPushButton("+")
            jog_plus_btn.setObjectName("JogButton")
            joint_layout.addWidget(jog_plus_btn, 0, 3, 2, 1)
            jog_plus_btn.clicked.connect(partial(self.jog_joint, joint_name, 1))
            
            joint_group_box.setLayout(joint_layout)
            row = i // 2
            col = i % 2
            sliders_grid.addWidget(joint_group_box, row, col)

        jog_step_group_box = QGroupBox("Global Jog Step")
        jog_step_layout = QHBoxLayout()
        self.jog_step_button_group = QButtonGroup()
        
        for step in JOINT_JOG_STEPS_DEG:
            button = QPushButton(step)
            button.setCheckable(True)
            jog_step_layout.addWidget(button)
            self.jog_step_button_group.addButton(button)
            if step == "5":
                button.setChecked(True)

        jog_step_group_box.setLayout(jog_step_layout)
        sliders_grid.addWidget(jog_step_group_box, 3, 1)

        layout.addLayout(sliders_grid)

        bottom_controls_layout = QGridLayout()
        action_buttons_layout = QVBoxLayout()
        
        apply_btn = QPushButton("Apply All Positions")
        apply_btn.clicked.connect(self.apply_all_positions)
        action_buttons_layout.addWidget(apply_btn)

        zero_btn = QPushButton("Zero All Sliders")
        zero_btn.clicked.connect(self.reset_sliders)
        action_buttons_layout.addWidget(zero_btn)
        
        action_buttons_layout.addStretch()
        bottom_controls_layout.addLayout(action_buttons_layout, 0, 0, Qt.AlignTop)

        calib_group_box = QGroupBox()
        calib_layout = QGridLayout()

        calib_layout.addWidget(QLabel("SET_ZERO Joint #:"), 0, 0)
        self.set_zero_input = QLineEdit("1")
        self.set_zero_input.setToolTip("Enter 1-6 for arm joints, 7 for the gripper.")
        calib_layout.addWidget(self.set_zero_input, 0, 1)
        set_zero_btn = QPushButton("Set Current as Zero")
        set_zero_btn.clicked.connect(self.send_set_zero)
        calib_layout.addWidget(set_zero_btn, 0, 2)

        calib_layout.addWidget(QLabel("FACTORY_RESET Servo ID:"), 1, 0)
        self.factory_reset_input = QLineEdit("10")
        calib_layout.addWidget(self.factory_reset_input, 1, 1)
        factory_reset_btn = QPushButton("Factory Reset Servo")
        factory_reset_btn.clicked.connect(self.send_factory_reset)
        calib_layout.addWidget(factory_reset_btn, 1, 2)

        refresh_limits_btn = QPushButton("Refresh Servo Limits")
        refresh_limits_btn.clicked.connect(self.send_refresh_limits)
        
        calib_group_box.setLayout(calib_layout)
        bottom_controls_layout.addWidget(calib_group_box, 0, 1)

        bottom_controls_layout.setColumnStretch(0, 1)
        bottom_controls_layout.setColumnStretch(1, 6)
        
        layout.addLayout(bottom_controls_layout)

        log_area_layout = QGridLayout()
        final_buttons_layout = QVBoxLayout()
        final_buttons_layout.addWidget(refresh_limits_btn)
        final_buttons_layout.addStretch()
        log_area_layout.addLayout(final_buttons_layout, 0, 0, Qt.AlignTop)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        log_area_layout.addWidget(self.log_text, 0, 1)

        log_area_layout.setColumnStretch(0, 1)
        log_area_layout.setColumnStretch(1, 6)

        layout.addLayout(log_area_layout)

        self.setLayout(layout)
        self.live_active = False
        self.log = []
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.CoarseTimer)
        self.timer.timeout.connect(self.toggle_status_visibility)
        # Joint command control loop (last-wins at 50 Hz)
        self._pending_joint_send = False
        self.joint_send_timer = QTimer(self)
        self.joint_send_timer.setTimerType(Qt.CoarseTimer)
        self.joint_send_timer.timeout.connect(self._on_joint_send_tick)
        self._last_joint_log_time = 0.0

    def toggle_status_visibility(self):
        current = self.status_label.property("alertOn")
        if current is None:
            current = False
        self.status_label.setProperty("alertOn", not bool(current))
        self.parent.repolish(self.status_label)

    def activate_live_control(self):
        self.live_active = True
        self.activate_btn.setEnabled(False)
        self.deactivate_btn.setEnabled(True)
        for slider in self.sliders.values():
            slider.setEnabled(True)
        self.status_label.setProperty("alertOn", True)
        self.parent.repolish(self.status_label)
        self.status_label.show()
        self.timer.start(500)
        self.log_message("Live control activated")

        # Async sync request; response will be handled by message dispatcher
        self.parent.send_command("GET_JOINT_ANGLES")
        self.log_message("Requested current joint angles for sync...")
        # Start the joint command control loop
        self._pending_joint_send = True
        self.joint_send_timer.start(20)

    def deactivate_live_control(self):
        self.live_active = False
        self.activate_btn.setEnabled(True)
        self.deactivate_btn.setEnabled(False)
        for slider in self.sliders.values():
            slider.setEnabled(False)
        self.timer.stop()
        self.status_label.hide()
        self.log_message("Live control deactivated")
        self.joint_send_timer.stop()
        self._pending_joint_send = False

    def _handle_slider_change(self, value, joint_name):
        set_label_text(self.value_labels[joint_name], f"{value}°")
        if self.live_active:
            # Mark that a send is pending; control loop will coalesce at 50 Hz
            self._pending_joint_send = True

    def jog_joint(self, joint_name, direction):
        slider = self.sliders[joint_name]
        
        increment = float(self.jog_step_button_group.checkedButton().text())
        current_value = slider.value()
        new_value = current_value + (increment * direction)
        
        new_value = max(slider.minimum(), min(slider.maximum(), new_value))
        slider.setValue(int(new_value))
        if self.live_active:
            self.apply_all_positions()

    def reset_sliders(self):
        for joint in self.sliders:
            self.sliders[joint].setValue(0)

    def apply_all_positions(self):
        values = [self.sliders[joint].value() * (np.pi / 180) for joint in self.joints]
        cmd = ",".join(map(str, values))
        self.parent.send_command(cmd)
        now = time.time()
        if now - self._last_joint_log_time >= 0.2:
            self.log_message(f"Sent Joint Command: {cmd}")
            self._last_joint_log_time = now

    def _on_joint_send_tick(self):
        if self.live_active and self._pending_joint_send:
            self._pending_joint_send = False
            self.apply_all_positions()

    def log_message(self, msg):
        self.log.append(msg)
        max_lines = 500
        if len(self.log) > max_lines:
            self.log = self.log[-max_lines:]
            self.log_text.setPlainText("\n".join(self.log))
        else:
            self.log_text.appendPlainText(msg)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def go_home(self):
        cmd = ",".join(map(str, POS_HOME))
        self.parent.send_command(cmd)
        self.log_message(f"Sent Home: {cmd}")

    def go_zero(self):
        cmd = "0,0,0,0,0,0"
        self.parent.send_command(cmd)
        self.log_message(f"Sent Zero: {cmd}")

    def go_rest(self):
        cmd = ",".join(map(str, POS_REST))
        self.parent.send_command(cmd)
        self.log_message(f"Sent Rest: {cmd}")

    def get_position(self):
        self.parent.send_command("GET_POSITION")
        self.log_message("Requested position...")

    def send_move_line(self):
        input_str = self.move_line_input.text()
        self.parent.send_command(f"MOVE_LINE,{input_str}")

    def send_move_line_rel(self):
        input_str = self.move_line_rel_input.text()
        self.parent.send_command(f"MOVE_LINE_RELATIVE,{input_str}")

    def send_set_orientation(self):
        input_str = self.set_ori_input.text()
        self.parent.send_command(f"SET_ORIENTATION,{input_str}")

    def send_run_trajectory(self):
        name = self.run_traj_combo.currentText()
        if not name:
            QMessageBox.warning(self, "Selection Error", "Please select a trajectory to run, or refresh the list.")
            return
        is_looping = self.loop_traj_btn.isChecked()
        self.parent.send_command(f"RUN_TRAJECTORY,{name},false,{is_looping}")

    def send_end_trajectory(self):
        name = self.end_traj_input.text()
        self.parent.send_command(f"END_TRAJECTORY,{name}")

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

    def send_refresh_limits(self):
        self.parent.send_command("REFRESH_LIMITS")
        self.log_message("Sent: REFRESH_LIMITS")

    def send_translate(self):
        input_str = self.translate_input.text()
        self.parent.send_command(f"TRANSLATE,{input_str}")

    def send_rotate(self):
        input_str = self.rotate_input.text()
        self.parent.send_command(f"ROTATE,{input_str}")


