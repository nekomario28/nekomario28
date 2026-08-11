"use strict";

// Experimental galaxy structure for the redesign branch.
// Every repository orbits the same galactic center. Category nodes are semantic
// sector labels that follow the centroid of their repositories; they are never
// local gravity centers. ?plain=1 leaves the force-only baseline untouched.
const galaxyPlainMode = new URLSearchParams(window.location.search).has("plain");
const TAU = Math.PI * 2;

const galaxyStructure = {
  initialized: false,
  lastTime: performance.now(),
  owner: null,
  ownerHome: null,
  categories: new Map(),
  repositories: new Map(),
};

function galaxyStructureMotionDisabled() {
  return galaxyPlainMode || motionMedia.matches;
}

function wrapAngle(angle) {
  let value = angle % TAU;
  if (value > Math.PI) value -= TAU;
  if (value < -Math.PI) value += TAU;
  return value;
}

function galaxyAngularSpeedForRadius(radius) {
  // Differential rotation for the visualization: outer projects advance more
  // slowly in angle than inner projects. Periods are deliberately time-compressed.
  const normalized = clamp((radius - 190) / 330, 0, 1);
  const periodSeconds = 250 + normalized * 210; // about 4.2–7.7 minutes.
  return TAU / periodSeconds;
}

function categoryMembersFromLinks() {
  const members = new Map();
  for (const node of state.nodes) {
    if (node.type === "group") members.set(node.id, []);
  }
  for (const link of state.links) {
    if (link.type !== "member" || link.source?.type !== "group" || link.target?.type !== "repository") continue;
    const groupMembers = members.get(link.source.id);
    if (groupMembers) groupMembers.push(link.target);
  }
  for (const groupMembers of members.values()) {
    groupMembers.sort((a, b) => String(a.id).localeCompare(String(b.id)));
  }
  return members;
}

function repositoryPlannedRadius(repository, slotIndex) {
  const lane = slotIndex % 3;
  const tier = Math.floor(slotIndex / 3);
  const jitter = (hash(`${repository.id}:galaxy-radius`) % 25) - 12;
  return clamp(220 + lane * 92 + tier * 34 + jitter, 205, 505);
}

function galaxyStructureInitialize() {
  if (!state.nodes.length) return false;
  if (performance.now() - state.startedAt < 180) return false;

  const owner = state.nodes.find((node) => node.type === "owner") || null;
  if (!owner) return false;

  galaxyStructure.owner = owner;
  galaxyStructure.ownerHome = { x: owner.x, y: owner.y };
  galaxyStructure.categories.clear();
  galaxyStructure.repositories.clear();

  const memberMap = categoryMembersFromLinks();
  const groups = state.nodes
    .filter((node) => node.type === "group")
    .sort((a, b) => String(a.id).localeCompare(String(b.id)));
  const categoryCount = Math.max(1, groups.length);

  groups.forEach((group, groupIndex) => {
    const members = memberMap.get(group.id) || [];
    const basePhase = -Math.PI / 2 + (TAU * groupIndex) / categoryCount;
    const sectorWidth = Math.min(0.92, (TAU / categoryCount) * 0.56);
    const category = {
      node: group,
      members,
      basePhase,
      armPhase: basePhase,
      sectorWidth,
      patternSpeed: 0,
    };

    let speedTotal = 0;
    members.forEach((repository, slotIndex) => {
      const targetRadius = repositoryPlannedRadius(repository, slotIndex);
      const slotCenter = members.length <= 1 ? 0 : slotIndex / (members.length - 1) - 0.5;
      const spiralOffset = ((targetRadius - 220) / 285) * 0.42;
      const phaseOffset = slotCenter * sectorWidth + spiralOffset;
      const angularSpeed = galaxyAngularSpeedForRadius(targetRadius);
      speedTotal += angularSpeed;

      galaxyStructure.repositories.set(repository.id, {
        node: repository,
        category,
        targetRadius,
        phaseOffset,
        angularSpeed,
      });
    });

    category.patternSpeed = members.length ? (speedTotal / members.length) * 0.94 : TAU / 420;
    galaxyStructure.categories.set(group.id, category);
  });

  // The galaxy mode has its own deterministic initial geometry. This is a one-time
  // layout operation, not a collision response: motion after this point is velocity
  // steering only.
  for (const target of galaxyStructure.repositories.values()) {
    const phase = target.category.armPhase + target.phaseOffset;
    const radius = target.targetRadius;
    target.node.x = owner.x + Math.cos(phase) * radius;
    target.node.y = owner.y + Math.sin(phase) * radius;
    const tangential = (target.angularSpeed * radius) / 60;
    target.node.vx = -Math.sin(phase) * tangential;
    target.node.vy = Math.cos(phase) * tangential;
  }

  for (const category of galaxyStructure.categories.values()) {
    positionCategoryAtCentroid(category, true);
  }

  owner.vx = 0;
  owner.vy = 0;
  galaxyStructure.lastTime = performance.now();
  galaxyStructure.initialized = true;
  fitView(false);
  return true;
}

