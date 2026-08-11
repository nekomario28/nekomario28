"use strict";

// Optional galaxy-motion layer. Motion is continuous force steering rather than
// direct coordinate rotation: nodes keep inertia, avoid one another, and gently
// return toward their orbital bands. ?plain=1 disables this layer.
const galaxyPlainMode = new URLSearchParams(window.location.search).has("plain");

const galaxyOrbits = {
  initialized: false,
  lastTime: performance.now(),
  owner: null,
  ownerHome: null,
  groupTargets: new Map(),
  repositoryTargets: new Map(),
};

function galaxyOrbitMotionDisabled() {
  return galaxyPlainMode || motionMedia.matches;
}

function galaxyOrbitInitialize() {
  if (!state.nodes.length) return false;
  // Let the ordinary force graph establish its shape before orbital steering learns
  // the local radii. This keeps the galaxy layer subordinate to the graph structure.
  if (performance.now() - state.startedAt < 140) return false;

  const owner = state.nodes.find((node) => node.type === "owner") || null;
  if (!owner) return false;

  galaxyOrbits.owner = owner;
  galaxyOrbits.ownerHome = { x: owner.x, y: owner.y };
  galaxyOrbits.groupTargets.clear();
  galaxyOrbits.repositoryTargets.clear();

  for (const group of state.nodes.filter((node) => node.type === "group")) {
    const currentRadius = Math.hypot(group.x - owner.x, group.y - owner.y);
    const preferred = 285 + (hash(`${group.id}:galaxy-radius`) % 96);
    const targetRadius = clamp(Math.max(currentRadius, preferred), 270, 430);
    const periodSeconds = 420 + (hash(`${group.id}:galaxy-period`) % 81); // 7.0–8.3 min.
    galaxyOrbits.groupTargets.set(group.id, {
      node: group,
      targetRadius,
      angularSpeed: (Math.PI * 2) / periodSeconds,
    });
  }

  for (const link of state.links) {
    if (link.type !== "member" || link.source?.type !== "group" || link.target?.type !== "repository") continue;
    if (galaxyOrbits.repositoryTargets.has(link.target.id)) continue;

    const repository = link.target;
    const parent = link.source;
    const currentRadius = Math.hypot(repository.x - parent.x, repository.y - parent.y);
    const preferred = 155 + (hash(`${repository.id}:local-radius`) % 121);
    const targetRadius = clamp(Math.max(currentRadius, preferred), 150, 300);
    const periodSeconds = 120 + (hash(`${repository.id}:local-period`) % 61); // 2–3 min.
    galaxyOrbits.repositoryTargets.set(repository.id, {
      node: repository,
      parent,
      targetRadius,
      angularSpeed: (Math.PI * 2) / periodSeconds,
    });
  }

  galaxyOrbits.lastTime = performance.now();
  galaxyOrbits.initialized = true;
  return true;
}

function steerOwnerHome(frameScale) {
  const owner = galaxyOrbits.owner;
  if (!owner) return;

  // Dragging the central node deliberately moves the galaxy's center. On release,
  // that location becomes the new equilibrium rather than snapping back.
  if (state.dragging === owner) {
    galaxyOrbits.ownerHome = { x: owner.x, y: owner.y };
    return;
  }

  if (!galaxyOrbits.ownerHome) galaxyOrbits.ownerHome = { x: owner.x, y: owner.y };
  const dx = galaxyOrbits.ownerHome.x - owner.x;
  const dy = galaxyOrbits.ownerHome.y - owner.y;
  const distance = Math.hypot(dx, dy);
  const adaptiveSpring = 0.00072 * (1 + clamp(distance / 180, 0, 1.6));

  owner.vx += dx * adaptiveSpring * frameScale;
  owner.vy += dy * adaptiveSpring * frameScale;

  // A heavy body still moves, but it does not accumulate an endless drift velocity.
  const damping = Math.pow(0.988, frameScale);
  owner.vx *= damping;
  owner.vy *= damping;
}

