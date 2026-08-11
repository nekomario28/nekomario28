"use strict";

// Force-graph baseline. The physics intentionally follow the four concepts exposed
// by Obsidian Graph View: center force, repel force, link force, and link distance.
// No node type receives a special physical anchor or fixed position.
const canvas = document.getElementById("graph");
const context = canvas.getContext("2d");
const searchInput = document.getElementById("search");
const resetButton = document.getElementById("reset");
const detailsTitle = document.getElementById("details-title");
const detailsDescription = document.getElementById("details-description");
const detailsMeta = document.getElementById("details-meta");
const detailsLink = document.getElementById("details-link");
const interactionHint = document.getElementById("interaction-hint");
const statusElement = document.getElementById("status");

const themeMedia = window.matchMedia("(prefers-color-scheme: dark)");
const motionMedia = window.matchMedia("(prefers-reduced-motion: reduce)");

const forceSettings = {
  center: 0.0018,
  repel: 16000,
  link: 0.018,
  linkDistance: 190,
  damping: 0.86,
  collisionPadding: 14,
};

const state = {
  nodes: [],
  links: [],
  nodeById: new Map(),
  width: 1,
  height: 1,
  scale: 1,
  offsetX: 0,
  offsetY: 0,
  alpha: 1,
  time: performance.now(),
  startedAt: performance.now(),
  dragging: null,
  panning: false,
  hovered: null,
  selected: null,
  pointerStart: null,
  lastPointer: null,
  query: "",
  interacted: false,
};

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

function hash(value) {
  let result = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    result ^= value.charCodeAt(index);
    result = Math.imul(result, 16777619);
  }
  return result >>> 0;
}

function palette() {
  if (themeMedia.matches) {
    return {
      background: "#0d1117",
      panel: "#161b22",
      edge: "#586069",
      relation: "#f0883e",
      text: "#f0f6fc",
      muted: "#8b949e",
      owner: "#58a6ff",
      group: "#1f6feb",
      repository: "#3fb950",
      fork: "#8b949e",
      selected: "#ffffff",
      shadow: "rgba(0,0,0,.32)",
    };
  }
  return {
    background: "#f6f8fa",
    panel: "#ffffff",
    edge: "#8c959f",
    relation: "#bc4c00",
    text: "#24292f",
    muted: "#57606a",
    owner: "#54aeff",
    group: "#0969da",
    repository: "#2da44e",
    fork: "#8c959f",
    selected: "#24292f",
    shadow: "rgba(31,35,40,.16)",
  };
}

function colorWithAlpha(hex, alpha) {
  const value = hex.replace("#", "");
  const size = value.length === 3 ? 1 : 2;
  const parts = value.match(new RegExp(`.{${size}}`, "g"));
  const channels = parts.map((part) => parseInt(size === 1 ? part + part : part, 16));
  return `rgba(${channels[0]}, ${channels[1]}, ${channels[2]}, ${alpha})`;
}

function displayLabel(node) {
  const label = String(node.label || "");
  return label.length <= 30 ? label : `${label.slice(0, 29)}…`;
}

function nodeRadius(node) {
  if (node.type === "owner") return 19;
  if (node.type === "group") return 15;
  return 9 + Math.min(3, Number(node.stars || 0));
}

function labelWidth(node) {
  const multiplier = node.type === "repository" ? 6.1 : 6.6;
  return clamp(16 + displayLabel(node).length * multiplier, 48, 188);
}

function nodeDimensions(node) {
  const radius = nodeRadius(node);
  return {
    width: Math.max(radius * 2 + 10, labelWidth(node)),
    height: radius * 2 + 28,
  };
}

function nodeCollisionRadius(node) {
  const dimensions = nodeDimensions(node);
  return Math.max(nodeRadius(node) + 18, Math.min(74, dimensions.width * 0.36 + 18));
}

function nodeColor(node, colors) {
  if (node.type === "owner") return colors.owner;
  if (node.type === "group") return colors.group;
  return node.fork ? colors.fork : colors.repository;
}

function worldToScreen(x, y) {
  return {
    x: state.width / 2 + state.offsetX + x * state.scale,
    y: state.height / 2 + state.offsetY + y * state.scale,
  };
}

function screenToWorld(x, y) {
  return {
    x: (x - state.width / 2 - state.offsetX) / state.scale,
    y: (y - state.height / 2 - state.offsetY) / state.scale,
  };
}

