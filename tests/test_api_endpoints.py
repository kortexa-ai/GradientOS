import json
import base64
import tempfile
import pytest

pytest.importorskip("httpx")

from contextlib import contextmanager
from fastapi.testclient import TestClient

from gradient_os.api.main import create_app


@contextmanager
def patch_send(monkeypatch):
    responses = {
        "STOP": (True, "ACK,STOP"),
        "WAIT_FOR_IDLE": (True, "ACK,WAIT_FOR_IDLE"),
        "GET_STATUS": (True, "STATUS,gripper_present,True"),
        "GET_POSITION": (
            True,
            "CURRENT_POSE,0.1,0.2,0.3,10.0,20.0,30.0,1,2,3,4,5,6",
        ),
        "GET_JOINT_ANGLES": (True, "JOINT_ANGLES,1,2,3,4,5,6,7"),
        "GET_GRIPPER_STATE": (True, "GRIPPER_STATE,45.0,2048"),
        "GET_ALL_POSITIONS": (
            True,
            "ALL_POS_DATA,10,2048,20,2050,21,2050",
        ),
        "GET_ORIENTATION": (
            True,
            "CURRENT_ORIENTATION,1,0,0,0,1,0,0,0,1",
        ),
        "GET_TRAJECTORIES": (True, "TRAJECTORIES,alpha,beta"),
    }
    no_reply_commands = {
        "PLAN_TRAJECTORY",
        "REC_POS",
        "END_TRAJECTORY,test",
        "RUN_TRAJECTORY,alpha,false",
        "0,0,0,0,0,0",
    }
    planner_payload = {
        "name": "__planner_preview__",
        "steps": [
            {"type": "move", "path": [[1.0, 2.0, 3.0]], "freq": 100},
        ],
        "trajectory": {
            "description": "Planned",
            "loop": False,
            "orientation_euler_angles_deg": None,
            "moves": [
                {"command": "move_absolute", "vector": [0.1, 0.2, 0.3]},
                {"command": "pause", "duration": 1.0},
            ],
        },
        "cartesian_path": [[0.1, 0.2, 0.3]],
        "waypoints": [[0.1, 0.2, 0.3]],
        "file_path": "/tmp/recorded_trajectories/__planner_preview__.json",
    }
    call_log = []

    def fake_send(command, timeout=0.5, expect_response=True):
        call_log.append((command, timeout, expect_response))
        if command.startswith("PLAN_TRAJECTORY_POINTS"):
            return True, f"PLANNED_TRAJECTORY_POINTS,{json.dumps(planner_payload)}"
        if command in no_reply_commands:
            if expect_response:
                return False, f"unexpected response requested for {command}"
            return True, ""
        if not expect_response:
            return True, ""
        return responses.get(command, (False, f"unexpected {command}"))

    class DummyCommandApi:
        sample_traj = {
            "description": "Sample trajectory",
            "loop": False,
            "orientation_euler_angles_deg": None,
            "moves": [
                {"command": "move_absolute", "vector": [0.1, 0.2, 0.3]},
                {"command": "pause", "duration": 1.0},
                {"command": "move_absolute", "vector": [0.4, 0.5, 0.6]},
            ],
        }

        @staticmethod
        def _load_trajectory_by_name(name):
            if name in {"alpha", "beta", "__planner_preview__"}:
                return DummyCommandApi.sample_traj
            return None

        @staticmethod
        def plan_preview_trajectory_points(points, preview_name="__planner_preview__", weld_metadata=None):
            if not points:
                raise ValueError("no points")
            body = dict(planner_payload)
            body["name"] = preview_name
            body["waypoints"] = points
            body["cartesian_path"] = points
            body["trajectory"] = dict(DummyCommandApi.sample_traj)
            if weld_metadata:
                body["trajectory"]["weld"] = weld_metadata
            return body

    class DummyTopologyService:
        model = {
            "model_id": "step-test",
            "filename": "fixture.step",
            "fingerprint": "abc123",
            "parts": [{"id": "part_0", "edge_count": 1}],
            "edges": [
                {
                    "id": "part_0:edge_00000",
                    "part_id": "part_0",
                    "samples": [[0.0, 0.0, 0.0], [0.1, 0.0, 0.0], [0.2, 0.0, 0.0]],
                }
            ],
        }

        def load_step(self, *, filename, step_bytes, sample_count):
            assert filename
            assert step_bytes
            return dict(self.model)

        def get_model(self, model_id):
            if model_id != self.model["model_id"]:
                raise KeyError(model_id)
            return dict(self.model)

        def sample_edge_segment(self, *, model_id, edge_id, start_s, end_s, sample_count):
            assert model_id == self.model["model_id"]
            assert edge_id == self.model["edges"][0]["id"]
            return [
                (0.0, 0.0, 0.0),
                (0.1, 0.0, 0.0),
                (0.2, 0.0, 0.0),
            ]

    monkeypatch.setattr("gradient_os.api.main._send_controller_command", fake_send)
    monkeypatch.setattr(
        "gradient_os.api.main._probe_controller", lambda timeout=0.5: (True, "ok")
    )
    monkeypatch.setattr(
        "gradient_os.api.main.controller_command_api", DummyCommandApi
    )
    monkeypatch.setattr(
        "gradient_os.api.main.topology_service", DummyTopologyService()
    )
    monkeypatch.setattr(
        "gradient_os.api.main._WELD_PROGRAM_DIR", tempfile.mkdtemp(prefix="weld-programs-")
    )
    yield call_log


