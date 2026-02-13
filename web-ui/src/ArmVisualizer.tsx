import {
  forwardRef,
  type ForwardedRef,
  useEffect,
  useImperativeHandle,
  useRef,
} from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls";
import URDFLoader, { type URDFRobot } from "urdf-loader";
import occtWasmUrl from "occt-import-js/dist/occt-import-js.wasm?url";
import type { Point3 } from "./previewUtils";

type ArmVisualizerProps = {
  joints?: number[];
  showBoundingBox: boolean;
  selectionMode: boolean;
  onPointSelected?: (point: { x: number; y: number; z: number }) => void;
  pathPoints?: Point3[];
  waypoints?: Point3[];
  stepFile?: File | null;
  stepTransform?: StepTransform;
  onStepStatusChange?: (status: StepLoadStatus) => void;
};

const GRID_CELL_SIZE = 0.05; // 10 cm per square
const GRID_CELLS_PER_SIDE = 80; // spans 4 m total (enough workspace)
const GRID_SIZE = GRID_CELL_SIZE * GRID_CELLS_PER_SIDE;
const ROBOT_SCALE = 1; // make the robot look bit bigger
const BOUNDING_MARKER_COLORS = [
  0xf87171,
  0xfbbf24,
  0x34d399,
  0x38bdf8,
  0xa855f7,
  0xf472b6,
  0x22d3ee,
  0xf97316,
] as const;
const STEP_FALLBACK_COLOR = 0x94a3b8;
const WORLD_AXIS_LENGTH = 0.26;
const WORLD_AXIS_RADIUS = 0.0025; // 2.5 mm
const WORLD_AXIS_HEAD_LENGTH = 0.03;
const WORLD_AXIS_HEAD_RADIUS = 0.008;
const STEP_LOCAL_AXIS_LENGTH = 0.18;
const STEP_LOCAL_AXIS_RADIUS = 0.002;
const STEP_LOCAL_AXIS_HEAD_LENGTH = 0.022;
const STEP_LOCAL_AXIS_HEAD_RADIUS = 0.006;
const ORIENTATION_WIDGET_SIZE_PX = 120;
const ORIENTATION_WIDGET_MIN_SIZE_PX = 84;
const ORIENTATION_WIDGET_MARGIN_PX = 16;
const DEFAULT_STEP_TRANSFORM: StepTransform = {
  position: { x: 0, y: 0, z: 0 },
  rotationDeg: { x: 0, y: 0, z: 0 },
  scale: 1,
};

type OcctImporter = {
  ReadStepFile?: (
    content: Uint8Array,
    params?: Record<string, unknown> | null,
  ) => {
    success?: boolean;
    meshes?: Array<{
      name?: string;
      color?: number[];
      attributes?: {
        position?: { array?: number[] };
        normal?: { array?: number[] };
      };
      index?: { array?: number[] };
    }>;
  };
};

let occtImporterPromise: Promise<OcctImporter> | null = null;

export type StepTransform = {
  position: { x: number; y: number; z: number };
  rotationDeg: { x: number; y: number; z: number };
  scale: number;
};

export type StepLoadStatus = {
  state: "idle" | "loading" | "loaded" | "error";
  message: string;
};

async function loadOcctImporter(): Promise<OcctImporter> {
  if (!occtImporterPromise) {
    occtImporterPromise = import("occt-import-js").then(async (module) => {
      const init = (module as { default?: unknown }).default ?? module;
      if (typeof init !== "function") {
        throw new Error("STEP importer module is not callable.");
      }
      return (await (init as (opts?: Record<string, unknown>) => Promise<OcctImporter>)({
        locateFile: (path: string) => (path.endsWith(".wasm") ? occtWasmUrl : path),
      })) as OcctImporter;
    });
  }
  return occtImporterPromise;
}

function toThreeColor(color?: number[]): number {
  if (!Array.isArray(color) || color.length < 3) {
    return STEP_FALLBACK_COLOR;
  }
  const [r, g, b] = color;
  const max = Math.max(r, g, b);
  const normalized =
    max > 1
      ? [r / 255, g / 255, b / 255]
      : [Math.max(r, 0), Math.max(g, 0), Math.max(b, 0)];
  return new THREE.Color(normalized[0], normalized[1], normalized[2]).getHex();
}

