"use strict";

// Optional double-orbit motion layered on top of the Obsidian-style force graph.
// graph.js remains the behavioral baseline. Add ?plain=1 to disable this layer.
const galaxyOrbitDisabled = new URLSearchParams(window.location.search).has("plain") || motionMedia.matches;

const galaxyOrbits = {
  initialized: false,
  lastTime: performance.now(),
  groups: new Map(),
  repositories: new Map(),
};

function galaxyOrbitClusterId(node) {
  if (!node) return null;
  if (node.type === "group") return node.id;
  if (node.type === "repository") return galaxyOrbits.repositories.get(node.id)?.parent?.id || null;
  return null;
}

function galaxyOrbitInitialize() {
  if (!state.nodes.length) return false;

  galaxyOrbits.groups.clear();
  galaxyOrbits.repositories.clear();
  const owner = state.nodes.find((node) => node.type === "owner");
  if (!owner) return false;

  // Keep all categories on one shared slow angular velocity so their relative
  // separation is stable. One full revolution takes five minutes.
  const categoryAngularSpeed = (Math.PI * 2) / (300 * 1000);

  for (const node of state.nodes) {
    if (node.type !== "group") continue;
    const dx = node.anchorX - owner.x;
    const dy = node.anchorY - owner.y;
    const flatten = 0.78;
    const radius = Math.max(125, Math.hypot(dx, dy / flatten));
    galaxyOrbits.groups.set(node.id, {
      node,
      owner,
      radius,
      flatten,
      phase: Math.atan2(dy / flatten, dx),
      angularSpeed: categoryAngularSpeed,
    });
  }

  for (const link of state.links) {
    if (link.type !== "member" || link.source?.type !== "group" || link.target?.type !== "repository") continue;
    const node = link.target;
    const parent = link.source;
    const dx = node.anchorX - parent.x;
    const dy = node.anchorY - parent.y;
    const flatten = 0.74 + (hash(node.id) % 9) / 100;
    const radius = Math.max(64, Math.hypot(dx, dy / flatten));
    const seconds = 68 + (hash(`${node.id}:period`) % 39); // 68–106 seconds.
    const direction = hash(`${node.id}:direction`) % 2 === 0 ? 1 : -1;
    galaxyOrbits.repositories.set(node.id, {
      node,
      parent,
      radius,
      flatten,
      phase: Math.atan2(dy / flatten, dx),
      angularSpeed: direction * (Math.PI * 2) / (seconds * 1000),
    });
  }

  galaxyOrbits.lastTime = performance.now();
  galaxyOrbits.initialized = true;
  return true;
}

function galaxyOrbitPausedClusters() {
  const paused = new Set();
  for (const node of [state.hovered, state.selected, state.dragging]) {
    const cluster = galaxyOrbitClusterId(node);
    if (cluster) paused.add(cluster);
  }
  return paused;
}

function galaxyOrbitUpdateDraggedGeometry() {
  // If a user drags a node, reinterpret the new position as a new point on its
  // orbit rather than snapping it back to the old phase/radius after release.
  const node = state.dragging;
  if (!node) return;

  if (node.type === "group") {
    const orbit = galaxyOrbits.groups.get(node.id);
    if (!orbit) return;
    const dx = node.x - orbit.owner.x;
    const dy = node.y - orbit.owner.y;
    orbit.radius = Math.max(90, Math.hypot(dx, dy / orbit.flatten));
    orbit.phase = Math.atan2(dy / orbit.flatten, dx);
    node.anchorX = node.x;
    node.anchorY = node.y;
    return;
  }

  if (node.type === "repository") {
    const orbit = galaxyOrbits.repositories.get(node.id);
    if (!orbit) return;
    const dx = node.x - orbit.parent.x;
    const dy = node.y - orbit.parent.y;
    orbit.radius = Math.max(48, Math.hypot(dx, dy / orbit.flatten));
    orbit.phase = Math.atan2(dy / orbit.flatten, dx);
    node.anchorX = node.x;
    node.anchorY = node.y;
  }
}

function galaxyOrbitStep(now = performance.now()) {
  if (galaxyOrbitDisabled) return;
  if (!galaxyOrbits.initialized && !galaxyOrbitInitialize()) return;

  const dt = clamp(now - galaxyOrbits.lastTime, 0, 50);
  galaxyOrbits.lastTime = now;
  if (dt <= 0) return;

  galaxyOrbitUpdateDraggedGeometry();
  const paused = galaxyOrbitPausedClusters();

  // First orbit categories around the owner.
  for (const orbit of galaxyOrbits.groups.values()) {
    const { node, owner } = orbit;
    if (state.dragging === node || paused.has(node.id)) continue;
    orbit.phase += orbit.angularSpeed * dt;
    node.anchorX = owner.x + Math.cos(orbit.phase) * orbit.radius;
    node.anchorY = owner.y + Math.sin(orbit.phase) * orbit.radius * orbit.flatten;
  }

  // Then orbit repositories around the category's *current* location. This gives
  // the visible two-level motion: the whole system travels while its projects spin.
  for (const orbit of galaxyOrbits.repositories.values()) {
    const { node, parent } = orbit;
    if (state.dragging === node || paused.has(parent.id)) continue;
    orbit.phase += orbit.angularSpeed * dt;
    node.anchorX = parent.x + Math.cos(orbit.phase) * orbit.radius;
    node.anchorY = parent.y + Math.sin(orbit.phase) * orbit.radius * orbit.flatten;
  }
}

const galaxyOrbitBaseApplyForces = applyForces;
applyForces = function applyForcesWithDoubleOrbit() {
  galaxyOrbitStep();
  galaxyOrbitBaseApplyForces();
};

motionMedia.addEventListener("change", () => {
  galaxyOrbits.lastTime = performance.now();
});
