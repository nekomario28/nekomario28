"use strict";

// Optional behavior layer for the project map. The base graph remains intact so
// this experiment can be removed by deleting one script tag.
const galaxyLayout = {
  canonicalHome: new Map(),
  parentByRepository: new Map(),
  cameraToken: 0,
};

function galaxyMobility(node) {
  if (node.type === "owner") return 0;
  if (node.type === "group") return 0.24;
  return 1;
}

function galaxySorted(ids) {
  return [...ids].sort((a, b) => hash(String(a)) - hash(String(b)) || String(a).localeCompare(String(b)));
}

buildInitialLayout = function buildGalaxyLayout(data) {
  const groups = data.nodes.filter((node) => node.type === "group");
  const membersByGroup = new Map();
  const membershipByRepository = new Map();

  for (const link of data.links) {
    if (link.type !== "member") continue;
    if (!membersByGroup.has(link.source)) membersByGroup.set(link.source, []);
    membersByGroup.get(link.source).push(link.target);
    if (!membershipByRepository.has(link.target)) membershipByRepository.set(link.target, link.source);
  }

  galaxyLayout.parentByRepository = membershipByRepository;
  galaxyLayout.canonicalHome = new Map();

  const groupAnchors = new Map();
  groups.forEach((group, index) => {
    const ring = Math.floor(index / 6);
    const ringGroups = groups.slice(ring * 6, ring * 6 + 6);
    const indexInRing = index % 6;
    const angle = -Math.PI / 2 + (indexInRing * Math.PI * 2) / Math.max(1, ringGroups.length);
    const rx = 235 + ring * 155;
    const ry = 178 + ring * 118;
    const anchor = {
      x: Math.cos(angle) * rx,
      y: Math.sin(angle) * ry,
      angle,
    };
    groupAnchors.set(group.id, anchor);
    galaxyLayout.canonicalHome.set(group.id, { x: anchor.x, y: anchor.y });
  });

  const repositoryAnchors = new Map();
  for (const group of groups) {
    const anchor = groupAnchors.get(group.id);
    const members = galaxySorted(membersByGroup.get(group.id) || []);
    let cursor = 0;
    let orbit = 0;

    while (cursor < members.length) {
      const capacity = 4 + orbit * 2;
      const count = Math.min(capacity, members.length - cursor);
      const radius = 112 + orbit * 82;
      const span = count <= 1 ? 0 : Math.min(1.82, 0.72 + count * 0.21);

      for (let slot = 0; slot < count; slot += 1) {
        const repositoryId = members[cursor + slot];
        const fraction = count <= 1 ? 0.5 : slot / (count - 1);
        const jitter = ((hash(String(repositoryId)) % 1000) / 1000 - 0.5) * 0.11;
        const angle = anchor.angle - span / 2 + span * fraction + jitter;
        const position = {
          x: anchor.x + Math.cos(angle) * radius,
          y: anchor.y + Math.sin(angle) * radius,
        };
        repositoryAnchors.set(repositoryId, position);
        galaxyLayout.canonicalHome.set(repositoryId, { ...position });
      }

      cursor += count;
      orbit += 1;
    }
  }

  const ungrouped = data.nodes.filter(
    (node) => node.type === "repository" && !membershipByRepository.has(node.id),
  );
  galaxySorted(ungrouped.map((node) => node.id)).forEach((repositoryId, index, ids) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / Math.max(1, ids.length);
    const ring = Math.floor(index / 10);
    const position = {
      x: Math.cos(angle) * (445 + ring * 120),
      y: Math.sin(angle) * (325 + ring * 90),
    };
    repositoryAnchors.set(repositoryId, position);
    galaxyLayout.canonicalHome.set(repositoryId, { ...position });
  });

  return { groupAnchors, repositoryAnchors };
};

function galaxySeparatePair(a, b, paddingX, paddingY, strength = 1) {
  const aSize = nodeDimensions(a);
  const bSize = nodeDimensions(b);
  let dx = b.x - a.x;
  let dy = b.y - a.y;
  if (Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001) {
    dx = ((hash(a.id + b.id) % 2) ? 1 : -1) * 0.01;
    dy = 0.01;
  }

  const overlapX = (aSize.width + bSize.width) / 2 + paddingX - Math.abs(dx);
  const overlapY = (aSize.height + bSize.height) / 2 + paddingY - Math.abs(dy);
  if (overlapX <= 0 || overlapY <= 0) return false;

  const pushX = overlapX < overlapY;
  const overlap = (pushX ? overlapX : overlapY) * strength;
  const direction = pushX ? Math.sign(dx || 1) : Math.sign(dy || 1);
  const aMobility = galaxyMobility(a);
  const bMobility = galaxyMobility(b);
  const totalMobility = aMobility + bMobility;
  if (totalMobility <= 0) return false;
  const aShare = aMobility / totalMobility;
  const bShare = bMobility / totalMobility;

  if (pushX) {
    a.x -= direction * overlap * aShare;
    b.x += direction * overlap * bShare;
  } else {
    a.y -= direction * overlap * aShare;
    b.y += direction * overlap * bShare;
  }
  return true;
}

