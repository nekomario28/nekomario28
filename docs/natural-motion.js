"use strict";

// Smooth collision avoidance layered over the force graph. This intentionally
// changes velocity only: no node is teleported, snapped, or forcibly stopped.
const naturalMotionSettings = {
  lookAheadFrames: 22,
  comfortMargin: 54,
  radialStrength: 0.050,
  predictiveStrength: 0.040,
  sidestepStrength: 0.018,
};

function naturalMotionPair(a, b, strength = 1) {
  let dx = b.x - a.x;
  let dy = b.y - a.y;
  let distance = Math.hypot(dx, dy);
  if (distance < 0.001) {
    const angle = (hash(`${a.id}:${b.id}:avoid`) % 6283) / 1000;
    dx = Math.cos(angle);
    dy = Math.sin(angle);
    distance = 1;
  }

  const ux = dx / distance;
  const uy = dy / distance;
  const minimum = nodeCollisionRadius(a) + nodeCollisionRadius(b) + forceSettings.collisionPadding;
  const comfort = minimum + naturalMotionSettings.comfortMargin;

  const relativeVx = (b.vx || 0) - (a.vx || 0);
  const relativeVy = (b.vy || 0) - (a.vy || 0);
  const predictedDx = dx + relativeVx * naturalMotionSettings.lookAheadFrames;
  const predictedDy = dy + relativeVy * naturalMotionSettings.lookAheadFrames;
  const predictedDistance = Math.hypot(predictedDx, predictedDy);
  const closingSpeed = Math.max(0, -(relativeVx * ux + relativeVy * uy));

  const proximity = clamp((comfort - distance) / Math.max(1, comfort - minimum * 0.55), 0, 1);
  const predicted = clamp((comfort - predictedDistance) / Math.max(1, comfort), 0, 1);
  if (proximity <= 0 && predicted <= 0) return;

  const scale = clamp(strength, 0, 1);
  const radial =
    (proximity * proximity * naturalMotionSettings.radialStrength +
      predicted * predicted * naturalMotionSettings.predictiveStrength * (1 + Math.min(1.4, closingSpeed * 0.35))) *
    scale;

  const aMovable = !a.fixed && state.dragging !== a;
  const bMovable = !b.fixed && state.dragging !== b;
  if (!aMovable && !bMovable) return;

  if (aMovable) {
    a.vx -= ux * radial;
    a.vy -= uy * radial;
  }
  if (bMovable) {
    b.vx += ux * radial;
    b.vy += uy * radial;
  }

  // Predictive sideways steering makes approaching nodes flow around each other
  // instead of braking head-on. The deterministic sign prevents visual jitter.
  if (predicted > 0.08 && closingSpeed > 0.02) {
    const sign = hash(`${a.id}:${b.id}:side`) % 2 === 0 ? 1 : -1;
    const tx = -uy * sign;
    const ty = ux * sign;
    const side = predicted * Math.min(1, closingSpeed * 0.5 + 0.18) * naturalMotionSettings.sidestepStrength * scale;
    if (aMovable) {
      a.vx += tx * side;
      a.vy += ty * side;
    }
    if (bMovable) {
      b.vx -= tx * side;
      b.vy -= ty * side;
    }
  }
}

function applyNaturalAvoidance(strength = 1, passes = 1) {
  if (state.nodes.length < 2) return;
  for (let pass = 0; pass < Math.max(1, passes); pass += 1) {
    for (let first = 0; first < state.nodes.length; first += 1) {
      for (let second = first + 1; second < state.nodes.length; second += 1) {
        naturalMotionPair(state.nodes[first], state.nodes[second], strength);
      }
    }
  }
}

// graph.js already calls this compatibility hook while settling and while running.
// Replacing it here removes the old hard positional correction without changing the
// force-only baseline structure.
resolveNodeCollisions = function resolveNodeCollisionsWithSmoothAvoidance(strength = 1, passes = 1) {
  applyNaturalAvoidance(strength, passes);
};
