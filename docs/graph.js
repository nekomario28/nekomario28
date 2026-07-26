"use strict";

const canvas = document.getElementById("graph");
const context = canvas.getContext("2d");
const searchInput = document.getElementById("search");
const resetButton = document.getElementById("reset");
const statusElement = document.getElementById("status");
const detailsTitle = document.getElementById("details-title");
const detailsDescription = document.getElementById("details-description");
const detailsMeta = document.getElementById("details-meta");
const detailsLink = document.getElementById("details-link");

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
  selected: null,
  hovered: null,
  dragging: null,
  panning: false,
  pointerStart: null,
  lastPointer: null,
  query: "",
};

const media = window.matchMedia("(prefers-color-scheme: dark)");
media.addEventListener("change", () => draw());

function palette() {
  if (media.matches) {
    return {
      background: "#0d1117",
      edge: "#484f58",
      relation: "#f0883e",
      text: "#f0f6fc",
      muted: "#8b949e",
      owner: "#58a6ff",
      group: "#1f6feb",
      repository: "#3fb950",
      fork: "#6e7681",
      language: "#a371f7",
      topic: "#d29922",
      selected: "#ffffff",
    };
  }
  return {
    background: "#f6f8fa",
    edge: "#afb8c1",
    relation: "#bc4c00",
    text: "#24292f",
    muted: "#57606a",
    owner: "#54aeff",
    group: "#0969da",
    repository: "#2da44e",
    fork: "#8c959f",
    language: "#8250df",
    topic: "#bf8700",
    selected: "#24292f",
  };
}

function hash(value) {
  let result = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    result ^= value.charCodeAt(index);
    result = Math.imul(result, 16777619);
  }
  return result >>> 0;
}

function nodeRadius(node) {
  if (node.type === "owner") return 28;
  if (node.type === "group") return 19;
  if (node.type === "repository") return 12 + Math.min(5, Number(node.stars || 0));
  if (node.type === "language") return 9;
  return 7;
}

function nodeColor(node, colors) {
  if (node.type === "owner") return colors.owner;
  if (node.type === "group") return colors.group;
  if (node.type === "repository") return node.fork ? colors.fork : colors.repository;
  if (node.type === "language") return colors.language;
  return colors.topic;
}

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

function initializeGraph(data) {
  const countByType = { owner: 0, group: 0, repository: 0, language: 0, topic: 0 };

  state.nodes = data.nodes.map((raw) => {
    const typeIndex = countByType[raw.type] || 0;
    countByType[raw.type] = typeIndex + 1;
    const seed = hash(raw.id);
    let radius = 0;
    if (raw.type === "group") radius = 115;
    if (raw.type === "repository") radius = 235;
    if (raw.type === "language") radius = 365;
    if (raw.type === "topic") radius = 470;
    const angle = ((seed % 3600) / 3600) * Math.PI * 2 + typeIndex * 0.19;

    return {
      ...raw,
      x: raw.type === "owner" ? 0 : Math.cos(angle) * radius,
      y: raw.type === "owner" ? 0 : Math.sin(angle) * radius,
      vx: 0,
      vy: 0,
      fixed: raw.type === "owner",
    };
  });

  state.nodeById = new Map(state.nodes.map((node) => [node.id, node]));
  state.links = data.links
    .map((link) => ({
      ...link,
      source: state.nodeById.get(link.source),
      target: state.nodeById.get(link.target),
    }))
    .filter((link) => link.source && link.target);

  statusElement.hidden = true;
  resetView();
  state.alpha = 1;
  requestAnimationFrame(tick);
}

function linkPhysics(link) {
  if (link.type === "owns") return { preferred: 230, strength: 0.008 };
  if (link.type === "contains") return { preferred: 110, strength: 0.025 };
  if (link.type === "member") return { preferred: 145, strength: 0.03 };
  if (link.type === "language" || link.type === "topic") {
    return { preferred: 135, strength: 0.018 };
  }
  return { preferred: 105, strength: 0.036 };
}

function isStructuralLink(link) {
  return ["owns", "contains", "member", "language", "topic"].includes(link.type);
}

