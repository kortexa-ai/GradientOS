
import curses
import socket
import threading
import time
import argparse
import sys
import numpy as np
from scipy.spatial.transform import Rotation as R

# --- Constants ---
DEFAULT_CONTROLLER_IP = "mini-arm.local"
UDP_PORT = 3000
UPDATE_INTERVAL_S = 0.1  # 10 Hz for UI updates
POSITION_REQUEST_INTERVAL_S = 0.5 # 2 Hz for position requests

# Movement parameters
PAN_STEP_M = 0.05  # 5 cm
ORIENT_STEP_DEG = 5.0 # 5 degrees
GRIPPER_STEP_DEG = 10.0 # 10 degrees

# Preset positions (in radians)
POS_ZERO = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
POS_HOME = [0.0, -0.785, 0.785, 0.0, -0.785, 0.0]
POS_REST = [0.0, -1.4, 1.5, 0.0, 0.0, 0.0]

class UDPClient:
    """Handles UDP communication with the robot controller."""
    def __init__(self, ip, port):
        self.server_address = (ip, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1.0)
        self.position_xyz = [0.0, 0.0, 0.0]
        self.orientation_rpy_deg = [0.0, 0.0, 0.0]
        self.lock = threading.Lock()
        self.running = True
        
        self.position_thread = threading.Thread(target=self._fetch_state, daemon=True)
        self.position_thread.start()

    def _send_command_locked(self, command):
        """Sends a command without acquiring the lock. Assumes lock is held."""
        try:
            self.sock.sendto(command.encode('utf-8'), self.server_address)
            return None
        except socket.gaierror:
            return f"Error: Hostname '{self.server_address[0]}' could not be resolved."
        except Exception as e:
            return f"Error sending command: {e}"

    def send_command(self, command):
        """Sends a fire-and-forget command to the robot controller."""
        with self.lock:
            return self._send_command_locked(command)

    def get_initial_gripper_angle(self):
        """Fetches the initial gripper angle. This is a blocking call."""
        with self.lock:
            self._send_command_locked("GET_GRIPPER_STATE")
            try:
                # Temporarily make the socket blocking with a short timeout
                self.sock.settimeout(0.5)
                data, _ = self.sock.recvfrom(1024)
                response = data.decode('utf-8')
                if response.startswith("GRIPPER_STATE,"):
                    parts = response.split(',')
                    if len(parts) >= 2:
                        # Round to nearest 10.
                        return round(float(parts[1]) / 10) * 10
            except (socket.timeout, ValueError, IndexError):
                return 0.0
            finally:
                self.sock.settimeout(1.0)
        return 0.0

    def _fetch_state(self):
        """Periodically sends GET_POSITION and GET_ORIENTATION and updates the internal state."""
        while self.running:
            # --- Get Position ---
            with self.lock:
                self._send_command_locked("GET_POSITION")
                try:
                    data, _ = self.sock.recvfrom(1024)
                    response = data.decode('utf-8')
                    if response.startswith("CURRENT_POSE,"):
                        parts = response.split(',')
                        if len(parts) >= 4:
                            self.position_xyz = [float(p) for p in parts[1:4]]
                except socket.timeout:
                    pass # It's okay to time out
                except Exception:
                    pass # Ignore other errors for now
            
            if not self.running:
                break
            time.sleep(0.02) # Small pause between requests

            # --- Get Orientation ---
            with self.lock:
                self._send_command_locked("GET_ORIENTATION")
                try:
                    data, _ = self.sock.recvfrom(1024)
                    response = data.decode('utf-8')
                    if response.startswith("CURRENT_ORIENTATION,"):
                        parts = response.split(',')
                        if len(parts) >= 10:
                            flat_matrix = [float(p) for p in parts[1:10]]
                            rot_matrix = np.array(flat_matrix).reshape((3, 3))
                            r = R.from_matrix(rot_matrix)
                            self.orientation_rpy_deg = r.as_euler('xyz', degrees=True)
                except socket.timeout:
                    pass
                except Exception:
                    pass
            
            time.sleep(POSITION_REQUEST_INTERVAL_S)

    def get_position(self):
        """Returns the last known position in a thread-safe way."""
        with self.lock:
            return self.position_xyz

    def get_orientation(self):
        """Returns the last known orientation in a thread-safe way."""
        with self.lock:
            return self.orientation_rpy_deg

    def close(self):
        self.running = False
        self.position_thread.join(timeout=1.0)
        self.sock.close()