resolveInitialCollisions = function resolveGalaxyInitialCollisions(nodes) {
  for (let iteration = 0; iteration < 260; iteration += 1) {
    let moved = false;
    for (let first = 0; first < nodes.length; first += 1) {
      for (let second = first + 1; second < nodes.length; second += 1) {
        moved = galaxySeparatePair(nodes[first], nodes[second], 30, 25, 0.58) || moved;
      }
    }

    for (const node of nodes) {
      if (node.type === "owner") continue;
      const home = galaxyLayout.canonicalHome.get(node.id);
      if (!home) continue;
      const pull = node.type === "group" ? 0.075 : 0.022;
      node.x += (home.x - node.x) * pull;
      node.y += (home.y - node.y) * pull;
    }
    if (!moved) break;
  }

  // Final collision-only passes guarantee labels do not get pulled back into one another.
  for (let iteration = 0; iteration < 100; iteration += 1) {
    let moved = false;
    for (let first = 0; first < nodes.length; first += 1) {
      for (let second = first + 1; second < nodes.length; second += 1) {
        moved = galaxySeparatePair(nodes[first], nodes[second], 27, 23, 0.54) || moved;
      }
    }
    if (!moved) break;
  }

  for (const node of nodes) {
    if (node.type === "owner") continue;
    node.anchorX = node.x;
    node.anchorY = node.y;
  }
};

function galaxyLinkPhysics(link) {
  if (link.type === "contains") return { preferred: 220, strength: 0.020 };
  if (link.type === "member") return { preferred: 138, strength: 0.022 };
  if (link.type === "owns") return { preferred: 410, strength: 0.007 };
  return { preferred: 145, strength: 0.032 };
}

function galaxyVelocityShare(a, b) {
  const aMobility = galaxyMobility(a);
  const bMobility = galaxyMobility(b);
  const total = Math.max(0.001, aMobility + bMobility);
  return { a: aMobility / total, b: bMobility / total };
}

function galaxyRuntimeRelax(nodes) {
  for (let first = 0; first < nodes.length; first += 1) {
    const a = nodes[first];
    if (a === state.dragging) continue;
    for (let second = first + 1; second < nodes.length; second += 1) {
      const b = nodes[second];
      if (b === state.dragging) continue;
      galaxySeparatePair(a, b, 21, 18, 0.13);
    }
  }
}

applyForces = function applyGalaxyForces() {
  const alpha = state.alpha;
  const liveAlpha = Math.max(alpha, 0.085);

  for (let first = 0; first < state.nodes.length; first += 1) {
    const a = state.nodes[first];
    const aSize = nodeDimensions(a);
    for (let second = first + 1; second < state.nodes.length; second += 1) {
      const b = state.nodes[second];
      const bSize = nodeDimensions(b);
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      if (Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001) dx = 1;

      const overlapX = (aSize.width + bSize.width) / 2 + 23 - Math.abs(dx);
      const overlapY = (aSize.height + bSize.height) / 2 + 20 - Math.abs(dy);
      if (overlapX > 0 && overlapY > 0) {
        const pushX = overlapX < overlapY;
        const overlap = pushX ? overlapX : overlapY;
        const direction = pushX ? Math.sign(dx || 1) : Math.sign(dy || 1);
        const share = galaxyVelocityShare(a, b);
        const amount = overlap * 0.17 * liveAlpha;
        if (!a.fixed && state.dragging !== a) {
          if (pushX) a.vx -= direction * amount * share.a;
          else a.vy -= direction * amount * share.a;
        }
        if (!b.fixed && state.dragging !== b) {
          if (pushX) b.vx += direction * amount * share.b;
          else b.vy += direction * amount * share.b;
        }
      }

      const distanceSquared = Math.max(1150, dx * dx + dy * dy);
      const distance = Math.sqrt(distanceSquared);
      const hubBoost = a.type === "group" || b.type === "group" || a.type === "owner" || b.type === "owner" ? 1.28 : 1;
      const repulsion = (1750 * hubBoost) / distanceSquared;
      const forceX = (dx / distance) * repulsion * liveAlpha;
      const forceY = (dy / distance) * repulsion * liveAlpha;
      const share = galaxyVelocityShare(a, b);
      if (!a.fixed && state.dragging !== a) {
        a.vx -= forceX * share.a;
        a.vy -= forceY * share.a;
      }
      if (!b.fixed && state.dragging !== b) {
        b.vx += forceX * share.b;
        b.vy += forceY * share.b;
      }
    }
  }

  for (const link of state.links) {
    const dx = link.target.x - link.source.x;
    const dy = link.target.y - link.source.y;
    const distance = Math.max(1, Math.hypot(dx, dy));
    const physics = galaxyLinkPhysics(link);
    const amount = (distance - physics.preferred) * physics.strength * alpha;
    const forceX = (dx / distance) * amount;
    const forceY = (dy / distance) * amount;
    const share = galaxyVelocityShare(link.source, link.target);
    if (!link.source.fixed && state.dragging !== link.source) {
      link.source.vx += forceX * share.a;
      link.source.vy += forceY * share.a;
    }
    if (!link.target.fixed && state.dragging !== link.target) {
      link.target.vx -= forceX * share.b;
      link.target.vy -= forceY * share.b;
    }
  }

  for (const node of state.nodes) {
    if (node.fixed || state.dragging === node) continue;
    const anchorStrength = node.type === "group" ? 0.020 : 0.013;
    node.vx += (node.anchorX - node.x) * anchorStrength * liveAlpha;
    node.vy += (node.anchorY - node.y) * anchorStrength * liveAlpha;
    node.vx *= node.type === "group" ? 0.79 : 0.83;
    node.vy *= node.type === "group" ? 0.79 : 0.83;
    node.x += node.vx;
    node.y += node.vy;
  }

  galaxyRuntimeRelax(state.nodes);
  state.alpha = Math.max(0.010, state.alpha * 0.987);
};

