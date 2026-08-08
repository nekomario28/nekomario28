"use strict";

// Real orbital motion layered over the stable galaxy layout. Repository anchors
// slowly orbit their category; the existing force/collision solver follows those
// anchors so labels remain readable instead of being teleported every frame.
const galaxyMotion = {
  repositories: new Map(),
  lastTime: performance.now(),
  initialized: false,
  dragCandidate: null,
  activePointers: new Set(),
};

function galaxyMotionParent(node) {
  const parentId = galaxyLayout.parentByRepository.get(node.id);
  return parentId ? state.nodeById.get(parentId) : null;
}

function galaxyMotionClusterId(node) {
  if (!node) return null;
  if (node.type === "group") return node.id;
  if (node.type === "repository") return galaxyLayout.parentByRepository.get(node.id) || null;
  return null;
}

function galaxyMotionInitialize() {
  galaxyMotion.repositories.clear();

  for (const node of state.nodes) {
    if (node.type !== "repository") continue;
    const parent = galaxyMotionParent(node);
    if (!parent) continue;

    const dx = node.anchorX - parent.x;
    const dy = node.anchorY - parent.y;
    const flatten = 0.78;
    const radius = Math.max(62, Math.hypot(dx, dy / flatten));
    const phase = Math.atan2(dy / flatten, dx);
    const seconds = 72 + (hash(node.id) % 49); // 72–120 second orbit.
    const direction = hash(`${node.id}:orbit-direction`) % 2 === 0 ? 1 : -1;

    galaxyMotion.repositories.set(node.id, {
      node,
      parent,
      radius,
      flatten,
      phase,
      angularSpeed: direction * (Math.PI * 2) / (seconds * 1000),
      detached: false,
    });
  }

  galaxyMotion.lastTime = performance.now();
  galaxyMotion.initialized = true;
}

function galaxyMotionPausedClusters() {
  const paused = new Set();
  for (const node of [state.hovered, state.selected, state.dragging]) {
    const clusterId = galaxyMotionClusterId(node);
    if (clusterId) paused.add(clusterId);
  }
  return paused;
}

function galaxyMotionStep(now = performance.now()) {
  if (!galaxyMotion.initialized || galaxyMotion.repositories.size === 0) {
    galaxyMotionInitialize();
  }

  const dt = clamp(now - galaxyMotion.lastTime, 0, 50);
  galaxyMotion.lastTime = now;
  if (motionMedia.matches || dt <= 0 || galaxyMotion.activePointers.size > 0) return;

  const pausedClusters = galaxyMotionPausedClusters();

  for (const orbit of galaxyMotion.repositories.values()) {
    const { node, parent } = orbit;
    if (orbit.detached || !parent || node === state.dragging) continue;
    if (pausedClusters.has(parent.id)) continue;

    orbit.phase += orbit.angularSpeed * dt;
    const targetX = parent.x + Math.cos(orbit.phase) * orbit.radius;
    const targetY = parent.y + Math.sin(orbit.phase) * orbit.radius * orbit.flatten;

    node.anchorX = targetX;
    node.anchorY = targetY;
  }
}

const galaxyMotionApplyForcesBase = applyForces;
applyForces = function applyGalaxyForcesWithOrbit() {
  galaxyMotionStep();
  galaxyMotionApplyForcesBase();
};

// A manually dragged repository becomes a free star. Reflow reattaches it to the
// deterministic orbital system. Categories still drag their whole cluster.
canvas.addEventListener("pointerdown", () => {
  galaxyMotion.dragCandidate = state.dragging?.type === "repository" ? state.dragging : null;
});

canvas.addEventListener("pointerup", () => {
  const node = galaxyMotion.dragCandidate;
  galaxyMotion.dragCandidate = null;
  if (!node) return;
  const orbit = galaxyMotion.repositories.get(node.id);
  if (!orbit) return;
  orbit.detached = true;
  node.anchorX = node.x;
  node.anchorY = node.y;
});

canvas.addEventListener("pointercancel", () => {
  galaxyMotion.dragCandidate = null;
});

// Pause orbital advance while a pointer gesture is active. This prevents targets
// from sliding under a mouse/finger during click, drag or pinch interactions.
canvas.addEventListener("pointerdown", (event) => {
  galaxyMotion.activePointers.add(event.pointerId);
});
canvas.addEventListener("pointerup", (event) => {
  galaxyMotion.activePointers.delete(event.pointerId);
  galaxyMotion.lastTime = performance.now();
});
canvas.addEventListener("pointercancel", (event) => {
  galaxyMotion.activePointers.delete(event.pointerId);
  galaxyMotion.lastTime = performance.now();
});

const galaxyMotionReflowBase = galaxyReflow;
galaxyReflow = function galaxyReflowWithOrbitReset() {
  galaxyMotion.initialized = false;
  galaxyMotion.repositories.clear();
  galaxyMotionReflowBase();
  galaxyMotionInitialize();
};

motionMedia.addEventListener("change", () => {
  galaxyMotion.lastTime = performance.now();
});