class CLI_UI:
    """Manages the curses-based CLI."""
    def __init__(self, stdscr, controller_ip):
        self.stdscr = stdscr
        self.client = UDPClient(controller_ip, UDP_PORT)
        self.mode = "pan"  # 'pan' or 'orient'
        self.last_error = None
        self.gripper_angle = self.client.get_initial_gripper_angle()

    def _setup_curses(self):
        curses.curs_set(0) # Hide cursor
        self.stdscr.nodelay(True) # Non-blocking getch
        self.stdscr.timeout(int(UPDATE_INTERVAL_S * 1000)) # Timeout for getch
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)

    def _draw(self):
        self.stdscr.erase()
        height, width = self.stdscr.getmaxyx()

        # Title
        title = "GradientOS Robot Arm CLI Controller"
        self.stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)

        # Status
        mode_str = f"Mode: {self.mode.upper()}"
        mode_color = curses.color_pair(2) if self.mode == 'pan' else curses.color_pair(3)
        self.stdscr.addstr(2, 2, mode_str, mode_color | curses.A_BOLD)

        pos = self.client.get_position()
        pos_str = f"Position (X,Y,Z): {pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f}"
        self.stdscr.addstr(3, 2, pos_str, curses.color_pair(1))

        orient = self.client.get_orientation()
        orient_str = f"Orient (R,P,Y): {orient[0]:.1f}, {orient[1]:.1f}, {orient[2]:.1f}"
        self.stdscr.addstr(4, 2, orient_str, curses.color_pair(1))

        gripper_str = f"Gripper Angle: {self.gripper_angle:.1f}° (0-120)"
        self.stdscr.addstr(5, 2, gripper_str, curses.color_pair(1))

        # Instructions
        y = 7
        self.stdscr.addstr(y, 2, "--- Controls ---", curses.A_UNDERLINE)
        
        if self.mode == 'pan':
            self.stdscr.addstr(y+1, 4, "[W] Forward (+X)   [S] Backward (-X)")
            self.stdscr.addstr(y+2, 4, "[A] Left (-Y)      [D] Right (+Y)")
            self.stdscr.addstr(y+3, 4, "[Shift+W] Up (+Z)  [Shift+S] Down (-Z)")
        else: # orient
            self.stdscr.addstr(y+1, 4, "[W] Pitch Down (-Y)  [S] Pitch Up (+Y)")
            self.stdscr.addstr(y+2, 4, "[A] Yaw Left (+Z)  [D] Yaw Right (-Z)")
            self.stdscr.addstr(y+3, 4, "[Shift+W] Roll (+) [Shift+S] Roll (-)")


        self.stdscr.addstr(y+5, 2, "--- General ---", curses.A_UNDERLINE)
        self.stdscr.addstr(y+6, 4, "[Tab]       Toggle Pan/Orient Mode")
        self.stdscr.addstr(y+7, 4, "[R]         Open Gripper")
        self.stdscr.addstr(y+8, 4, "[F]         Close Gripper")
        self.stdscr.addstr(y+9, 4, "[1]         Go to REST position")
        self.stdscr.addstr(y+10, 4, "[2]         Go to HOME position")
        self.stdscr.addstr(y+11, 4, "[3]         Go to ZERO position")
        self.stdscr.addstr(y+12, 4, "[Q]         Quit")

        # Error message
        if self.last_error:
            self.stdscr.addstr(height - 2, 2, self.last_error, curses.color_pair(4))

        self.stdscr.refresh()

    def _handle_pan_input(self, key):
        """Handles keyboard input for panning mode."""
        pan_map = {
            ord('w'): f"MOVE_LINE_RELATIVE,{PAN_STEP_M},0,0",
            ord('s'): f"MOVE_LINE_RELATIVE,{-PAN_STEP_M},0,0",
            ord('a'): f"MOVE_LINE_RELATIVE,0,{PAN_STEP_M},0",
            ord('d'): f"MOVE_LINE_RELATIVE,0,{-PAN_STEP_M},0",
            ord('W'): f"MOVE_LINE_RELATIVE,0,0,{PAN_STEP_M}",
            ord('S'): f"MOVE_LINE_RELATIVE,0,0,{-PAN_STEP_M}",
        }
        return pan_map.get(key)

    def _handle_orient_input(self, key):
        """Handles keyboard input for orientation mode."""
        orient_map = {
            ord('w'): (0, 1, 0),  # Pitch Up (+Y)
            ord('s'): (0, -1, 0), # Pitch Down (-Y)
            ord('a'): (0, 0, 1),  # Yaw Left (+Z)
            ord('d'): (0, 0, -1), # Yaw Right (-Z)
            ord('W'): (1, 0, 0),  # Roll + (+X)
            ord('S'): (-1, 0, 0), # Roll - (-X)
        }
        delta = orient_map.get(key)
        if delta is None:
            return None

        current_rpy = self.client.get_orientation()
        new_rpy = [
            current_rpy[0] + delta[0] * ORIENT_STEP_DEG,
            current_rpy[1] + delta[1] * ORIENT_STEP_DEG,
            current_rpy[2] + delta[2] * ORIENT_STEP_DEG,
        ]
        # Use a short duration for responsive jogging
        return f"SET_ORIENTATION,{new_rpy[0]},{new_rpy[1]},{new_rpy[2]},duration_s=0.2"

    def _handle_input(self, key):
        cmd = None
        if key in [ord('q'), ord('Q')]:
            return False # Signal to exit

        # Mode switching
        if key == ord('\t') or key == 9:
            self.mode = 'orient' if self.mode == 'pan' else 'pan'
            return True

        # Key-to-command mapping for simple cases
        simple_commands = {
            ord('1'): ",".join(map(str, POS_REST)),
            ord('2'): ",".join(map(str, POS_HOME)),
            ord('3'): ",".join(map(str, POS_ZERO)),
        }
        cmd = simple_commands.get(key)

        # Gripper controls
        if key in [ord('r'), ord('R')]:
            self.gripper_angle = min(120.0, self.gripper_angle + GRIPPER_STEP_DEG)
            cmd = f"SET_GRIPPER,{self.gripper_angle}"
        elif key in [ord('f'), ord('F')]:
            self.gripper_angle = max(0.0, self.gripper_angle - GRIPPER_STEP_DEG)
            cmd = f"SET_GRIPPER,{self.gripper_angle}"

        # Mode-dependent movement
        if cmd is None:
            if self.mode == 'pan':
                cmd = self._handle_pan_input(key)
            else: # orient
                cmd = self._handle_orient_input(key)

        if cmd:
            err = self.client.send_command(cmd)
            if err:
                self.last_error = err
            else:
                self.last_error = None

        return True

    def run(self):
        self._setup_curses()
        running = True
        while running:
            self._draw()
            try:
                key = self.stdscr.getch()
                if key != -1:
                    running = self._handle_input(key)
            except (curses.error, KeyboardInterrupt):
                break
        
        self.client.close()

def _cli_main(stdscr, ip_address):
    """The main function that runs inside the curses wrapper."""
    ui = CLI_UI(stdscr, ip_address)
    ui.run()

def main():
    """Parses args and launches the curses UI."""
    parser = argparse.ArgumentParser(description='Robot Arm CLI Controller')
    parser.add_argument('--ip', type=str, default=DEFAULT_CONTROLLER_IP,
                        help=f'The IP address or hostname of the robot controller. Defaults to {DEFAULT_CONTROLLER_IP}.')
    args = parser.parse_args()
    
    try:
        curses.wrapper(_cli_main, args.ip)
    except curses.error as e:
        print(f"Error: Failed to initialize curses: {e}")
        print("This CLI is not supported on Windows or in environments without a TTY.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