function buildStepMesh(meshData: {
  name?: string;
  color?: number[];
  attributes?: {
    position?: { array?: number[] };
    normal?: { array?: number[] };
  };
  index?: { array?: number[] };
}): THREE.Mesh | null {
  const positions = meshData.attributes?.position?.array;
  if (!Array.isArray(positions) || positions.length < 9) {
    return null;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(positions, 3),
  );
  const normals = meshData.attributes?.normal?.array;
  if (Array.isArray(normals) && normals.length === positions.length) {
    geometry.setAttribute(
      "normal",
      new THREE.Float32BufferAttribute(normals, 3),
    );
  } else {
    geometry.computeVertexNormals();
  }
  const indices = meshData.index?.array;
  if (Array.isArray(indices) && indices.length > 0) {
    geometry.setIndex(indices);
  }
  geometry.computeBoundingBox();
  const material = new THREE.MeshStandardMaterial({
    color: toThreeColor(meshData.color),
    metalness: 0.25,
    roughness: 0.6,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = meshData.name ?? "step-mesh";
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function disposeObject3D(object: THREE.Object3D) {
  object.traverse((child) => {
    if ((child as THREE.Mesh).isMesh) {
      const mesh = child as THREE.Mesh;
      mesh.geometry.dispose();
      if (Array.isArray(mesh.material)) {
        mesh.material.forEach((material) => material.dispose());
      } else if (mesh.material) {
        mesh.material.dispose();
      }
      return;
    }
    if (child instanceof THREE.Line || child instanceof THREE.LineSegments) {
      child.geometry.dispose();
      if (Array.isArray(child.material)) {
        child.material.forEach((material) => material.dispose());
      } else {
        child.material.dispose();
      }
      return;
    }
    if (child instanceof THREE.Sprite) {
      const spriteMaterial = child.material as THREE.SpriteMaterial;
      spriteMaterial.map?.dispose();
      spriteMaterial.dispose();
      return;
    }
  });
}

function createAxisLabelSprite(
  label: string,
  color: number,
  scale: number,
): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 128;
  canvas.height = 128;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = `#${new THREE.Color(color).getHexString()}`;
    ctx.font = "bold 82px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(label, canvas.width / 2, canvas.height / 2);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false,
    depthWrite: false,
  });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(scale, scale, scale);
  sprite.renderOrder = 50;
  return sprite;
}

function createAxisArrow(
  direction: THREE.Vector3,
  color: number,
  options: {
    length: number;
    radius: number;
    headLength: number;
    headRadius: number;
  },
): THREE.Group {
  const { length, radius, headLength, headRadius } = options;
  const shaftLength = Math.max(length - headLength, length * 0.65);
  const shaft = new THREE.Mesh(
    new THREE.CylinderGeometry(radius, radius, shaftLength, 16),
    new THREE.MeshBasicMaterial({ color }),
  );
  shaft.position.y = shaftLength * 0.5;

  const tip = new THREE.Mesh(
    new THREE.ConeGeometry(headRadius, headLength, 16),
    new THREE.MeshBasicMaterial({ color }),
  );
  tip.position.y = shaftLength + headLength * 0.5;

  const group = new THREE.Group();
  group.add(shaft);
  group.add(tip);
  group.quaternion.setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    direction.clone().normalize(),
  );
  return group;
}

function createAxisTripod(options: {
  length: number;
  radius: number;
  headLength: number;
  headRadius: number;
  includeLabels: boolean;
  labelScale?: number;
  labelOffset?: number;
}): THREE.Group {
  const group = new THREE.Group();
  const axisDefs = [
    { axis: "x", dir: new THREE.Vector3(1, 0, 0), color: 0xef4444 },
    { axis: "y", dir: new THREE.Vector3(0, 1, 0), color: 0x22c55e },
    { axis: "z", dir: new THREE.Vector3(0, 0, 1), color: 0x3b82f6 },
  ] as const;

  axisDefs.forEach(({ axis, dir, color }) => {
    const arrow = createAxisArrow(dir, color, options);
    group.add(arrow);
    if (options.includeLabels) {
      const label = createAxisLabelSprite(
        axis.toUpperCase(),
        color,
        options.labelScale ?? 0.12,
      );
      const distance = options.length + (options.labelOffset ?? 0.07);
      label.position.copy(dir.clone().multiplyScalar(distance));
      group.add(label);
    }
  });

  return group;
}

function applyStepTransform(root: THREE.Group, transform?: StepTransform) {
  const next = transform ?? DEFAULT_STEP_TRANSFORM;
  // Apply STEP transform directly in scene/world axes.
  root.position.set(next.position.x, next.position.y, next.position.z);
  root.rotation.set(
    THREE.MathUtils.degToRad(next.rotationDeg.x),
    THREE.MathUtils.degToRad(next.rotationDeg.y),
    THREE.MathUtils.degToRad(next.rotationDeg.z),
  );
  const safeScale = Number.isFinite(next.scale)
    ? Math.max(1e-4, next.scale)
    : 1;
  root.scale.setScalar(safeScale);
}

export type ArmVisualizerHandle = {
  resetView: () => void;
};