function positionCategoryAtCentroid(category, immediate = false) {
  const group = category?.node;
  if (!group || state.dragging === group) return;
  const members = category.members.filter((node) => Number.isFinite(node.x) && Number.isFinite(node.y));
  if (!members.length) return;

  let x = 0;
  let y = 0;
  let vx = 0;
  let vy = 0;
  for (const member of members) {
    x += member.x;
    y += member.y;
    vx += member.vx || 0;
    vy += member.vy || 0;
  }
  x /= members.length;
  y /= members.length;
  vx /= members.length;
  vy /= members.length;

  if (immediate) {
    group.x = x;
    group.y = y;
    group.vx = vx;
    group.vy = vy;
    return;
  }

  // Category nodes are labels for moving sectors, not bodies that repositories orbit.
  group.vx += (x - group.x) * 0.0011;
  group.vy += (y - group.y) * 0.0011;
  group.vx += (vx - group.vx) * 0.012;
  group.vy += (vy - group.vy) * 0.012;
}

function steerOwnerHome(frameScale) {
  const owner = galaxyStructure.owner;
  if (!owner) return;
  if (state.dragging === owner) {
    galaxyStructure.ownerHome = { x: owner.x, y: owner.y };
    return;
  }
  if (!galaxyStructure.ownerHome) galaxyStructure.ownerHome = { x: owner.x, y: owner.y };

  const dx = galaxyStructure.ownerHome.x - owner.x;
  const dy = galaxyStructure.ownerHome.y - owner.y;
  const distance = Math.hypot(dx, dy);
  const spring = 0.00082 * (1 + clamp(distance / 180, 0, 1.5));
  owner.vx += dx * spring * frameScale;
  owner.vy += dy * spring * frameScale;
  const damping = Math.pow(0.986, frameScale);
  owner.vx *= damping;
  owner.vy *= damping;
}

function steerRepository(target, frameScale) {
  const node = target.node;
  const owner = galaxyStructure.owner;
  if (!node || !owner || state.dragging === node) return;

  let dx = node.x - owner.x;
  let dy = node.y - owner.y;
  let radius = Math.hypot(dx, dy);
  if (radius < 1) {
    const seed = (hash(`${node.id}:galaxy-phase`) % 6283) / 1000;
    dx = Math.cos(seed);
    dy = Math.sin(seed);
    radius = 1;
  }

  const ux = dx / radius;
  const uy = dy / radius;
  const tx = -uy;
  const ty = ux;
  const radialVelocity = (node.vx || 0) * ux + (node.vy || 0) * uy;
  const tangentialVelocity = (node.vx || 0) * tx + (node.vy || 0) * ty;
  const desiredTangential = (target.angularSpeed * radius) / 60;

  const radialError = target.targetRadius - radius;
  const radialAcceleration = (radialError * 0.00034 - radialVelocity * 0.034) * frameScale;

  // A very weak density-wave pull keeps each semantic category recognizable without
  // making the category itself a gravity center. Repositories still have different
  // angular speeds by radius, so the arm slowly shears instead of rotating rigidly.
  const currentPhase = Math.atan2(dy, dx);
  const desiredPhase = target.category.armPhase + target.phaseOffset;
  const phaseError = wrapAngle(desiredPhase - currentPhase);
  const phaseAcceleration = clamp(phaseError * radius * 0.000018, -0.010, 0.010) * frameScale;
  const tangentialAcceleration =
    ((desiredTangential - tangentialVelocity) * 0.020 + phaseAcceleration) * frameScale;

  node.vx += ux * radialAcceleration + tx * tangentialAcceleration;
  node.vy += uy * radialAcceleration + ty * tangentialAcceleration;
}