function deterministicScatter(raw, index, count) {
  const golden = Math.PI * (3 - Math.sqrt(5));
  const jitter = (hash(String(raw.id)) % 1000) / 1000;
  const angle = index * golden + jitter * 0.7;
  const radius = 58 + Math.sqrt((index + 1) / Math.max(1, count)) * 360;
  return {
    x: Math.cos(angle) * radius,
    y: Math.sin(angle) * radius,
  };
}

function initializeGraph(data) {
  const rawNodes = Array.isArray(data.nodes) ? data.nodes : [];
  state.nodes = rawNodes.map((raw, index) => {
    const position = deterministicScatter(raw, index, rawNodes.length);
    return {
      ...raw,
      x: position.x,
      y: position.y,
      vx: 0,
      vy: 0,
      fixed: false,
    };
  });
  state.nodeById = new Map(state.nodes.map((node) => [node.id, node]));
  state.links = (Array.isArray(data.links) ? data.links : [])
    .map((raw) => ({
      ...raw,
      source: state.nodeById.get(raw.source),
      target: state.nodeById.get(raw.target),
    }))
    .filter((link) => link.source && link.target);
  state.alpha = 1;
  state.startedAt = performance.now();
  statusElement.hidden = true;

  // Let the graph settle briefly before fitting. This changes no semantics; it only
  // avoids showing the deterministic seed scatter as the final arrangement.
  for (let index = 0; index < 160; index += 1) applyForces();
  resolveNodeCollisions(1, 6);
  fitView(false);
}

function reheat(value = 0.72) {
  state.alpha = Math.max(state.alpha, value);
}

function resolveNodeCollisions(strength = 1, passes = 2) {
  if (state.nodes.length < 2) return;

  for (let pass = 0; pass < passes; pass += 1) {
    for (let first = 0; first < state.nodes.length; first += 1) {
      const a = state.nodes[first];
      for (let second = first + 1; second < state.nodes.length; second += 1) {
        const b = state.nodes[second];
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        let distance = Math.hypot(dx, dy);
        if (distance < 0.001) {
          const angle = (hash(`${a.id}:${b.id}:collision`) % 6283) / 1000;
          dx = Math.cos(angle);
          dy = Math.sin(angle);
          distance = 1;
        }

        const minimum = nodeCollisionRadius(a) + nodeCollisionRadius(b) + forceSettings.collisionPadding;
        if (distance >= minimum) continue;

        const overlap = (minimum - distance) * clamp(strength, 0, 1);
        const ux = dx / distance;
        const uy = dy / distance;
        const aMovable = !a.fixed && state.dragging !== a;
        const bMovable = !b.fixed && state.dragging !== b;
        if (!aMovable && !bMovable) continue;

        const aShare = aMovable ? (bMovable ? 0.5 : 1) : 0;
        const bShare = bMovable ? (aMovable ? 0.5 : 1) : 0;
        if (aMovable) {
          a.x -= ux * overlap * aShare;
          a.y -= uy * overlap * aShare;
          a.vx *= 0.6;
          a.vy *= 0.6;
        }
        if (bMovable) {
          b.x += ux * overlap * bShare;
          b.y += uy * overlap * bShare;
          b.vx *= 0.6;
          b.vy *= 0.6;
        }
      }
    }
  }
}

