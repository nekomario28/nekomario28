"use strict";

// Optional galaxy-motion layer. The force graph remains graph.js; this layer only
// adds continuous coordinate rotation after the force step. ?plain=1 disables it.
const galaxyPlainMode = new URLSearchParams(window.location.search).has("plain");

const galaxyOrbits = {
  initialized: false,
  lastTime: performance.now(),
  owner: null,
  membersByGroup: new Map(),
  parentByRepository: new Map(),
  repositorySpeeds: new Map(),
  lastGroupPositions: new Map(),
};

function galaxyOrbitMotionDisabled() {
  return galaxyPlainMode || motionMedia.matches;
}

function galaxyOrbitInitialize() {
  if (!state.nodes.length) return false;
  galaxyOrbits.owner = state.nodes.find((node) => node.type === "owner") || null;
  if (!galaxyOrbits.owner) return false;
  galaxyOrbits.membersByGroup.clear();
  galaxyOrbits.parentByRepository.clear();
  galaxyOrbits.repositorySpeeds.clear();
  galaxyOrbits.lastGroupPositions.clear();

  for (const node of state.nodes) {
    if (node.type === "group") {
      galaxyOrbits.membersByGroup.set(node.id, []);
      galaxyOrbits.lastGroupPositions.set(node.id, { x: node.x, y: node.y });
    }
  }

  for (const link of state.links) {
    if (link.type !== "member" || link.source?.type !== "group" || link.target?.type !== "repository") continue;
    const members = galaxyOrbits.membersByGroup.get(link.source.id) || [];
    members.push(link.target);
    galaxyOrbits.membersByGroup.set(link.source.id, members);
    if (!galaxyOrbits.parentByRepository.has(link.target.id)) {
      galaxyOrbits.parentByRepository.set(link.target.id, link.source);
    }
  }

  for (const [repositoryId] of galaxyOrbits.parentByRepository) {
    const seconds = 60 + (hash(`${repositoryId}:orbit-period`) % 37); // 60–96 s.
    const direction = hash(`${repositoryId}:orbit-direction`) % 2 === 0 ? 1 : -1;
    galaxyOrbits.repositorySpeeds.set(repositoryId, direction * (Math.PI * 2) / (seconds * 1000));
  }

  galaxyOrbits.lastTime = performance.now();
  galaxyOrbits.initialized = true;
  return true;
}

function rotatePoint(node, centerX, centerY, angle) {
  const dx = node.x - centerX;
  const dy = node.y - centerY;
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  node.x = centerX + dx * cosine - dy * sine;
  node.y = centerY + dx * sine + dy * cosine;
  const vx = node.vx || 0;
  const vy = node.vy || 0;
  node.vx = vx * cosine - vy * sine;
  node.vy = vx * sine + vy * cosine;
}

function translateGroupMembers(group, dx, dy) {
  if (Math.abs(dx) < 1e-9 && Math.abs(dy) < 1e-9) return;
  for (const member of galaxyOrbits.membersByGroup.get(group.id) || []) {
    if (state.dragging === member) continue;
    member.x += dx;
    member.y += dy;
  }
}

function galaxyOrbitStep(now = performance.now()) {
  if (galaxyOrbitMotionDisabled()) return;
  if (!galaxyOrbits.initialized && !galaxyOrbitInitialize()) return;

  const dt = clamp(now - galaxyOrbits.lastTime, 0, 50);
  galaxyOrbits.lastTime = now;
  if (dt <= 0) return;

  const owner = galaxyOrbits.owner;
  const categoryAngularSpeed = (Math.PI * 2) / (300 * 1000); // 5-minute revolution.

  // First level: each category rotates around the owner's current position. Moving
  // the category translates its repositories by the exact same delta, so the whole
  // local system travels together.
  for (const group of state.nodes.filter((node) => node.type === "group")) {
    const previous = galaxyOrbits.lastGroupPositions.get(group.id) || { x: group.x, y: group.y };

    if (state.dragging === group) {
      translateGroupMembers(group, group.x - previous.x, group.y - previous.y);
      galaxyOrbits.lastGroupPositions.set(group.id, { x: group.x, y: group.y });
      continue;
    }

    const beforeX = group.x;
    const beforeY = group.y;
    rotatePoint(group, owner.x, owner.y, categoryAngularSpeed * dt);
    translateGroupMembers(group, group.x - beforeX, group.y - beforeY);
    galaxyOrbits.lastGroupPositions.set(group.id, { x: group.x, y: group.y });
  }

  // Second level: every repository independently rotates around the category after
  // the category itself has moved. This is direct coordinate motion, not an anchor,
  // so it remains visible even after the force simulation has cooled completely.
  for (const [repositoryId, parent] of galaxyOrbits.parentByRepository) {
    const node = state.nodeById.get(repositoryId);
    if (!node || state.dragging === node || state.dragging === parent) continue;
    rotatePoint(node, parent.x, parent.y, (galaxyOrbits.repositorySpeeds.get(repositoryId) || 0) * dt);
  }
}

const galaxyOrbitBaseApplyForces = applyForces;
applyForces = function applyForcesWithDoubleOrbit() {
  galaxyOrbitBaseApplyForces();
  galaxyOrbitStep();
  if (!galaxyOrbitMotionDisabled()) resolveNodeCollisions(0.92, 3);
};

function syncGalaxyCopy() {
  if (!galaxyOrbitMotionDisabled()) return;
  if (detailsDescription) {
    detailsDescription.textContent = galaxyPlainMode
      ? "Force-only baseline: center, repel, link force and link distance. Drag nodes, pan empty space, and scroll or pinch to zoom."
      : "Motion is reduced by your system preference. The underlying force graph remains interactive.";
  }
  const title = interactionHint?.querySelector("strong");
  const text = interactionHint?.querySelector("span");
  if (title) title.textContent = "Explore the force graph";
  if (text) text.textContent = "Drag nodes · Pan empty space · Scroll or pinch to zoom";
}

motionMedia.addEventListener("change", () => {
  galaxyOrbits.lastTime = performance.now();
  syncGalaxyCopy();
});
requestAnimationFrame(syncGalaxyCopy);