function applyForces() {
  const nodes = state.nodes;
  const links = state.links;
  const alpha = state.alpha;

  for (let first = 0; first < nodes.length; first += 1) {
    const a = nodes[first];
    for (let second = first + 1; second < nodes.length; second += 1) {
      const b = nodes[second];
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      let distanceSquared = dx * dx + dy * dy;
      if (distanceSquared < 1) {
        dx = 1;
        dy = 0;
        distanceSquared = 1;
      }
      const distance = Math.sqrt(distanceSquared);
      const minimum = nodeRadius(a) + nodeRadius(b) + 28;
      const repulsion = (distance < minimum ? 9800 : 3400) / distanceSquared;
      const forceX = (dx / distance) * repulsion * alpha;
      const forceY = (dy / distance) * repulsion * alpha;
      if (!a.fixed && state.dragging !== a) {
        a.vx -= forceX;
        a.vy -= forceY;
      }
      if (!b.fixed && state.dragging !== b) {
        b.vx += forceX;
        b.vy += forceY;
      }
    }
  }

  for (const link of links) {
    const dx = link.target.x - link.source.x;
    const dy = link.target.y - link.source.y;
    const distance = Math.max(1, Math.hypot(dx, dy));
    const physics = linkPhysics(link);
    const amount = (distance - physics.preferred) * physics.strength * alpha;
    const forceX = (dx / distance) * amount;
    const forceY = (dy / distance) * amount;
    if (!link.source.fixed && state.dragging !== link.source) {
      link.source.vx += forceX;
      link.source.vy += forceY;
    }
    if (!link.target.fixed && state.dragging !== link.target) {
      link.target.vx -= forceX;
      link.target.vy -= forceY;
    }
  }

  for (const node of nodes) {
    if (node.fixed || state.dragging === node) continue;
    node.vx += -node.x * 0.0008 * alpha;
    node.vy += -node.y * 0.0008 * alpha;
    node.vx *= 0.86;
    node.vy *= 0.86;
    node.x += node.vx;
    node.y += node.vy;
  }

  state.alpha = Math.max(0.018, state.alpha * 0.992);
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
  const text = [node.label, node.description, node.language, ...(node.topics || [])]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return text.includes(state.query);
}

function draw() {
  const colors = palette();
  context.clearRect(0, 0, state.width, state.height);
  context.fillStyle = colors.background;
  context.fillRect(0, 0, state.width, state.height);

  for (const link of state.links) {
    const source = worldToScreen(link.source.x, link.source.y);
    const target = worldToScreen(link.target.x, link.target.y);
    const structural = isStructuralLink(link);
    let opacity = structural ? 0.3 : 0.72;
    if (state.selected && (link.source === state.selected || link.target === state.selected)) opacity = 0.98;
    if (state.query && !(matchesQuery(link.source) || matchesQuery(link.target))) opacity = 0.08;
    context.lineWidth = structural ? 1 : 2.2;
    context.strokeStyle = colorWithAlpha(structural ? colors.edge : colors.relation, opacity);
    context.beginPath();
    context.moveTo(source.x, source.y);
    context.lineTo(target.x, target.y);
    context.stroke();
  }

  for (const node of state.nodes) {
    const point = worldToScreen(node.x, node.y);
    const radius = nodeRadius(node) * Math.max(0.74, Math.min(1.2, state.scale));
    let opacity = 1;
    if (state.selected && !connectedToSelected(node)) opacity = 0.25;
    if (state.query && !matchesQuery(node)) opacity = 0.14;

    context.globalAlpha = opacity;
    context.fillStyle = nodeColor(node, colors);
    context.beginPath();
    context.arc(point.x, point.y, radius, 0, Math.PI * 2);
    context.fill();

    if (node === state.selected || node === state.hovered || (state.query && matchesQuery(node))) {
      context.lineWidth = node === state.selected ? 3 : 2;
      context.strokeStyle = colors.selected;
      context.stroke();
    }

    const showLabel =
      node.type === "owner" ||
      node.type === "group" ||
      node.type === "repository" ||
      node === state.selected ||
      node === state.hovered ||
      state.scale > 1.35;

    if (showLabel) {
      context.globalAlpha = opacity;
      const emphasized = node.type === "owner" || node.type === "group";
      context.font = `${emphasized ? 600 : 500} ${node.type === "owner" ? 13 : 11}px -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif`;
      context.textAlign = "center";
      context.textBaseline = "top";
      context.fillStyle = colors.text;
      context.fillText(node.label, point.x, point.y + radius + 5);
    }
  }

  context.globalAlpha = 1;
}

function colorWithAlpha(hex, alpha) {
  const value = hex.replace("#", "");
  const size = value.length === 3 ? 1 : 2;
  const parts = value.match(new RegExp(`.{${size}}`, "g"));
  const channels = parts.map((part) => parseInt(size === 1 ? part + part : part, 16));
  return `rgba(${channels[0]}, ${channels[1]}, ${channels[2]}, ${alpha})`;
}

function tick() {
  applyForces();
  draw();
  requestAnimationFrame(tick);
}

function pointerPosition(event) {
  const rect = canvas.getBoundingClientRect();
  return { x: event.clientX - rect.left, y: event.clientY - rect.top };
}

function hitTest(screenX, screenY) {
  let nearest = null;
  let nearestDistance = Infinity;
  for (const node of state.nodes) {
    const point = worldToScreen(node.x, node.y);
    const distance = Math.hypot(screenX - point.x, screenY - point.y);
    const threshold = nodeRadius(node) * Math.max(0.8, state.scale) + 8;
    if (distance <= threshold && distance < nearestDistance) {
      nearest = node;
      nearestDistance = distance;
    }
  }
  return nearest;
}