function applyForces() {
  if (!state.nodes.length) return;
  const alpha = state.alpha;
  if (alpha < 0.001) {
    resolveNodeCollisions(0.55, 1);
    return;
  }

  // Repel force. All node types use the same law; radius only prevents circles from
  // collapsing into each other at very short distances.
  for (let first = 0; first < state.nodes.length; first += 1) {
    const a = state.nodes[first];
    for (let second = first + 1; second < state.nodes.length; second += 1) {
      const b = state.nodes[second];
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      let distanceSquared = dx * dx + dy * dy;
      if (distanceSquared < 1) {
        const angle = (hash(`${a.id}:${b.id}`) % 6283) / 1000;
        dx = Math.cos(angle);
        dy = Math.sin(angle);
        distanceSquared = 1;
      }
      const distance = Math.sqrt(distanceSquared);
      const minimum = nodeCollisionRadius(a) + nodeCollisionRadius(b) + forceSettings.collisionPadding;
      const effectiveSquared = Math.max(distanceSquared, minimum * minimum * 0.34);
      const force = (forceSettings.repel * alpha) / effectiveSquared;
      const fx = (dx / distance) * force;
      const fy = (dy / distance) * force;
      if (!a.fixed && state.dragging !== a) {
        a.vx -= fx;
        a.vy -= fy;
      }
      if (!b.fixed && state.dragging !== b) {
        b.vx += fx;
        b.vy += fy;
      }
    }
  }

  // Link force and link distance. Structural and verified-relation links are drawn
  // differently, but the baseline physics treats every edge equally.
  for (const link of state.links) {
    const dx = link.target.x - link.source.x;
    const dy = link.target.y - link.source.y;
    const distance = Math.max(1, Math.hypot(dx, dy));
    const amount = (distance - forceSettings.linkDistance) * forceSettings.link * alpha;
    const fx = (dx / distance) * amount;
    const fy = (dy / distance) * amount;
    if (!link.source.fixed && state.dragging !== link.source) {
      link.source.vx += fx;
      link.source.vy += fy;
    }
    if (!link.target.fixed && state.dragging !== link.target) {
      link.target.vx -= fx;
      link.target.vy -= fy;
    }
  }

  // Center force. There is deliberately no privileged owner node at (0, 0).
  for (const node of state.nodes) {
    if (node.fixed || state.dragging === node) continue;
    node.vx += -node.x * forceSettings.center * alpha;
    node.vy += -node.y * forceSettings.center * alpha;
    node.vx *= forceSettings.damping;
    node.vy *= forceSettings.damping;
    node.x += node.vx;
    node.y += node.vy;
  }

  resolveNodeCollisions(0.82, 2);
  state.alpha *= 0.986;
}

function connectedToSelected(node) {
  if (!state.selected || state.selected === node) return true;
  return state.links.some(
    (link) =>
      (link.source === state.selected && link.target === node) ||
      (link.target === state.selected && link.source === node),
  );
}