export const ArmVisualizer = forwardRef(function ArmVisualizer(
  {
    joints,
    showBoundingBox,
    selectionMode,
    onPointSelected,
    pathPoints,
    waypoints,
    stepFile,
    stepTransform,
    onStepStatusChange,
  }: ArmVisualizerProps,
  ref: ForwardedRef<ArmVisualizerHandle>,
) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const robotRef = useRef<URDFRobot | null>(null);
  const targetAnglesRef = useRef<number[] | null>(null);
  const currentAnglesRef = useRef<number[] | null>(null);
  const previousTimeRef = useRef<number | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const initialControlsTarget = useRef(new THREE.Vector3(0.25, 0.15, 0));
  const defaultCameraOffset = useRef(new THREE.Vector3(1.15, 0.85, 1.6));
  const defaultCameraOffsetCaptured = useRef(false);
  const isGroundedRef = useRef(false);
  const boundingCenterRef = useRef(new THREE.Vector3());
  const pendingDynamicBoundsRef = useRef(false);
  const boundingWallsRef = useRef<THREE.Mesh[]>([]);
  const boundingEdgesRef = useRef<THREE.LineSegments | null>(null);
  const boundingMarkersRef = useRef<THREE.Object3D[]>([]);
  const setBoundsVisibilityRef = useRef<((visible: boolean) => void) | null>(null);
  const showBoundingBoxRef = useRef(showBoundingBox);
  const selectionModeRef = useRef(selectionMode);
  const onPointSelectedRef = useRef(onPointSelected);
  const previewGroupRef = useRef<THREE.Group | null>(null);
  const stepRootRef = useRef<THREE.Group | null>(null);
  const onStepStatusChangeRef = useRef(onStepStatusChange);
  const raycasterRef = useRef(new THREE.Raycaster());
  const pointerRef = useRef(new THREE.Vector2());
  const groundPlaneRef = useRef(new THREE.Plane(new THREE.Vector3(0, 0, 1), 0));

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#020617");
    sceneRef.current = scene;
    const raycaster = raycasterRef.current;
    const pointer = pointerRef.current;
    const groundPlane = groundPlaneRef.current;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.autoClear = false;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / Math.max(1, container.clientHeight),
      0.05,
      50,
    );
    camera.up.set(0, 0, 1);
    camera.position
      .copy(initialControlsTarget.current)
      .add(defaultCameraOffset.current);
    cameraRef.current = camera;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.target.copy(initialControlsTarget.current);
    controlsRef.current = controls;

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
    keyLight.position.set(1.5, 2, 1.5);
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x89cff0, 0.4);
    fillLight.position.set(-1.5, 1, -1.5);
    scene.add(fillLight);

    const hemiLight = new THREE.HemisphereLight(0x9be7ff, 0x0f172a, 0.3);
    scene.add(hemiLight);

    const grid = new THREE.GridHelper(
      GRID_SIZE,
      GRID_CELLS_PER_SIDE,
      0x38bdf8,
      0x1e293b,
    );
    // GridHelper is XZ by default (Y-up). Rotate into XY so Z becomes up.
    grid.rotation.x = Math.PI / 2;
    scene.add(grid);
    const worldAxes = createAxisTripod({
      length: WORLD_AXIS_LENGTH,
      radius: WORLD_AXIS_RADIUS,
      headLength: WORLD_AXIS_HEAD_LENGTH,
      headRadius: WORLD_AXIS_HEAD_RADIUS,
      includeLabels: false,
    });
    worldAxes.position.set(0, 0, 0);
    scene.add(worldAxes);
    const orientationScene = new THREE.Scene();
    const orientationAxes = createAxisTripod({
      length: 0.4,
      radius: 0.03,
      headLength: 0.09,
      headRadius: 0.06,
      includeLabels: true,
      labelScale: 0.13,
      labelOffset: 0.1,
    });
    orientationScene.add(orientationAxes);
    const orientationCamera = new THREE.OrthographicCamera(-0.8, 0.8, 0.8, -0.8, 0.01, 10);
    orientationCamera.position.set(0, 0, 2);
    orientationCamera.lookAt(0, 0, 0);

    const handlePointerDown = (event: PointerEvent) => {
      if (!selectionModeRef.current || !event.shiftKey || event.button !== 0) {
        return;
      }
      const camera = cameraRef.current;
      if (!camera) {
        return;
      }
      event.preventDefault();
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const intersection = new THREE.Vector3();
      if (raycaster.ray.intersectPlane(groundPlane, intersection)) {
        const callback = onPointSelectedRef.current;
        if (callback) {
          callback({
            x: intersection.x,
            y: intersection.y,
            z: Math.max(intersection.z, 0),
          });
        }
      }
    };

    const loader = new URDFLoader();
    const assetBasePath = "/assets/mini-6dof-arm/";
    const urdfPath = `${assetBasePath}mini-6dof-arm.urdf`;
    loader.workingPath = assetBasePath;
    const debugMarkers = boundingMarkersRef.current;
    const isFiniteBox = (box: THREE.Box3) =>
      Number.isFinite(box.min.x) &&
      Number.isFinite(box.min.y) &&
      Number.isFinite(box.min.z) &&
      Number.isFinite(box.max.x) &&
      Number.isFinite(box.max.y) &&
      Number.isFinite(box.max.z);

    const updateBoundingMarkers = (box: THREE.Box3) => {
      const corners = [
        new THREE.Vector3(box.min.x, box.min.y, box.min.z),
        new THREE.Vector3(box.min.x, box.min.y, box.max.z),
        new THREE.Vector3(box.min.x, box.max.y, box.min.z),
        new THREE.Vector3(box.min.x, box.max.y, box.max.z),
        new THREE.Vector3(box.max.x, box.min.y, box.min.z),
        new THREE.Vector3(box.max.x, box.min.y, box.max.z),
        new THREE.Vector3(box.max.x, box.max.y, box.min.z),
        new THREE.Vector3(box.max.x, box.max.y, box.max.z),
      ];

      if (debugMarkers.length === 0) {
        corners.forEach((corner, index) => {
          const marker = new THREE.Mesh(
            new THREE.SphereGeometry(0.005, 12, 12),
            new THREE.MeshBasicMaterial({
              color: BOUNDING_MARKER_COLORS[index % BOUNDING_MARKER_COLORS.length],
            }),
          );
          marker.position.copy(corner);
          scene.add(marker);
          debugMarkers.push(marker);
        });
      } else {
        debugMarkers.forEach((marker, index) => {
          marker.position.copy(corners[index]);
        });
      }
    };

    const wallConfigs = [
      {
        // Left wall (x = min)
        axis: "x" as const,
        sign: -1,
        rotation: new THREE.Euler(0, Math.PI / 2, 0),
        size: (size: THREE.Vector3) => new THREE.Vector2(size.z, size.y),
        position: (box: THREE.Box3, center: THREE.Vector3) =>
          new THREE.Vector3(box.min.x, center.y, center.z),
      },
      {
        // Right wall (x = max)
        axis: "x" as const,
        sign: 1,
        rotation: new THREE.Euler(0, -Math.PI / 2, 0),
        size: (size: THREE.Vector3) => new THREE.Vector2(size.z, size.y),
        position: (box: THREE.Box3, center: THREE.Vector3) =>
          new THREE.Vector3(box.max.x, center.y, center.z),
      },
      {
        // Front wall (z = max)
        axis: "z" as const,
        sign: 1,
        rotation: new THREE.Euler(0, 0, 0),
        size: (size: THREE.Vector3) => new THREE.Vector2(size.x, size.y),
        position: (box: THREE.Box3, center: THREE.Vector3) =>
          new THREE.Vector3(center.x, center.y, box.max.z),
      },
      {
        // Back wall (z = min)
        axis: "z" as const,
        sign: -1,
        rotation: new THREE.Euler(Math.PI, 0, 0),
        size: (size: THREE.Vector3) => new THREE.Vector2(size.x, size.y),
        position: (box: THREE.Box3, center: THREE.Vector3) =>
          new THREE.Vector3(center.x, center.y, box.min.z),
      },
      {
        // Ceiling (y = max)
        axis: "y" as const,
        sign: 1,
        rotation: new THREE.Euler(-Math.PI / 2, 0, 0),
        size: (size: THREE.Vector3) => new THREE.Vector2(size.x, size.z),
        position: (box: THREE.Box3, center: THREE.Vector3) =>
          new THREE.Vector3(center.x, box.max.y, center.z),
      },
      {
        // Floor hint (y = min)
        axis: "y" as const,
        sign: -1,
        rotation: new THREE.Euler(Math.PI / 2, 0, 0),
        size: (size: THREE.Vector3) => new THREE.Vector2(size.x, size.z),
        position: (box: THREE.Box3, center: THREE.Vector3) =>
          new THREE.Vector3(center.x, box.min.y, center.z),
      },
    ];

    const ensureBoundingWalls = (box: THREE.Box3) => {
      const size = box.getSize(new THREE.Vector3());
      const center = box.getCenter(new THREE.Vector3());
      const walls = boundingWallsRef.current;

      wallConfigs.forEach((config, index) => {
        let wall = walls[index];
        if (!wall) {
          const geometry = new THREE.PlaneGeometry(1, 1);
          const material = new THREE.MeshBasicMaterial({
            color: 0x38bdf8,
            transparent: true,
            opacity: 0.05,
            depthWrite: false,
            side: THREE.DoubleSide,
          });
          wall = new THREE.Mesh(geometry, material);
          wall.renderOrder = 5;
          walls[index] = wall;
          scene.add(wall);
        }

        const extent = config.size(size);
        wall.scale.set(Math.max(extent.x, 1e-6), Math.max(extent.y, 1e-6), 1);
        wall.position.copy(config.position(box, center));
        wall.rotation.copy(config.rotation);
      });
    };

    const ensureBoundingEdges = (box: THREE.Box3) => {
      const corners = [
        new THREE.Vector3(box.min.x, box.min.y, box.min.z),
        new THREE.Vector3(box.max.x, box.min.y, box.min.z),
        new THREE.Vector3(box.max.x, box.max.y, box.min.z),
        new THREE.Vector3(box.min.x, box.max.y, box.min.z),
        new THREE.Vector3(box.min.x, box.min.y, box.max.z),
        new THREE.Vector3(box.max.x, box.min.y, box.max.z),
        new THREE.Vector3(box.max.x, box.max.y, box.max.z),
        new THREE.Vector3(box.min.x, box.max.y, box.max.z),
      ];

      const indices = [
        0, 1, 1, 2, 2, 3, 3, 0, // bottom
        4, 5, 5, 6, 6, 7, 7, 4, // top
        0, 4, 1, 5, 2, 6, 3, 7, // verticals
      ];

      let edges = boundingEdgesRef.current;
      if (!edges) {
        const geometry = new THREE.BufferGeometry();
        const material = new THREE.LineBasicMaterial({
          color: 0x38bdf8,
          transparent: true,
          opacity: 0.25,
        });
        edges = new THREE.LineSegments(geometry, material);
        edges.renderOrder = 6;
        boundingEdgesRef.current = edges;
        scene.add(edges);
      }

      const positions = new Float32Array(indices.length * 3);
      indices.forEach((idx, arrayIndex) => {
        const vertex = corners[idx];
        positions[arrayIndex * 3] = vertex.x;
        positions[arrayIndex * 3 + 1] = vertex.y;
        positions[arrayIndex * 3 + 2] = vertex.z;
      });
      edges.geometry.setAttribute(
        "position",
        new THREE.BufferAttribute(positions, 3),
      );
      edges.geometry.computeBoundingSphere();
    };

    const updateBoundsVisibility = (visible: boolean) => {
      boundingMarkersRef.current.forEach((marker) => {
        marker.visible = visible;
      });
      boundingWallsRef.current.forEach((wall) => {
        wall.visible = visible;
      });
      if (boundingEdgesRef.current) {
        boundingEdgesRef.current.visible = visible;
      }
    };
    setBoundsVisibilityRef.current = updateBoundsVisibility;

    const alignToGroundAndUpdateBounds = (options?: {
      snapCamera?: boolean;
      applySnapshot?: boolean;
    }) => {
      const robot = robotRef.current;
      if (!robot) {
        return;
      }
      robot.updateMatrixWorld(true);

      const candidateNames = ["base", "base_link", "link0", "base_link_inertia"];
      let baseObject: THREE.Object3D | null = null;
      const linksRecord = robot.links as unknown as Record<
        string,
        THREE.Object3D | undefined
      >;
      for (const name of candidateNames) {
        const fromLinks = linksRecord?.[name];
        if (fromLinks) {
          baseObject = fromLinks;
          break;
        }
        const found = robot.getObjectByName(name);
        if (found) {
          baseObject = found;
          break;
        }
      }

      const baseSource =
        baseObject ?? linksRecord?.base ?? linksRecord?.base_link ?? robot;
      const baseBox = new THREE.Box3().setFromObject(baseSource);
      if (!isFiniteBox(baseBox)) {
        return;
      }

      const shouldApplyGrounding = !isGroundedRef.current;
      if (shouldApplyGrounding) {
        const deltaZ = baseBox.min.z;
        if (Number.isFinite(deltaZ) && Math.abs(deltaZ) > 1e-5) {
          robot.position.z -= deltaZ;
          robot.updateMatrixWorld(true);
        }
      }

      const groundedBBox = new THREE.Box3().setFromObject(robot);
      if (!isFiniteBox(groundedBBox)) {
        return;
      }

      const center = groundedBBox.getCenter(boundingCenterRef.current);
      initialControlsTarget.current.copy(center);

      updateBoundingMarkers(groundedBBox);
      ensureBoundingWalls(groundedBBox);
      ensureBoundingEdges(groundedBBox);
      updateBoundsVisibility(showBoundingBoxRef.current);

      if (options?.applySnapshot) {
        const values = targetAnglesRef.current;
        if (values) {
          currentAnglesRef.current = values.slice();
          values.forEach((value, index) => {
            const joint = robot.joints[`joint${index + 1}`];
            if (joint) {
              joint.setJointValue(value);
            }
          });
        }
      }

      const controlsInstance = controlsRef.current;
      const cameraInstance = cameraRef.current;
      if ((options?.snapCamera || shouldApplyGrounding) && controlsInstance && cameraInstance) {
        const offset = cameraInstance.position
          .clone()
          .sub(controlsInstance.target);
        controlsInstance.target.copy(initialControlsTarget.current);
        cameraInstance.position
          .copy(initialControlsTarget.current)
          .add(offset);
        cameraInstance.updateProjectionMatrix();
        controlsInstance.update();
        if (!defaultCameraOffsetCaptured.current) {
          defaultCameraOffset.current.copy(offset);
          defaultCameraOffsetCaptured.current = true;
        }
      }
    };

    const scheduleBoundingRefresh = () => {
      if (!isGroundedRef.current) {
        return;
      }
      pendingDynamicBoundsRef.current = true;
    };

    loader.load(
      urdfPath,
      (robot) => {
        console.info("[ArmVisualizer] URDF loaded", {
          jointNames: Object.keys(robot.joints),
          linkNames: Object.keys(robot.links),
        });
        robot.scale.setScalar(ROBOT_SCALE);
        const defaultMaterial = new THREE.MeshStandardMaterial({
          color: 0x1e293b,
          metalness: 0.1,
          roughness: 0.8,
        });
        const accentMaterial = new THREE.MeshStandardMaterial({
          color: 0x38bdf8,
          metalness: 0.2,
          roughness: 0.5,
        });

        robot.traverse((obj) => {
          if ((obj as THREE.Mesh).isMesh) {
            const mesh = obj as THREE.Mesh;
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            const material =
              mesh.name.toLowerCase().includes("wrist") ||
              mesh.name.toLowerCase().includes("tool")
                ? accentMaterial
                : defaultMaterial;

            if (Array.isArray(mesh.material)) {
              mesh.material.forEach((mat) => {
                (mat as THREE.Material).dispose();
              });
            } else if (mesh.material) {
              (mesh.material as THREE.Material).dispose();
            }
            mesh.material = material;
          }
        });

        scene.add(robot);

        robotRef.current = robot;
        if (!currentAnglesRef.current) {
          currentAnglesRef.current = new Array(6).fill(0);
        }
        if (!targetAnglesRef.current) {
          targetAnglesRef.current = new Array(6).fill(0);
        }

        const initialiseScene = () => {
          alignToGroundAndUpdateBounds({ snapCamera: true, applySnapshot: true });
          isGroundedRef.current = true;
        };

        initialiseScene();
        updateBoundsVisibility(showBoundingBoxRef.current);
        renderer.render(scene, camera);
      },
      undefined,
      (error) => {
        console.error("[ArmVisualizer] Failed to load URDF", {
          error,
          attemptedPath: urdfPath,
        });
      },
    );

    const handleResize = () => {
      if (!container) {
        return;
      }
      const { clientWidth, clientHeight } = container;
      renderer.setSize(clientWidth, clientHeight);
      camera.aspect = clientWidth / Math.max(clientHeight, 1);
      camera.updateProjectionMatrix();
    };

    let animationFrameId: number;
    const animate = (time?: number) => {
      animationFrameId = requestAnimationFrame(animate);

      const deltaSeconds =
        previousTimeRef.current !== null && time !== undefined
          ? Math.min((time - previousTimeRef.current) / 1000, 0.05)
          : 0.016;
      previousTimeRef.current = time ?? null;

      const targetAngles = targetAnglesRef.current;
      const robot = robotRef.current;
      let jointsChanged = false;
      if (robot && targetAngles && targetAngles.length > 0 && isGroundedRef.current) {
        if (!currentAnglesRef.current) {
          currentAnglesRef.current = targetAngles.slice();
        }
        const currentAngles = currentAnglesRef.current!;
        const jointsMap = robot.joints;
        const smoothing = 12; // rad/s tracking speed

        for (let index = 0; index < targetAngles.length; index += 1) {
          const jointName = `joint${index + 1}`;
          const joint = jointsMap[jointName];
          if (!joint) {
            continue;
          }
          const currentValue =
            typeof currentAngles[index] === "number" ? currentAngles[index] : 0;
          const targetValue = targetAngles[index];
          if (!Number.isFinite(targetValue)) {
            continue;
          }
          const blend = Math.min(1, deltaSeconds * smoothing);
          const blendFactor = Number.isFinite(blend) ? blend : 1;
          const nextValue = currentValue + (targetValue - currentValue) * blendFactor;
          if (Math.abs(nextValue - currentValue) > 1e-5) {
            jointsChanged = true;
          }
          joint.setJointValue(nextValue);
          currentAngles[index] = nextValue;
        }
      }

      if (jointsChanged) {
        scheduleBoundingRefresh();
      }

      if (pendingDynamicBoundsRef.current) {
        pendingDynamicBoundsRef.current = false;
        alignToGroundAndUpdateBounds({ snapCamera: false, applySnapshot: false });
      }

      controls.update();
      const canvasWidth = container.clientWidth;
      const canvasHeight = container.clientHeight;
      renderer.setViewport(0, 0, canvasWidth, canvasHeight);
      renderer.setScissorTest(false);
      renderer.clear();
      renderer.render(scene, camera);

      orientationAxes.quaternion.copy(camera.quaternion).invert();
      const maxWidgetSize = Math.round(
        Math.min(canvasWidth, canvasHeight) * 0.24,
      );
      const widgetSize = Math.max(
        ORIENTATION_WIDGET_MIN_SIZE_PX,
        Math.min(ORIENTATION_WIDGET_SIZE_PX, maxWidgetSize),
      );
      const widgetX = ORIENTATION_WIDGET_MARGIN_PX;
      const widgetY = ORIENTATION_WIDGET_MARGIN_PX;
      renderer.clearDepth();
      renderer.setScissor(widgetX, widgetY, widgetSize, widgetSize);
      renderer.setViewport(widgetX, widgetY, widgetSize, widgetSize);
      renderer.setScissorTest(true);
      renderer.render(orientationScene, orientationCamera);
      renderer.setScissorTest(false);
      renderer.setViewport(0, 0, canvasWidth, canvasHeight);
    };
    animate();

    renderer.domElement.addEventListener("pointerdown", handlePointerDown);
    window.addEventListener("resize", handleResize);

    return () => {
      renderer.domElement.removeEventListener("pointerdown", handlePointerDown);
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(animationFrameId);
      controls.dispose();
      controlsRef.current = null;
      renderer.dispose();
      grid.geometry.dispose();
      if (Array.isArray(grid.material)) {
        grid.material.forEach((material) => material.dispose());
      } else {
        grid.material.dispose();
      }
      scene.remove(worldAxes);
      disposeObject3D(worldAxes);
      disposeObject3D(orientationAxes);
      orientationScene.clear();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      const previewGroup = previewGroupRef.current;
      if (previewGroup) {
        disposeObject3D(previewGroup);
        scene.remove(previewGroup);
        previewGroupRef.current = null;
      }
      const stepRoot = stepRootRef.current;
      if (stepRoot) {
        disposeObject3D(stepRoot);
        scene.remove(stepRoot);
        stepRootRef.current = null;
      }
      boundingMarkersRef.current.forEach((marker) => {
        scene.remove(marker);
        marker.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            const meshChild = child as THREE.Mesh;
            meshChild.geometry.dispose();
            if (Array.isArray(meshChild.material)) {
              meshChild.material.forEach((mat) => mat.dispose());
            } else if (meshChild.material) {
              (meshChild.material as THREE.Material).dispose();
            }
          }
        });
      });
      boundingMarkersRef.current = [];
      scene.clear();
      sceneRef.current = null;
      robotRef.current = null;
      targetAnglesRef.current = null;
      currentAnglesRef.current = null;
      previousTimeRef.current = null;
      cameraRef.current = null;
      isGroundedRef.current = false;
      pendingDynamicBoundsRef.current = false;
      boundingWallsRef.current.forEach((wall) => {
        scene.remove(wall);
        if ((wall.material as THREE.Material | THREE.Material[])) {
          if (Array.isArray(wall.material)) {
            wall.material.forEach((mat) => mat.dispose());
          } else {
            (wall.material as THREE.Material).dispose();
          }
        }
        wall.geometry.dispose();
      });
      boundingWallsRef.current = [];
      const edges = boundingEdgesRef.current;
      if (edges) {
        scene.remove(edges);
        edges.geometry.dispose();
        (edges.material as THREE.Material).dispose();
        boundingEdgesRef.current = null;
      }
      setBoundsVisibilityRef.current = null;
    };
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      resetView: () => {
        const camera = cameraRef.current;
        const controls = controlsRef.current;
        if (!camera || !controls) {
          return;
        }
        controls.target.copy(initialControlsTarget.current);
        camera
          .position.copy(initialControlsTarget.current)
          .add(defaultCameraOffset.current);
        camera.updateProjectionMatrix();
        controls.update();
      },
    }),
    [],
  );

  useEffect(() => {
    selectionModeRef.current = selectionMode;
  }, [selectionMode]);

  useEffect(() => {
    onPointSelectedRef.current = onPointSelected;
  }, [onPointSelected]);

  useEffect(() => {
    onStepStatusChangeRef.current = onStepStatusChange;
  }, [onStepStatusChange]);

  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) {
      return;
    }
    const notify = (status: StepLoadStatus) => {
      onStepStatusChangeRef.current?.(status);
    };
    const clearStepRoot = () => {
      const existing = stepRootRef.current;
      if (existing) {
        scene.remove(existing);
        disposeObject3D(existing);
        stepRootRef.current = null;
      }
    };
    clearStepRoot();
    if (!stepFile) {
      notify({ state: "idle", message: "No STEP model loaded." });
      return;
    }

    let disposed = false;
    notify({ state: "loading", message: `Loading ${stepFile.name}...` });

    const run = async () => {
      try {
        const importer = await loadOcctImporter();
        if (disposed) {
          return;
        }
        const readStep = importer.ReadStepFile;
        if (typeof readStep !== "function") {
          throw new Error("STEP importer does not expose ReadStepFile.");
        }
        const bytes = new Uint8Array(await stepFile.arrayBuffer());
        const result = readStep(bytes, {
          linearUnit: "meter",
        });
        if (!result?.success) {
          throw new Error("Failed to parse STEP model.");
        }
        const meshes = Array.isArray(result.meshes) ? result.meshes : [];
        const modelGroup = new THREE.Group();
        modelGroup.name = "step-model";
        meshes.forEach((meshData) => {
          const mesh = buildStepMesh(meshData);
          if (mesh) {
            modelGroup.add(mesh);
          }
        });
        if (modelGroup.children.length === 0) {
          throw new Error("The STEP file does not contain renderable meshes.");
        }

        const modelBounds = new THREE.Box3().setFromObject(modelGroup);
        const center = modelBounds.getCenter(new THREE.Vector3());
        modelGroup.position.set(-center.x, -center.y, -modelBounds.min.z);

        const stepRoot = new THREE.Group();
        stepRoot.name = "step-root";
        const stepLocalAxes = createAxisTripod({
          length: STEP_LOCAL_AXIS_LENGTH,
          radius: STEP_LOCAL_AXIS_RADIUS,
          headLength: STEP_LOCAL_AXIS_HEAD_LENGTH,
          headRadius: STEP_LOCAL_AXIS_HEAD_RADIUS,
          includeLabels: false,
        });
        stepLocalAxes.name = "step-local-axes";
        stepRoot.add(modelGroup);
        stepRoot.add(stepLocalAxes);
        applyStepTransform(stepRoot, stepTransform);

        if (disposed) {
          disposeObject3D(stepRoot);
          return;
        }
        scene.add(stepRoot);
        stepRootRef.current = stepRoot;
        notify({
          state: "loaded",
          message: `Loaded ${stepFile.name} (${modelGroup.children.length} mesh${modelGroup.children.length === 1 ? "" : "es"}).`,
        });
      } catch (error) {
        if (disposed) {
          return;
        }
        notify({
          state: "error",
          message: `STEP load failed: ${(error as Error).message}`,
        });
      }
    };

    run();
    return () => {
      disposed = true;
      clearStepRoot();
    };
  }, [stepFile]);

  useEffect(() => {
    const stepRoot = stepRootRef.current;
    if (!stepRoot) {
      return;
    }
    applyStepTransform(stepRoot, stepTransform);
  }, [stepTransform]);

  useEffect(() => {
    if (!joints || joints.length === 0) {
      return;
    }
    targetAnglesRef.current = joints.slice();
    if (!currentAnglesRef.current) {
      currentAnglesRef.current = joints.slice();
    }
    if (!isGroundedRef.current) {
      return;
    }
    const robot = robotRef.current;
    if (robot) {
      joints.forEach((value, index) => {
        const joint = robot.joints[`joint${index + 1}`];
        if (joint) {
          joint.setJointValue(value);
        }
      });
      pendingDynamicBoundsRef.current = true;
    }
  }, [joints]);

  useEffect(() => {
    showBoundingBoxRef.current = showBoundingBox;
    const setter = setBoundsVisibilityRef.current;
    if (setter) {
      setter(showBoundingBox);
    }
  }, [showBoundingBox]);

  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) {
      return;
    }

    const disposeGroup = (group: THREE.Group | null) => {
      if (!group) {
        return;
      }
      group.traverse((object) => {
        if ((object as THREE.Mesh).isMesh) {
          const mesh = object as THREE.Mesh;
          mesh.geometry.dispose();
          if (Array.isArray(mesh.material)) {
            mesh.material.forEach((mat) => mat.dispose());
          } else {
            (mesh.material as THREE.Material).dispose();
          }
        } else if (object instanceof THREE.Line) {
          object.geometry.dispose();
          (object.material as THREE.Material).dispose();
        }
      });
    };

    if (previewGroupRef.current) {
      scene.remove(previewGroupRef.current);
      disposeGroup(previewGroupRef.current);
      previewGroupRef.current = null;
    }

    const pathList = Array.isArray(pathPoints)
      ? pathPoints.map(({ x, y, z }) => new THREE.Vector3(x, y, z))
      : [];
    const waypointList =
      Array.isArray(waypoints) && waypoints.length > 0
        ? waypoints.map(({ x, y, z }) => new THREE.Vector3(x, y, z))
        : [];

    if (pathList.length === 0 && waypointList.length === 0) {
      return;
    }

    const group = new THREE.Group();

    if (pathList.length >= 2) {
      const geometry = new THREE.BufferGeometry().setFromPoints(pathList);
      const material = new THREE.LineBasicMaterial({ color: 0xfacc15 });
      const line = new THREE.Line(geometry, material);
      group.add(line);
    }

    const markerSource =
      waypointList.length > 0 ? waypointList : pathList.length > 0 ? pathList : [];

    markerSource.forEach((point, index) => {
      const marker = new THREE.Mesh(
        new THREE.SphereGeometry(0.008, 12, 12),
        new THREE.MeshBasicMaterial({
          color: index === markerSource.length - 1 ? 0xfacc15 : 0xfef08a,
        }),
      );
      marker.position.copy(point);
      group.add(marker);
    });

    scene.add(group);
    previewGroupRef.current = group;

    return () => {
      scene.remove(group);
      disposeGroup(group);
      if (previewGroupRef.current === group) {
        previewGroupRef.current = null;
      }
    };
  }, [pathPoints, waypoints]);

  useEffect(() => {
    const canvas = containerRef.current?.querySelector("canvas");
    if (canvas) {
      canvas.style.cursor = selectionMode ? "crosshair" : "";
    }
  }, [selectionMode]);

  return <div ref={containerRef} className="absolute inset-0" />;
});
