export type Point3 = { x: number; y: number; z: number };

export type TrajectoryMove = {
  command: string;
  vector?: number[] | null;
  orientation_euler_deg?: number[] | null;
  [key: string]: unknown;
};

export type TrajectoryFile = {
  description?: string;
  loop?: boolean;
  orientation_euler_angles_deg?: number[] | null;
  moves: TrajectoryMove[];
};

export type PreviewPlan = {
  name: string;
  trajectory: TrajectoryFile;
  pathPoints: Point3[];
  waypoints: Point3[];
};

export type ProgramNodeType =
  | "program"
  | "setupGroup"
  | "operationGroup"
  | "move"
  | "waypoint"
  | "weldSegment";

export type ProgramNodeFocus = {
  openPanel?: "trajectory" | "weld";
  moveIndex?: number;
  waypointIndices?: number[];
  pathRange?: { start: number; end: number };
  weldSegmentEdgeId?: string;
};

export type ProgramNode = {
  id: string;
  type: ProgramNodeType;
  label: string;
  subtitle?: string;
  badge?: string;
  focus?: ProgramNodeFocus;
  children: ProgramNode[];
};

type BuildProgramTreeInput = {
  plan: PreviewPlan | null;
  weldSegments?: Array<{
    edgeId: string;
    startS: number;
    endS: number;
  }>;
  weldType?: string;
};

function toNodeId(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]+/g, "_");
}

function estimatePathRange(
  segmentIndex: number,
  totalSegments: number,
  pathPointCount: number,
): { start: number; end: number } | undefined {
  if (totalSegments <= 0 || pathPointCount < 2) {
    return undefined;
  }
  const maxIdx = pathPointCount - 1;
  const start = Math.max(
    0,
    Math.min(maxIdx, Math.floor((segmentIndex / totalSegments) * maxIdx)),
  );
  const end = Math.max(
    start,
    Math.min(maxIdx, Math.ceil(((segmentIndex + 1) / totalSegments) * maxIdx)),
  );
  return { start, end };
}

function toPoint3(value: unknown): Point3 | null {
  if (Array.isArray(value) && value.length >= 3) {
    const [x, y, z] = value;
    const nx = Number(x);
    const ny = Number(y);
    const nz = Number(z);
    if (Number.isFinite(nx) && Number.isFinite(ny) && Number.isFinite(nz)) {
      return { x: nx, y: ny, z: nz };
    }
  } else if (
    typeof value === "object" &&
    value !== null &&
    "x" in value &&
    "y" in value &&
    "z" in value
  ) {
    const vector = value as { x: unknown; y: unknown; z: unknown };
    const nx = Number(vector.x);
    const ny = Number(vector.y);
    const nz = Number(vector.z);
    if (Number.isFinite(nx) && Number.isFinite(ny) && Number.isFinite(nz)) {
      return { x: nx, y: ny, z: nz };
    }
  }
  return null;
}

function coercePointList(value: unknown): Point3[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((entry) => toPoint3(entry))
    .filter((point): point is Point3 => point !== null);
}

function deriveWaypointsFromTrajectory(trajectory: TrajectoryFile): Point3[] {
  if (!trajectory?.moves || !Array.isArray(trajectory.moves)) {
    return [];
  }
  const points: Point3[] = [];
  trajectory.moves.forEach((move) => {
    if (move?.command === "move_absolute") {
      const point = toPoint3(move.vector ?? null);
      if (point) {
        points.push(point);
      }
    }
  });
  return points;
}

function buildPreviewPlan(
  name: string,
  trajectory: TrajectoryFile,
  explicitPath?: unknown,
  explicitWaypoints?: unknown,
): PreviewPlan {
  const fallbackWaypoints = deriveWaypointsFromTrajectory(trajectory);
  const explicitWaypointsList = coercePointList(explicitWaypoints);
  const waypoints =
    explicitWaypointsList.length > 0
      ? explicitWaypointsList
      : fallbackWaypoints;
  const cartesianPath = coercePointList(explicitPath);
  const pathPoints =
    cartesianPath.length > 0
      ? cartesianPath
      : waypoints.length > 0
        ? waypoints
        : fallbackWaypoints;

  return {
    name,
    trajectory,
    pathPoints: pathPoints.map(({ x, y, z }) => transformToScenePoint({ x, y, z })),
    waypoints: (waypoints.length > 0 ? waypoints : fallbackWaypoints).map(
      ({ x, y, z }) => transformToScenePoint({ x, y, z }),
    ),
  };
}

export function previewFromPlannerPayload(payload: any): {
  plan: PreviewPlan;
  waypoints: Point3[];
} {
  const name =
    typeof payload?.name === "string" && payload.name.trim()
      ? payload.name.trim()
      : "__planner_preview__";
  const trajectory =
    payload && typeof payload.trajectory === "object" && payload.trajectory
      ? (payload.trajectory as TrajectoryFile)
      : ({ moves: [] } as TrajectoryFile);
  const plan = buildPreviewPlan(
    name,
    trajectory,
    payload?.cartesian_path,
    payload?.waypoints,
  );
  const waypoints = plan.waypoints;
  return { plan, waypoints };
}

export function previewFromTrajectoryDetail(
  name: string,
  trajectory: TrajectoryFile,
): PreviewPlan {
  return buildPreviewPlan(name, trajectory);
}