function galaxyGroupMembers(group) {
  return state.links
    .filter((link) => link.type === "member" && link.source === group)
    .map((link) => link.target);
}

function galaxyCameraTarget(nodes) {
  if (!nodes.length) return null;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const node of nodes) {
    const size = nodeDimensions(node);
    minX = Math.min(minX, node.x - size.width / 2 - 45);
    maxX = Math.max(maxX, node.x + size.width / 2 + 45);
    minY = Math.min(minY, node.y - size.height / 2 - 45);
    maxY = Math.max(maxY, node.y + size.height / 2 + 45);
  }

  const availableWidth = Math.max(320, state.width - (state.width > 900 ? 365 : 40));
  const availableHeight = Math.max(260, state.height - 70);
  const width = Math.max(120, maxX - minX);
  const height = Math.max(100, maxY - minY);
  const scale = clamp(Math.min(availableWidth / width, availableHeight / height), 0.48, 1.55);
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  return {
    scale,
    offsetX: -centerX * scale + (state.width > 900 ? -135 : 0),
    offsetY: -centerY * scale,
  };
}

function galaxyAnimateCamera(nodes) {
  const target = galaxyCameraTarget(nodes);
  if (!target) return;
  const token = ++galaxyLayout.cameraToken;
  const start = {
    scale: state.scale,
    offsetX: state.offsetX,
    offsetY: state.offsetY,
    time: performance.now(),
  };
  const duration = motionMedia.matches ? 0 : 360;

  function frame(now) {
    if (token !== galaxyLayout.cameraToken) return;
    const raw = duration === 0 ? 1 : clamp((now - start.time) / duration, 0, 1);
    const eased = 1 - Math.pow(1 - raw, 3);
    state.scale = start.scale + (target.scale - start.scale) * eased;
    state.offsetX = start.offsetX + (target.offsetX - start.offsetX) * eased;
    state.offsetY = start.offsetY + (target.offsetY - start.offsetY) * eased;
    draw();
    if (raw < 1) requestAnimationFrame(frame);
  }

  requestAnimationFrame(frame);
}

function galaxyFocusNode(node) {
  if (!node) return;
  if (node.type === "group") {
    galaxyAnimateCamera([node, ...galaxyGroupMembers(node)]);
  } else {
    galaxyAnimateCamera([node]);
  }
}

function galaxyReflow() {
  galaxyLayout.cameraToken += 1;
  for (const node of state.nodes) {
    node.vx = 0;
    node.vy = 0;
    if (node.type === "owner") {
      node.x = 0;
      node.y = 0;
      node.anchorX = 0;
      node.anchorY = 0;
      continue;
    }
    const home = galaxyLayout.canonicalHome.get(node.id);
    if (!home) continue;
    node.x = home.x;
    node.y = home.y;
    node.anchorX = home.x;
    node.anchorY = home.y;
  }
  resolveInitialCollisions(state.nodes);
  state.alpha = 0.72;
  fitView(false);
}

canvas.addEventListener("dblclick", (event) => {
  const point = pointerPosition(event);
  const node = hitTest(point.x, point.y);
  if (node?.type === "group") {
    event.preventDefault();
    selectNode(node);
    galaxyFocusNode(node);
  } else if (!node) {
    event.preventDefault();
    fitView(false);
  }
});

searchInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  const match = state.selected || state.nodes.find(matchesQuery);
  if (!match) return;
  event.preventDefault();
  selectNode(match);
  galaxyFocusNode(match);
});

window.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  galaxyLayout.cameraToken += 1;
  searchInput.value = "";
  state.query = "";
  selectNode(null);
  fitView(false);
});

const reflowButton = document.getElementById("reflow");
reflowButton?.addEventListener("click", () => {
  hideInteractionHint();
  galaxyReflow();
});