function selectNode(node) {
  state.selected = node;
  if (!node) {
    detailsTitle.textContent = "Select a node";
    detailsDescription.textContent = "Drag nodes, use the mouse wheel to zoom, and drag the background to pan.";
    detailsMeta.hidden = true;
    detailsLink.hidden = true;
    draw();
    return;
  }

  detailsTitle.textContent = node.label;
  detailsDescription.textContent = node.description || descriptionForType(node.type);

  const rows = [];
  rows.push(["Type", node.type]);
  if (node.language) rows.push(["Language", node.language]);
  if (node.topics && node.topics.length) rows.push(["Topics", node.topics.join(", ")]);
  if (node.type === "repository") rows.push(["Stars", String(node.stars || 0)]);
  if (node.type === "group") rows.push(["Projects", String(node.repositoryCount || 0)]);
  if (node.fork) rows.push(["Repository", "Fork"]);
  if (node.archived) rows.push(["Status", "Archived"]);

  detailsMeta.replaceChildren();
  for (const [term, value] of rows) {
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = term;
    dd.textContent = value;
    detailsMeta.append(dt, dd);
  }
  detailsMeta.hidden = rows.length === 0;

  if (node.url) {
    detailsLink.href = node.url;
    detailsLink.textContent = node.type === "repository" ? "Open repository" : "Open on GitHub";
    detailsLink.hidden = false;
  } else {
    detailsLink.hidden = true;
  }
  draw();
}

function descriptionForType(type) {
  if (type === "owner") return "GitHub account at the center of the public project graph.";
  if (type === "group") return "A curated group of related public projects.";
  if (type === "language") return "Primary language shared by connected repositories.";
  if (type === "topic") return "GitHub topic shared by connected repositories.";
  return "Public GitHub repository.";
}

function resetView() {
  state.scale = Math.min(1, Math.max(0.58, Math.min(state.width / 1050, state.height / 780)));
  state.offsetX = 0;
  state.offsetY = 0;
  state.alpha = Math.max(state.alpha, 0.45);
  selectNode(null);
}

canvas.addEventListener("pointerdown", (event) => {
  canvas.setPointerCapture(event.pointerId);
  const point = pointerPosition(event);
  const node = hitTest(point.x, point.y);
  state.pointerStart = point;
  state.lastPointer = point;
  if (node) {
    state.dragging = node;
    node.fixedBeforeDrag = node.fixed;
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
    state.alpha = Math.max(state.alpha, 0.25);
  } else if (state.panning && state.lastPointer) {
    state.offsetX += point.x - state.lastPointer.x;
    state.offsetY += point.y - state.lastPointer.y;
  } else {
    state.hovered = hitTest(point.x, point.y);
  }
  state.lastPointer = point;
  draw();
});

canvas.addEventListener("pointerup", (event) => {
  const point = pointerPosition(event);
  const moved = state.pointerStart ? Math.hypot(point.x - state.pointerStart.x, point.y - state.pointerStart.y) : 0;
  const draggedNode = state.dragging;
  if (draggedNode) {
    draggedNode.fixed = draggedNode.fixedBeforeDrag || draggedNode.type === "owner";
    delete draggedNode.fixedBeforeDrag;
  }
  state.dragging = null;
  state.panning = false;
  state.pointerStart = null;
  state.lastPointer = null;
  canvas.classList.remove("dragging");
  if (moved < 6) selectNode(hitTest(point.x, point.y));
});

canvas.addEventListener("pointercancel", () => {
  state.dragging = null;
  state.panning = false;
  canvas.classList.remove("dragging");
});

canvas.addEventListener("dblclick", (event) => {
  const point = pointerPosition(event);
  const node = hitTest(point.x, point.y);
  if (node && node.url) window.open(node.url, "_blank", "noopener");
});

canvas.addEventListener(
  "wheel",
  (event) => {
    event.preventDefault();
    const point = pointerPosition(event);
    const before = screenToWorld(point.x, point.y);
    const factor = Math.exp(-event.deltaY * 0.0012);
    state.scale = Math.max(0.25, Math.min(3.5, state.scale * factor));
    const after = worldToScreen(before.x, before.y);
    state.offsetX += point.x - after.x;
    state.offsetY += point.y - after.y;
    draw();
  },
  { passive: false },
);

searchInput.addEventListener("input", () => {
  state.query = searchInput.value.trim().toLowerCase();
  if (state.query) {
    const match = state.nodes.find((node) => matchesQuery(node));
    if (match) selectNode(match);
  } else {
    selectNode(null);
  }
  draw();
});

resetButton.addEventListener("click", () => {
  searchInput.value = "";
  state.query = "";
  resetView();
});

window.addEventListener("resize", resize);

resize();
fetch("graph-data.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then(initializeGraph)
  .catch((error) => {
    statusElement.textContent = `Could not load graph data: ${error.message}`;
    statusElement.hidden = false;
  });
