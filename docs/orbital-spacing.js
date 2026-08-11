"use strict";

// Orbital spacing for galaxy mode. Projects are separated by phase while they are
// still far apart on nearby radial lanes. The algorithm changes tangential velocity
// only: no teleporting, braking-to-zero, or last-moment sidestep behavior.
const orbitalSpacingPlainMode = new URLSearchParams(window.location.search).has("plain");
const orbitalSpacingBaseResolveNodeCollisions = resolveNodeCollisions;

function orbitalAngleDelta(from, to) {
  let value = (to - from) % (Math.PI * 2);
  if (value > Math.PI) value -= Math.PI * 2;
  if (value < -Math.PI) value += Math.PI * 2;
  return value;
}

function applyOrbitalSpacing(strength = 1) {
  if (orbitalSpacingPlainMode) return;
  if (typeof galaxyStructure === "undefined" || !galaxyStructure.initialized || !galaxyStructure.owner) return;

  const owner = galaxyStructure.owner;
  const targets = Array.from(galaxyStructure.repositories.values());
  for (let first = 0; first < targets.length; first += 1) {
    const aTarget = targets[first];
    const a = aTarget.node;
    if (!a || state.dragging === a) continue;

    const aDx = a.x - owner.x;
    const aDy = a.y - owner.y;
    const aRadius = Math.max(1, Math.hypot(aDx, aDy));
    const aAngle = Math.atan2(aDy, aDx);
    const aTx = -Math.sin(aAngle);
    const aTy = Math.cos(aAngle);

    for (let second = first + 1; second < targets.length; second += 1) {
      const bTarget = targets[second];
      const b = bTarget.node;
      if (!b || state.dragging === b) continue;

      const radialGap = Math.abs(aTarget.targetRadius - bTarget.targetRadius);
      const radialInfluence = clamp(1 - radialGap / 105, 0, 1);
      if (radialInfluence <= 0) continue;

      const bDx = b.x - owner.x;
      const bDy = b.y - owner.y;
      const bRadius = Math.max(1, Math.hypot(bDx, bDy));
      const bAngle = Math.atan2(bDy, bDx);
      let angularGap = orbitalAngleDelta(aAngle, bAngle);
      if (Math.abs(angularGap) < 0.0001) {
        angularGap = String(a.id).localeCompare(String(b.id)) <= 0 ? 0.0001 : -0.0001;
      }

      const averageRadius = (aRadius + bRadius) / 2;
      const labelClearance = nodeCollisionRadius(a) + nodeCollisionRadius(b) + 72;
      const comfortAngle = clamp(labelClearance / averageRadius, 0.14, 0.62) * (0.72 + radialInfluence * 0.28);
      const gap = Math.abs(angularGap);
      if (gap >= comfortAngle) continue;

      const proximity = 1 - gap / comfortAngle;
      const sameCategory = aTarget.category === bTarget.category;
      const phasePush =
        proximity * proximity * radialInfluence * (sameCategory ? 0.0042 : 0.0030) * clamp(strength, 0, 1);
      const direction = angularGap > 0 ? 1 : -1;

      const bTx = -Math.sin(bAngle);
      const bTy = Math.cos(bAngle);
      a.vx -= aTx * phasePush * direction;
      a.vy -= aTy * phasePush * direction;
      b.vx += bTx * phasePush * direction;
      b.vy += bTy * phasePush * direction;
    }
  }
}

// graph.js invokes this hook during its force step. In plain mode preserve the core
// force-graph collision behavior; in galaxy mode replace it with phase spacing.
resolveNodeCollisions = function resolveNodeCollisionsWithOrbitalSpacing(strength = 1, passes = 1) {
  if (orbitalSpacingPlainMode) {
    orbitalSpacingBaseResolveNodeCollisions(strength, passes);
    return;
  }
  for (let pass = 0; pass < Math.max(1, passes); pass += 1) applyOrbitalSpacing(strength);
};