@pytest.fixture
def client(monkeypatch):
    with patch_send(monkeypatch) as call_log:
        app = create_app()
        with TestClient(app) as client:
            client.command_calls = call_log  # type: ignore[attr-defined]
            yield client


def test_control_stop(client):
    resp = client.post("/control/stop")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "ACK,STOP"


def test_control_wait_for_idle(client):
    resp = client.post("/control/wait-for-idle")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "ACK,WAIT_FOR_IDLE"


def test_control_home(client):
    resp = client.post("/control/home")
    assert resp.status_code == 200
    assert client.command_calls[-1] == ("0,0,0,0,0,0", 2.0, False)


def test_info_status(client):
    resp = client.get("/info/status")
    assert resp.status_code == 200
    assert resp.json() == {"gripper_present": True}


def test_info_pose(client):
    resp = client.get("/info/pose")
    assert resp.status_code == 200
    body = resp.json()
    assert body["position_m"]["x"] == pytest.approx(0.1)
    assert body["orientation_euler_deg"]["yaw"] == pytest.approx(30.0)
    assert body["joints_deg"] == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]


def test_info_joints(client):
    resp = client.get("/info/joints")
    assert resp.status_code == 200
    assert resp.json() == {"arm_deg": [1, 2, 3, 4, 5, 6], "gripper_deg": 7}


def test_info_gripper(client):
    resp = client.get("/info/gripper")
    assert resp.status_code == 200
    assert resp.json() == {"angle_deg": 45.0, "raw_position": 2048}


def test_info_all_positions(client):
    resp = client.get("/info/all-positions")
    assert resp.status_code == 200
    assert resp.json() == {
        "servos": [
            {"servo_id": 10, "raw_position": 2048},
            {"servo_id": 20, "raw_position": 2050},
            {"servo_id": 21, "raw_position": 2050},
        ]
    }