function steerOrbit(node, center, targetRadius, angularSpeed, frameScale, options = {}) {
  if (!node || !center || state.dragging === node) return;

  let dx = node.x - center.x;
  let dy = node.y - center.y;
  let radius = Math.hypot(dx, dy);
  if (radius < 1) {
    const angle = (hash(`${node.id}:orbit-seed`) % 6283) / 1000;
    dx = Math.cos(angle);
    dy = Math.sin(angle);
    radius = 1;
  }

  const ux = dx / radius;
  const uy = dy / radius;
  const tx = -uy;
  const ty = ux;
  const radialVelocity = (node.vx || 0) * ux + (node.vy || 0) * uy;
  const tangentialVelocity = (node.vx || 0) * tx + (node.vy || 0) * ty;

  // angularSpeed is radians/second; graph velocity is effectively world-units/frame.
  const desiredTangentialVelocity = (angularSpeed * radius) / 60;
  const radialError = targetRadius - radius;
  const radialStiffness = options.radialStiffness ?? 0.00055;
  const radialDamping = options.radialDamping ?? 0.035;
  const tangentialGain = options.tangentialGain ?? 0.018;

  const radialAcceleration =
    (radialError * radialStiffness - radialVelocity * radialDamping) * frameScale;
  const tangentialAcceleration =
    (desiredTangentialVelocity - tangentialVelocity) * tangentialGain * frameScale;

  node.vx += ux * radialAcceleration + tx * tangentialAcceleration;
  node.vy += uy * radialAcceleration + ty * tangentialAcceleration;
}

function limitGalaxySpeed(node) {
  if (!node || state.dragging === node) return;
  const speed = Math.hypot(node.vx || 0, node.vy || 0);
  const maximum = node.type === "owner" ? 0.24 : node.type === "group" ? 0.62 : node.type === "repository" ? 1.05 : 0.45;
  if (speed <= maximum || speed < 0.001) return;
  const scale = maximum / speed;
  node.vx *= scale;
  node.vy *= scale;
}

function galaxyOrbitStep(now = performance.now()) {
  if (galaxyOrbitMotionDisabled()) return;
  if (!galaxyOrbits.initialized && !galaxyOrbitInitialize()) return;

  const dt = clamp(now - galaxyOrbits.lastTime, 0, 50);
  galaxyOrbits.lastTime = now;
  if (dt <= 0) return;
  const frameScale = dt / (1000 / 60);

  steerOwnerHome(frameScale);

  for (const target of galaxyOrbits.groupTargets.values()) {
    steerOrbit(target.node, galaxyOrbits.owner, target.targetRadius, target.angularSpeed, frameScale, {
      radialStiffness: 0.00042,
      radialDamping: 0.030,
      tangentialGain: 0.014,
    });
  }

  for (const target of galaxyOrbits.repositoryTargets.values()) {
    if (state.dragging === target.parent) continue;
    steerOrbit(target.node, target.parent, target.targetRadius, target.angularSpeed, frameScale, {
      radialStiffness: 0.00072,
      radialDamping: 0.040,
      tangentialGain: 0.022,
    });
  }

  // Predictive avoidance bends trajectories before nodes overlap. It never teleports
  // or zeroes velocity, so close encounters look like flowing paths rather than stops.
  if (typeof applyNaturalAvoidance === "function") applyNaturalAvoidance(1, 1);

  for (const node of state.nodes) limitGalaxySpeed(node);

  // Once the baseline force simulation has cooled, this layer becomes the integrator
  // so the graph keeps moving indefinitely without reheating or snapping.
  if (state.alpha < 0.001) {
    for (const node of state.nodes) {
      if (node.fixed || state.dragging === node) continue;
      node.vx *= node.type === "repository" ? 0.9985 : 0.9975;
      node.vy *= node.type === "repository" ? 0.9985 : 0.9975;
      node.x += node.vx * frameScale;
      node.y += node.vy * frameScale;
    }
  }
}

const galaxyOrbitBaseApplyForces = applyForces;
applyForces = function applyForcesWithContinuousGalaxyMotion() {
  galaxyOrbitBaseApplyForces();
  galaxyOrbitStep();
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

resetButton.addEventListener("click", () => {
  galaxyOrbits.initialized = false;
  galaxyOrbits.ownerHome = null;
  galaxyOrbits.lastTime = performance.now();
});

motionMedia.addEventListener("change", () => {
  galaxyOrbits.lastTime = performance.now();
  syncGalaxyCopy();
});
requestAnimationFrame(syncGalaxyCopy);