function limitGalaxyStructureSpeed(node) {
  if (!node || state.dragging === node) return;
  const speed = Math.hypot(node.vx || 0, node.vy || 0);
  const maximum = node.type === "owner" ? 0.22 : node.type === "group" ? 0.58 : 0.82;
  if (speed <= maximum || speed < 0.001) return;
  const scale = maximum / speed;
  node.vx *= scale;
  node.vy *= scale;
}

function galaxyStructureStep(now = performance.now()) {
  if (galaxyStructureMotionDisabled()) return;
  if (!galaxyStructure.initialized && !galaxyStructureInitialize()) return;

  const dt = clamp(now - galaxyStructure.lastTime, 0, 50);
  galaxyStructure.lastTime = now;
  if (dt <= 0) return;
  const frameScale = dt / (1000 / 60);

  steerOwnerHome(frameScale);

  for (const category of galaxyStructure.categories.values()) {
    category.armPhase = wrapAngle(category.armPhase + category.patternSpeed * (dt / 1000));
  }
  for (const target of galaxyStructure.repositories.values()) steerRepository(target, frameScale);
  for (const category of galaxyStructure.categories.values()) positionCategoryAtCentroid(category, false);

  // The planned radial lanes and phases carry almost all collision prevention. Keep
  // only a weak predictive safety force for temporary disturbances caused by dragging.
  if (typeof applyNaturalAvoidance === "function") applyNaturalAvoidance(0.22, 1);

  for (const node of state.nodes) limitGalaxyStructureSpeed(node);

  // Once the force baseline has cooled, this layer owns integration so the galaxy
  // continues to move without reheating or hard collision correction.
  if (state.alpha < 0.001) {
    for (const node of state.nodes) {
      if (node.fixed || state.dragging === node) continue;
      const damping = node.type === "repository" ? 0.9992 : node.type === "group" ? 0.9975 : 0.995;
      node.vx *= Math.pow(damping, frameScale);
      node.vy *= Math.pow(damping, frameScale);
      node.x += node.vx * frameScale;
      node.y += node.vy * frameScale;
    }
  }
}

const galaxyStructureBaseApplyForces = applyForces;
applyForces = function applyForcesWithGalaxyStructure() {
  galaxyStructureBaseApplyForces();
  galaxyStructureStep();
};

function syncGalaxyStructureCopy() {
  if (!galaxyStructureMotionDisabled()) return;
  if (detailsDescription) {
    detailsDescription.textContent = galaxyPlainMode
      ? "Force-only baseline: center, repel, link force and link distance. Drag nodes, pan empty space, and scroll or pinch to zoom."
      : "Motion is reduced by your system preference. The underlying force graph remains interactive.";
  }
}

resetButton.addEventListener("click", () => {
  galaxyStructure.initialized = false;
  galaxyStructure.ownerHome = null;
  galaxyStructure.lastTime = performance.now();
});

motionMedia.addEventListener("change", () => {
  galaxyStructure.lastTime = performance.now();
  syncGalaxyStructureCopy();
});
requestAnimationFrame(syncGalaxyStructureCopy);