export function buildProgramTree({
  plan,
  weldSegments = [],
  weldType,
}: BuildProgramTreeInput): ProgramNode | null {
  if (!plan && (!Array.isArray(weldSegments) || weldSegments.length === 0)) {
    return null;
  }

  const trajectory = plan?.trajectory;
  const moves = Array.isArray(trajectory?.moves) ? trajectory.moves : [];
  const pathPointCount = plan?.pathPoints.length ?? 0;
  const totalWaypointSegments = Math.max((plan?.waypoints.length ?? 0) - 1, 0);

  const motionNodes: ProgramNode[] = [];
  const controlNodes: ProgramNode[] = [];
  const timingNodes: ProgramNode[] = [];
  const waypointNodes: ProgramNode[] = [];

  let waypointIndex = -1;
  let traversedWaypointSegment = -1;

  moves.forEach((move, moveIndex) => {
    const command = String(move?.command ?? "").trim() || "unknown";
    const isAbsoluteMove = command === "move_absolute";
    if (isAbsoluteMove) {
      waypointIndex += 1;
    }

    const focus: ProgramNodeFocus = {
      openPanel: "trajectory",
      moveIndex,
    };
    if (isAbsoluteMove && waypointIndex >= 0) {
      focus.waypointIndices = [waypointIndex];
      if (waypointIndex > 0) {
        traversedWaypointSegment += 1;
        const range = estimatePathRange(
          traversedWaypointSegment,
          totalWaypointSegments,
          pathPointCount,
        );
        if (range) {
          focus.pathRange = range;
        }
      }
    }

    const moveNode: ProgramNode = {
      id: `move_${moveIndex}`,
      type: "move",
      label: `${command}`,
      subtitle: `Move ${moveIndex + 1}`,
      badge: `#${moveIndex + 1}`,
      focus,
      children: [],
    };

    if (isAbsoluteMove && waypointIndex >= 0) {
      const point = plan?.waypoints[waypointIndex];
      moveNode.children.push({
        id: `move_${moveIndex}_waypoint_${waypointIndex}`,
        type: "waypoint",
        label: `Waypoint ${waypointIndex + 1}`,
        subtitle: point
          ? `${point.x.toFixed(3)}, ${point.y.toFixed(3)}, ${point.z.toFixed(3)}`
          : undefined,
        focus: {
          openPanel: "trajectory",
          waypointIndices: [waypointIndex],
          pathRange: focus.pathRange,
          moveIndex,
        },
        children: [],
      });
    }

    if (command === "pause") {
      timingNodes.push(moveNode);
    } else if (
      command === "move_absolute" ||
      command === "move_relative" ||
      command === "move_arc"
    ) {
      motionNodes.push(moveNode);
    } else {
      controlNodes.push(moveNode);
    }
  });

  if (Array.isArray(plan?.waypoints)) {
    plan!.waypoints.forEach((point, index) => {
      waypointNodes.push({
        id: `waypoint_${index}`,
        type: "waypoint",
        label: `Waypoint ${index + 1}`,
        subtitle: `${point.x.toFixed(3)}, ${point.y.toFixed(3)}, ${point.z.toFixed(3)}`,
        badge: `${index + 1}`,
        focus: {
          openPanel: "trajectory",
          waypointIndices: [index],
        },
        children: [],
      });
    });
  }

  const operationGroups: ProgramNode[] = [];
  if (motionNodes.length > 0) {
    operationGroups.push({
      id: "op_motion",
      type: "operationGroup",
      label: "Motion Operations",
      badge: `${motionNodes.length}`,
      children: motionNodes,
    });
  }
  if (timingNodes.length > 0) {
    operationGroups.push({
      id: "op_timing",
      type: "operationGroup",
      label: "Timing Operations",
      badge: `${timingNodes.length}`,
      children: timingNodes,
    });
  }
  if (controlNodes.length > 0) {
    operationGroups.push({
      id: "op_control",
      type: "operationGroup",
      label: "Control Operations",
      badge: `${controlNodes.length}`,
      children: controlNodes,
    });
  }
  if (waypointNodes.length > 0) {
    operationGroups.push({
      id: "op_waypoints",
      type: "operationGroup",
      label: "Waypoint List",
      badge: `${waypointNodes.length}`,
      children: waypointNodes,
    });
  }

  if (Array.isArray(weldSegments) && weldSegments.length > 0) {
    const weldNodes: ProgramNode[] = weldSegments.map((segment, index) => {
      const range = estimatePathRange(index, weldSegments.length, pathPointCount);
      return {
        id: `weld_segment_${index}_${toNodeId(segment.edgeId)}`,
        type: "weldSegment",
        label: `Segment ${index + 1}`,
        subtitle: segment.edgeId,
        badge: weldType ?? "weld",
        focus: {
          openPanel: "weld",
          weldSegmentEdgeId: segment.edgeId,
          pathRange: range,
        },
        children: [],
      };
    });
    operationGroups.push({
      id: "op_weld",
      type: "operationGroup",
      label: "Weld Features",
      badge: `${weldNodes.length}`,
      children: weldNodes,
    });
  }

  return {
    id: "program_root",
    type: "program",
    label: plan?.name ?? "Program",
    subtitle: `${moves.length} move(s)`,
    children: [
      {
        id: "setup_primary",
        type: "setupGroup",
        label: "Setup",
        subtitle: weldType ? `${weldType} workflow` : "Robot sequence",
        children: operationGroups,
      },
    ],
  };
}

export function encodePointsForApi(points: Point3[]): any[] {
  return points.map((point) => {
    const world = transformFromScenePoint(point);
    return {
      x: Number(world.x),
      y: Number(world.y),
      z: Number(world.z),
    };
  });
}

export function transformToScenePoint(point: Point3): Point3 {
  return {
    x: point.x,
    y: point.y,
    z: point.z,
  };
}

export function transformFromScenePoint(point: Point3): Point3 {
  return {
    x: point.x,
    y: point.y,
    z: point.z,
  };
}