function matchesQuery(node) {
  if (!state.query) return true;
  const text = [
    node.label,
    node.description,
    node.language,
    ...(node.topics || []),
    ...(node.categories || []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return text.includes(state.query);
}

function drawBackground(colors) {
  context.fillStyle = colors.background;
  context.fillRect(0, 0, state.width, state.height);
}

function drawLinks(colors) {
  for (const link of state.links) {
    const source = worldToScreen(link.source.x, link.source.y);
    const target = worldToScreen(link.target.x, link.target.y);
    let opacity = link.type === "relation" ? 0.78 : 0.34;
    if (state.selected && (link.source === state.selected || link.target === state.selected)) opacity = 0.95;
    else if (state.selected && !(connectedToSelected(link.source) && connectedToSelected(link.target))) opacity = 0.08;
    if (state.query && !(matchesQuery(link.source) || matchesQuery(link.target))) opacity = 0.05;
    context.strokeStyle = colorWithAlpha(link.type === "relation" ? colors.relation : colors.edge, opacity);
    context.lineWidth = link.type === "relation" ? 1.7 : 1;
    context.setLineDash([]);
    context.beginPath();
    context.moveTo(source.x, source.y);
    context.lineTo(target.x, target.y);
    context.stroke();
  }
}

function drawNode(node, colors) {
  const point = worldToScreen(node.x, node.y);
  const highlighted = node === state.selected || node === state.hovered;
  const radius = nodeRadius(node) * state.scale * (highlighted ? 1.12 : 1);
  let opacity = 1;
  if (state.selected && !connectedToSelected(node)) opacity = 0.18;
  if (state.query && !matchesQuery(node)) opacity = 0.10;

  context.save();
  context.globalAlpha = opacity;
  context.shadowColor = highlighted ? colors.shadow : "transparent";
  context.shadowBlur = highlighted ? 12 : 0;
  context.fillStyle = nodeColor(node, colors);
  context.beginPath();
  context.arc(point.x, point.y, Math.max(3, radius), 0, Math.PI * 2);
  context.fill();

  if (highlighted) {
    context.shadowColor = "transparent";
    context.strokeStyle = node === state.selected ? colors.selected : colorWithAlpha(colors.selected, 0.72);
    context.lineWidth = node === state.selected ? 2 : 1.5;
    context.beginPath();
    context.arc(point.x, point.y, radius + 5, 0, Math.PI * 2);
    context.stroke();
  }

  const showLabel = node.type !== "repository" || state.scale > 0.42 || highlighted;
  if (showLabel) {
    const fontSize = clamp((node.type === "repository" ? 11 : 12) * state.scale, 9, 14);
    const labelY = point.y + radius + clamp(12 * state.scale, 9, 16);
    context.font = `${node.type === "repository" ? 500 : 600} ${fontSize}px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif`;
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.lineJoin = "round";
    context.strokeStyle = colorWithAlpha(colors.background, 0.94);
    context.lineWidth = 3.5;
    context.strokeText(displayLabel(node), point.x, labelY);
    context.fillStyle = colors.text;
    context.fillText(displayLabel(node), point.x, labelY);
  }
  context.restore();
}

function draw() {
  if (!context) return;
  const colors = palette();
  context.clearRect(0, 0, state.width, state.height);
  drawBackground(colors);
  drawLinks(colors);
  for (const node of state.nodes) drawNode(node, colors);
  context.globalAlpha = 1;
}

function tick(timestamp) {
  state.time = timestamp;
  applyForces();
  draw();
  requestAnimationFrame(tick);
}

function pointerPosition(event) {
  const rect = canvas.getBoundingClientRect();
  return { x: event.clientX - rect.left, y: event.clientY - rect.top };
}

function hitTest(screenX, screenY) {
  for (let index = state.nodes.length - 1; index >= 0; index -= 1) {
    const node = state.nodes[index];
    const point = worldToScreen(node.x, node.y);
    const radius = nodeRadius(node) * state.scale + 9;
    if (Math.hypot(screenX - point.x, screenY - point.y) <= radius) return node;
  }
  return null;
}

function hideInteractionHint() {
  if (state.interacted) return;
  state.interacted = true;
  interactionHint?.classList.add("is-hidden");
}

function descriptionForType(type) {
  if (type === "owner") return "GitHub account node in the public project graph.";
  if (type === "group") return "A manually curated category of related public projects.";
  return "Public GitHub repository.";
}

function selectNode(node) {
  state.selected = node;
  if (!node) {
    detailsTitle.textContent = "Explore the map";
    detailsDescription.textContent = "Select a circle. Drag nodes, drag empty space to pan, and scroll or pinch to zoom.";
    detailsMeta.hidden = true;
    detailsLink.hidden = true;
    draw();
    return;
  }

  hideInteractionHint();
  detailsTitle.textContent = node.label;
  detailsDescription.textContent = node.description || descriptionForType(node.type);
  const rows = [["Type", node.type === "group" ? "category" : node.type]];
  if (node.categories?.length) rows.push(["Category", node.categories.join(", ")]);
  if (node.language) rows.push(["Language", node.language]);
  if (node.topics?.length) rows.push(["Topics", node.topics.join(", ")]);
  if (node.type === "repository") rows.push(["Stars", String(node.stars || 0)]);
  if (node.type === "group") rows.push(["Projects", String(node.repositoryCount || 0)]);
  if (node.fork) rows.push(["Repository", "Fork / continuation"]);
  if (node.archived) rows.push(["Status", "Archived"]);
  detailsMeta.replaceChildren();
  for (const [term, value] of rows) {
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = term;
    dd.textContent = value;
    detailsMeta.append(dt, dd);
  }
  detailsMeta.hidden = false;
  if (node.url) {
    detailsLink.href = node.url;
    detailsLink.textContent = node.type === "repository" ? "Open repository →" : "Open on GitHub →";
    detailsLink.hidden = false;
  } else {
    detailsLink.hidden = true;
  }
  draw();
}

function fitView(resetSelection = true) {
  if (!state.nodes.length) return;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const node of state.nodes) {
    const radius = nodeCollisionRadius(node) + 18;
    minX = Math.min(minX, node.x - radius);
    maxX = Math.max(maxX, node.x + radius);
    minY = Math.min(minY, node.y - radius);
    maxY = Math.max(maxY, node.y + radius);
  }
  const width = Math.max(120, maxX - minX);
  const height = Math.max(120, maxY - minY);
  const availableWidth = Math.max(280, state.width - (state.width > 900 ? 350 : 34));
  const availableHeight = Math.max(240, state.height - 42);
  state.scale = clamp(Math.min(availableWidth / width, availableHeight / height), 0.30, 1.5);
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  state.offsetX = -centerX * state.scale + (state.width > 900 ? -130 : 0);
  state.offsetY = -centerY * state.scale;
  if (resetSelection) selectNode(null);
  draw();
}

function reseedGraph() {
  const count = state.nodes.length;
  state.nodes.forEach((node, index) => {
    const position = deterministicScatter(node, index, count);
    node.x = position.x;
    node.y = position.y;
    node.vx = 0;
    node.vy = 0;
    node.fixed = false;
  });
  reheat(1);
  for (let index = 0; index < 120; index += 1) applyForces();
  resolveNodeCollisions(1, 6);
  fitView(true);
}

canvas.addEventListener("pointerdown", (event) => {
  canvas.setPointerCapture(event.pointerId);
  const point = pointerPosition(event);
  const node = hitTest(point.x, point.y);
  state.pointerStart = point;
  state.lastPointer = point;
  hideInteractionHint();
  if (node) {
    state.dragging = node;
    node.fixed = true;
  } else {
    state.panning = true;
  }
  canvas.classList.add("dragging");
});

canvas.addEventListener("pointermove", (event) => {
  const point = pointerPosition(event);
  if (state.dragging) {
    const world = screenToWorld(point.x, point.y);
    state.dragging.x = world.x;
    state.dragging.y = world.y;
    state.dragging.vx = 0;
    state.dragging.vy = 0;
    reheat(0.55);
  } else if (state.panning && state.lastPointer) {
    state.offsetX += point.x - state.lastPointer.x;
    state.offsetY += point.y - state.lastPointer.y;
  } else {
    state.hovered = hitTest(point.x, point.y);
    canvas.classList.toggle("over-node", Boolean(state.hovered));
  }
  state.lastPointer = point;
  draw();
});

canvas.addEventListener("pointerleave", () => {
  if (!state.dragging && !state.panning) {
    state.hovered = null;
    canvas.classList.remove("over-node");
  }
});

function finishPointer(event, cancelled = false) {
  const point = pointerPosition(event);
  const moved = state.pointerStart ? Math.hypot(point.x - state.pointerStart.x, point.y - state.pointerStart.y) : 99;
  const dragged = state.dragging;
  if (dragged) {
    dragged.fixed = false;
    dragged.vx = 0;
    dragged.vy = 0;
    reheat(0.55);
  }
  state.dragging = null;
  state.panning = false;
  state.pointerStart = null;
  state.lastPointer = null;
  canvas.classList.remove("dragging");
  if (!cancelled && moved < 6) selectNode(hitTest(point.x, point.y));
}

canvas.addEventListener("pointerup", (event) => finishPointer(event, false));
canvas.addEventListener("pointercancel", (event) => finishPointer(event, true));

canvas.addEventListener("dblclick", (event) => {
  const point = pointerPosition(event);
  const node = hitTest(point.x, point.y);
  if (node?.type === "repository" && node.url) window.open(node.url, "_blank", "noopener");
});

canvas.addEventListener(
  "wheel",
  (event) => {
    event.preventDefault();
    hideInteractionHint();
    const point = pointerPosition(event);
    const before = screenToWorld(point.x, point.y);
    state.scale = clamp(state.scale * Math.exp(-event.deltaY * 0.0012), 0.25, 3.5);
    const after = worldToScreen(before.x, before.y);
    state.offsetX += point.x - after.x;
    state.offsetY += point.y - after.y;
    draw();
  },
  { passive: false },
);

searchInput.addEventListener("input", () => {
  state.query = searchInput.value.trim().toLowerCase();
  hideInteractionHint();
  selectNode(state.query ? state.nodes.find(matchesQuery) || null : null);
});

resetButton.addEventListener("click", () => {
  searchInput.value = "";
  state.query = "";
  reseedGraph();
});

themeMedia.addEventListener("change", draw);

function resize() {
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.max(1, window.devicePixelRatio || 1);
  state.width = Math.max(1, rect.width);
  state.height = Math.max(1, rect.height);
  canvas.width = Math.floor(state.width * ratio);
  canvas.height = Math.floor(state.height * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  draw();
}

window.addEventListener("resize", resize, { passive: true });
resize();
requestAnimationFrame(tick);

fetch("graph-data.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then(initializeGraph)
  .catch((error) => {
    statusElement.textContent = `Could not load project map: ${error.message}`;
    statusElement.hidden = false;
  });