def test_info_orientation(client):
    resp = client.get("/info/orientation")
    assert resp.status_code == 200
    assert resp.json() == {
        "matrix": [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    }


def test_trajectory_plan_record_end(client):
    resp = client.post("/trajectory/plan")
    assert resp.status_code == 200
    assert client.command_calls[-1] == ("PLAN_TRAJECTORY", 1.0, False)

    resp = client.post("/trajectory/record")
    assert resp.status_code == 200
    assert client.command_calls[-1] == ("REC_POS", 1.0, False)

    resp = client.post("/trajectory/end", json={"name": "test"})
    assert resp.status_code == 200
    assert client.command_calls[-1] == ("END_TRAJECTORY,test", 2.0, False)


def test_trajectory_list(client):
    resp = client.get("/trajectory/list")
    assert resp.status_code == 200
    assert resp.json() == {"trajectories": ["alpha", "beta"]}


def test_trajectory_run(client):
    resp = client.post("/trajectory/run", json={"name": "alpha"})
    assert resp.status_code == 200
    assert client.command_calls[-1] == ("RUN_TRAJECTORY,alpha,false", 2.0, False)


def test_trajectory_plan_points_success(client):
    resp = client.post(
        "/trajectory/plan-points",
        json={"points": [{"x": 0.1, "y": 0.2, "z": 0.3}, [0.4, 0.5, 0.6]]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "__planner_preview__"
    assert body["trajectory"]["moves"][0]["vector"] == [0.1, 0.2, 0.3]
    assert client.command_calls[-1][0].startswith("PLAN_TRAJECTORY_POINTS,0.1,0.2,0.3,0.4,0.5,0.6")
    assert client.command_calls[-1][2] is True


def test_trajectory_plan_points_validation(client):
    start_len = len(client.command_calls)
    resp = client.post("/trajectory/plan-points", json={"points": [{"x": 1.0}]})
    assert resp.status_code == 400
    assert len(client.command_calls) == start_len


def test_trajectory_detail(client):
    resp = client.get("/trajectory/detail/alpha")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "alpha"
    assert body["trajectory"]["moves"][0]["vector"] == [0.1, 0.2, 0.3]


def test_cad_topology_load_and_get(client):
    raw = b"STEP-MOCK"
    encoded = base64.b64encode(raw).decode("ascii")
    resp = client.post(
        "/cad/topology/load-step",
        json={"filename": "fixture.step", "step_base64": encoded},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_id"] == "step-test"
    assert body["edges"][0]["id"] == "part_0:edge_00000"

    resp = client.get("/cad/topology/step-test")
    assert resp.status_code == 200
    assert resp.json()["parts"][0]["id"] == "part_0"


def test_trajectory_plan_weld(client):
    resp = client.post(
        "/trajectory/plan-weld",
        json={
            "model_id": "step-test",
            "edge_id": "part_0:edge_00000",
            "start_s": 0.1,
            "end_s": 0.9,
            "weld_type": "fillet",
            "weld_name": "test weld",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "__weld_preview__"
    assert body["trajectory"]["weld"]["type"] == "fillet"
    assert body["source"]["mode"] == "edge_segment"


def test_weld_program_save_list_load(client):
    step_payload = base64.b64encode(b"STEP-MOCK").decode("ascii")
    save_resp = client.post(
        "/weld-program/save",
        json={
            "name": "demo_program",
            "step": {
                "filename": "fixture.step",
                "step_base64": step_payload,
                "transform": {
                    "position": {"x": 0.1, "y": 0.2, "z": 0.3},
                    "rotationDeg": {"x": 1.0, "y": 2.0, "z": 3.0},
                    "scale": 1.5,
                },
            },
            "weld_draft": {
                "modelId": "step-test",
                "edgeId": "part_0:edge_00000",
                "weldType": "fillet",
                "weldName": "demo weld",
                "startS": 0.2,
                "endS": 0.8,
            },
            "editable_waypoints": [{"x": 0.0, "y": 0.0, "z": 0.0}, {"x": 0.2, "y": 0.0, "z": 0.0}],
            "planned_trajectory": {"name": "__weld_preview__", "waypoints": [{"x": 0.0, "y": 0.0, "z": 0.0}]},
        },
    )
    assert save_resp.status_code == 200
    assert save_resp.json()["name"] == "demo_program"

    list_resp = client.get("/weld-program/list")
    assert list_resp.status_code == 200
    assert "demo_program" in list_resp.json()["programs"]

    load_resp = client.get("/weld-program/demo_program")
    assert load_resp.status_code == 200
    payload = load_resp.json()
    assert payload["name"] == "demo_program"
    assert payload["weld_draft"]["edgeId"] == "part_0:edge_00000"
    assert payload["step"]["filename"] == "fixture.step"


def test_preview_execute_clear(client, monkeypatch):
    planned_path = [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.05, 0.04, 0.03, 0.02, 0.01, 0.0],
    ]

    def fake_plan(start_q, target_pos, velocity, acceleration, frequency, use_smoothing):
        return planned_path

    monkeypatch.setattr(
        "gradient_os.arm_controller.trajectory_execution._plan_smooth_move",
        fake_plan,
    )

    def fake_fk(joints):
        return [0.2, 0.1, 0.3]

    monkeypatch.setattr(
        "gradient_os.ik_solver.get_fk",
        fake_fk,
    )

    resp = client.post(
        "/trajectory/preview",
        json={"x": 0.2, "y": 0.1, "z": 0.3, "velocity": 0.2, "acceleration": 0.1, "closed_loop": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["joints_rad"] == planned_path
    assert body.get("cartesian_m") == [[0.2, 0.1, 0.3], [0.2, 0.1, 0.3]]
    assert client.command_calls[-1] == ("GET_POSITION", 1.0, True)

    resp = client.post("/trajectory/execute-preview")
    assert resp.status_code == 200
    # Last two commands: MOVE_LINE..., WAIT_FOR_IDLE
    assert client.command_calls[-2][0].startswith("MOVE_LINE,0.2,0.1,0.3,0.2,0.1")
    assert client.command_calls[-1] == ("WAIT_FOR_IDLE", 60.0, True)

    # Preview cleared, executing again should fail
    resp = client.post("/trajectory/execute-preview")
    assert resp.status_code == 404

    resp = client.post("/trajectory/clear-preview")
    assert resp.status_code == 200
