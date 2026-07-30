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
const interactionHint = document.getElementById("interaction-hint");

const themeMedia = window.matchMedia("(prefers-color-scheme: dark)");
const motionMedia = window.matchMedia("(prefers-reduced-motion: reduce)");

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
  startedAt: performance.now(),
  time: 0,
  interacted: false,
};

themeMedia.addEventListener("change", draw);
motionMedia.addEventListener("change", draw);

function palette() {
  if (themeMedia.matches) {
    return {
      background: "#0d1117",
      panel: "#161b22",
      panelStrong: "#21262d",
      edge: "#484f58",
      relation: "#f0883e",
      text: "#f0f6fc",
      muted: "#8b949e",
      border: "#30363d",
      owner: "#58a6ff",
      group: "#1f6feb",
      repository: "#3fb950",
      fork: "#8b949e",
      selected: "#ffffff",
      shadow: "rgba(0, 0, 0, 0.28)",
    };
  }
  return {
    background: "#f6f8fa",
    panel: "#ffffff",
    panelStrong: "#f6f8fa",
    edge: "#afb8c1",
    relation: "#bc4c00",
    text: "#24292f",
    muted: "#57606a",
    border: "#d0d7de",
    owner: "#54aeff",
    group: "#0969da",
    repository: "#2da44e",
    fork: "#8c959f",
    selected: "#24292f",
    shadow: "rgba(31, 35, 40, 0.14)",
  };
}

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

function easeOutBack(value) {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(value - 1, 3) + c1 * Math.pow(value - 1, 2);
}

function nodeDimensions(node) {
  if (node.type === "owner") return { width: 128, height: 48 };
  const estimated = 38 + String(node.label || "").length * 7;
  if (node.type === "group") {
    return { width: clamp(estimated, 148, 218), height: 42 };
  }
  return { width: clamp(estimated, 100, 202), height: 36 };
}

function nodeColor(node, colors) {
  if (node.type === "owner") return colors.owner;
  if (node.type === "group") return colors.group;
  return node.fork ? colors.fork : colors.repository;
}

function resize() {
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.max(1, window.devicePixelRatio || 1);
  state.width = Math.max(1, rect.width);
  state.height = Math.max(1, rect.height);
  canvas.width = Math.floor(state.width * ratio);
  canvas.height = Math.floor(state.height * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  if (state.nodes.length) fitView(false);
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

function buildInitialLayout(data) {
  const groups = data.nodes.filter((node) => node.type === "group");
  const membersByGroup = new Map();
  const membershipByRepository = new Map();

  for (const link of data.links) {
    if (link.type !== "member") continue;
    if (!membersByGroup.has(link.source)) membersByGroup.set(link.source, []);
    membersByGroup.get(link.source).push(link.target);
    if (!membershipByRepository.has(link.target)) membershipByRepository.set(link.target, link.source);
  }

  const groupAnchors = new Map();
  groups.forEach((group, index) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / Math.max(1, groups.length);
    groupAnchors.set(group.id, {
      x: Math.cos(angle) * 225,
      y: Math.sin(angle) * 175,
      angle,
    });
  });

  const repositoryAnchors = new Map();
  for (const group of groups) {
    const anchor = groupAnchors.get(group.id);
    const members = membersByGroup.get(group.id) || [];
    const columns = Math.min(3, Math.max(1, Math.ceil(Math.sqrt(members.length))));
    const outwardX = Math.cos(anchor.angle);
    const outwardY = Math.sin(anchor.angle);
    const tangentX = -outwardY;
    const tangentY = outwardX;

    members.forEach((repositoryId, index) => {
      const row = Math.floor(index / columns);
      const column = index % columns;
      const itemsInRow = Math.min(columns, members.length - row * columns);
      const tangentOffset = (column - (itemsInRow - 1) / 2) * 172;
      const outwardOffset = 142 + row * 72;
      repositoryAnchors.set(repositoryId, {
        x: anchor.x + outwardX * outwardOffset + tangentX * tangentOffset,
        y: anchor.y + outwardY * outwardOffset + tangentY * tangentOffset,
      });
    });
  }

  const ungrouped = data.nodes.filter(
    (node) => node.type === "repository" && !membershipByRepository.has(node.id),
  );
  ungrouped.forEach((node, index) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / Math.max(1, ungrouped.length);
    repositoryAnchors.set(node.id, {
      x: Math.cos(angle) * 405,
      y: Math.sin(angle) * 300,
    });
  });

  return { groupAnchors, repositoryAnchors };
}

function initializeGraph(data) {
  const { groupAnchors, repositoryAnchors } = buildInitialLayout(data);
  let appearanceIndex = 0;

  state.nodes = data.nodes.map((raw) => {
    let anchor = { x: 0, y: 0 };
    if (raw.type === "group") anchor = groupAnchors.get(raw.id) || anchor;
    if (raw.type === "repository") anchor = repositoryAnchors.get(raw.id) || anchor;

    const node = {
      ...raw,
      x: anchor.x,
      y: anchor.y,
      anchorX: anchor.x,
      anchorY: anchor.y,
      vx: 0,
      vy: 0,
      fixed: raw.type === "owner",
      appearDelay: appearanceIndex * 55,
    };
    appearanceIndex += 1;
    return node;
  });

  state.nodeById = new Map(state.nodes.map((node) => [node.id, node]));
  state.links = data.links
    .map((link, index) => ({
      ...link,
      index,
      source: state.nodeById.get(link.source),
      target: state.nodeById.get(link.target),
    }))
    .filter((link) => link.source && link.target);

  statusElement.hidden = true;
  state.startedAt = performance.now();
  state.alpha = 1;
  fitView(true);
  requestAnimationFrame(tick);
}

function linkPhysics(link) {
  if (link.type === "contains") return { preferred: 210, strength: 0.018 };
  if (link.type === "member") return { preferred: 175, strength: 0.018 };
  if (link.type === "owns") return { preferred: 360, strength: 0.008 };
  return { preferred: 145, strength: 0.03 };
}

function isStructuralLink(link) {
  return ["owns", "contains", "member"].includes(link.type);
}

function applyForces() {
  const alpha = state.alpha;

  for (let first = 0; first < state.nodes.length; first += 1) {
    const a = state.nodes[first];
    const aSize = nodeDimensions(a);
    for (let second = first + 1; second < state.nodes.length; second += 1) {
      const b = state.nodes[second];
      const bSize = nodeDimensions(b);
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      if (Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001) dx = 1;

      const overlapX = (aSize.width + bSize.width) / 2 + 20 - Math.abs(dx);
      const overlapY = (aSize.height + bSize.height) / 2 + 18 - Math.abs(dy);
      if (overlapX > 0 && overlapY > 0) {
        const pushX = overlapX < overlapY;
        const amount = (pushX ? overlapX : overlapY) * 0.055 * alpha;
        const direction = pushX ? Math.sign(dx || 1) : Math.sign(dy || 1);
        if (!a.fixed && state.dragging !== a) {
          if (pushX) a.vx -= direction * amount;
          else a.vy -= direction * amount;
        }
        if (!b.fixed && state.dragging !== b) {
          if (pushX) b.vx += direction * amount;
          else b.vy += direction * amount;
        }
      }

      const distanceSquared = Math.max(900, dx * dx + dy * dy);
      const distance = Math.sqrt(distanceSquared);
      const repulsion = 1800 / distanceSquared;
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

  for (const link of state.links) {
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

  for (const node of state.nodes) {
    if (node.fixed || state.dragging === node) continue;
    node.vx += (node.anchorX - node.x) * 0.012 * alpha;
    node.vy += (node.anchorY - node.y) * 0.012 * alpha;
    node.vx *= 0.82;
    node.vy *= 0.82;
    node.x += node.vx;
    node.y += node.vy;
  }

  state.alpha = Math.max(0.012, state.alpha * 0.988);
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

function colorWithAlpha(hex, alpha) {
  const value = hex.replace("#", "");
  const size = value.length === 3 ? 1 : 2;
  const parts = value.match(new RegExp(`.{${size}}`, "g"));
  const channels = parts.map((part) => parseInt(size === 1 ? part + part : part, 16));
  return `rgba(${channels[0]}, ${channels[1]}, ${channels[2]}, ${alpha})`;
}

function roundedRect(x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  context.beginPath();
  context.moveTo(x + r, y);
  context.arcTo(x + width, y, x + width, y + height, r);
  context.arcTo(x + width, y + height, x, y + height, r);
  context.arcTo(x, y + height, x, y, r);
  context.arcTo(x, y, x + width, y, r);
  context.closePath();
}

function nodeAppearance(node) {
  if (motionMedia.matches) return 1;
  const elapsed = state.time - state.startedAt - node.appearDelay;
  return easeOutBack(clamp(elapsed / 420, 0, 1));
}

function drawBackground(colors) {
  context.fillStyle = colors.background;
  context.fillRect(0, 0, state.width, state.height);

  context.fillStyle = colorWithAlpha(colors.edge, themeMedia.matches ? 0.16 : 0.2);
  const spacing = 34;
  const offsetX = ((state.offsetX % spacing) + spacing) % spacing;
  const offsetY = ((state.offsetY % spacing) + spacing) % spacing;
  for (let x = offsetX; x < state.width; x += spacing) {
    for (let y = offsetY; y < state.height; y += spacing) {
      context.beginPath();
      context.arc(x, y, 0.8, 0, Math.PI * 2);
      context.fill();
    }
  }
}

function drawLinks(colors) {
  state.links.forEach((link, index) => {
    const source = worldToScreen(link.source.x, link.source.y);
    const target = worldToScreen(link.target.x, link.target.y);
    const structural = isStructuralLink(link);
    let opacity = structural ? 0.38 : 0.82;
    if (state.selected && (link.source === state.selected || link.target === state.selected)) opacity = 1;
    if (state.query && !(matchesQuery(link.source) || matchesQuery(link.target))) opacity = 0.07;

    const stroke = structural ? colors.edge : colors.relation;
    context.lineWidth = structural ? 1.25 : 2.4;
    context.strokeStyle = colorWithAlpha(stroke, opacity);
    context.setLineDash(structural ? [5, 7] : []);
    context.lineDashOffset = motionMedia.matches ? 0 : -(state.time / 90 + index * 3);
    context.beginPath();
    context.moveTo(source.x, source.y);
    context.lineTo(target.x, target.y);
    context.stroke();
    context.setLineDash([]);

    if (!motionMedia.matches && opacity > 0.15) {
      const progress = (state.time / 2600 + index / Math.max(1, state.links.length)) % 1;
      const x = source.x + (target.x - source.x) * progress;
      const y = source.y + (target.y - source.y) * progress;
      context.fillStyle = colorWithAlpha(stroke, structural ? 0.72 : 0.95);
      context.beginPath();
      context.arc(x, y, structural ? 2 : 2.7, 0, Math.PI * 2);
      context.fill();
    }
  });
}

function drawNode(node, colors) {
  const point = worldToScreen(node.x, node.y);
  const dimensions = nodeDimensions(node);
  const appearance = nodeAppearance(node);
  const highlighted = node === state.selected || node === state.hovered;
  const scale = appearance * (highlighted ? 1.045 : 1);
  const width = dimensions.width * scale * state.scale;
  const height = dimensions.height * scale * state.scale;
  const x = point.x - width / 2;
  const y = point.y - height / 2;

  let opacity = 1;
  if (state.selected && !connectedToSelected(node)) opacity = 0.2;
  if (state.query && !matchesQuery(node)) opacity = 0.1;
  opacity *= clamp(appearance, 0, 1);

  context.save();
  context.globalAlpha = opacity;
  context.shadowColor = colors.shadow;
  context.shadowBlur = highlighted ? 14 : 8;
  context.shadowOffsetY = 3;

  if (node.type === "owner" || node.type === "group") {
    context.fillStyle = nodeColor(node, colors);
    context.strokeStyle = highlighted ? colors.selected : colorWithAlpha(colors.selected, 0.22);
  } else {
    context.fillStyle = colors.panel;
    context.strokeStyle = highlighted ? colors.selected : colors.border;
  }
  context.lineWidth = highlighted ? 2.4 : 1;
  roundedRect(x, y, width, height, Math.min(14, height / 2));
  context.fill();
  context.shadowColor = "transparent";
  context.stroke();

  const fontSize = clamp(12 * state.scale, 10, 15);
  context.font = `${node.type === "repository" ? 500 : 650} ${fontSize}px -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif`;
  context.textBaseline = "middle";

  if (node.type === "repository") {
    const markerX = x + 18 * state.scale;
    context.fillStyle = nodeColor(node, colors);
    context.beginPath();
    context.arc(markerX, point.y, clamp(5.2 * state.scale, 4.2, 6.4), 0, Math.PI * 2);
    context.fill();
    context.fillStyle = colors.text;
    context.textAlign = "left";
    context.fillText(node.label, x + 31 * state.scale, point.y + 0.5);
  } else {
    context.fillStyle = "#ffffff";
    context.textAlign = "center";
    context.fillText(node.label, point.x, point.y + 0.5);
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
    const dimensions = nodeDimensions(node);
    const width = dimensions.width * state.scale;
    const height = dimensions.height * state.scale;
    if (
      screenX >= point.x - width / 2 - 6 &&
      screenX <= point.x + width / 2 + 6 &&
      screenY >= point.y - height / 2 - 6 &&
      screenY <= point.y + height / 2 + 6
    ) {
      return node;
    }
  }
  return null;
}

function descriptionForType(type) {
  if (type === "owner") return "GitHub account at the center of the public project map.";
  if (type === "group") return "A manually curated category of related public projects.";
  return "Public GitHub repository.";
}

function hideInteractionHint() {
  if (state.interacted) return;
  state.interacted = true;
  interactionHint?.classList.add("is-hidden");
}

function selectNode(node) {
  state.selected = node;
  if (!node) {
    detailsTitle.textContent = "Explore the map";
    detailsDescription.textContent = "Select a project or category. Drag to rearrange, scroll to zoom, and double-click a repository to open it.";
    detailsMeta.hidden = true;
    detailsLink.hidden = true;
    draw();
    return;
  }

  hideInteractionHint();
  detailsTitle.textContent = node.label;
  detailsDescription.textContent = node.description || descriptionForType(node.type);
  const rows = [["Type", node.type === "group" ? "category" : node.type]];
  if (node.categories && node.categories.length) rows.push(["Category", node.categories.join(", ")]);
  if (node.language) rows.push(["Language", node.language]);
  if (node.topics && node.topics.length) rows.push(["Topics", node.topics.join(", ")]);
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
    const size = nodeDimensions(node);
    minX = Math.min(minX, node.x - size.width / 2 - 30);
    maxX = Math.max(maxX, node.x + size.width / 2 + 30);
    minY = Math.min(minY, node.y - size.height / 2 - 30);
    maxY = Math.max(maxY, node.y + size.height / 2 + 30);
  }
  const availableWidth = Math.max(320, state.width - (state.width > 900 ? 360 : 36));
  const availableHeight = Math.max(260, state.height - 56);
  state.scale = clamp(Math.min(availableWidth / (maxX - minX), availableHeight / (maxY - minY)), 0.42, 1.15);
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  state.offsetX = -centerX * state.scale + (state.width > 900 ? -135 : 0);
  state.offsetY = -centerY * state.scale;
  state.alpha = Math.max(state.alpha, 0.55);
  if (resetSelection) selectNode(null);
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
    state.alpha = Math.max(state.alpha, 0.28);
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

canvas.addEventListener("pointerup", (event) => {
  const point = pointerPosition(event);
  const moved = state.pointerStart ? Math.hypot(point.x - state.pointerStart.x, point.y - state.pointerStart.y) : 0;
  const draggedNode = state.dragging;
  if (draggedNode) {
    draggedNode.fixed = draggedNode.fixedBeforeDrag || draggedNode.type === "owner";
    if (!draggedNode.fixed) {
      draggedNode.anchorX = draggedNode.x;
      draggedNode.anchorY = draggedNode.y;
    }
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
    hideInteractionHint();
    const point = pointerPosition(event);
    const before = screenToWorld(point.x, point.y);
    const factor = Math.exp(-event.deltaY * 0.0012);
    state.scale = clamp(state.scale * factor, 0.25, 3.5);
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
  draw();
});

resetButton.addEventListener("click", () => {
  searchInput.value = "";
  state.query = "";
  state.nodes.forEach((node) => {
    node.x = node.anchorX;
    node.y = node.anchorY;
    node.vx = 0;
    node.vy = 0;
  });
  fitView(true);
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
    statusElement.textContent = `Could not load project map: ${error.message}`;
    statusElement.hidden = false;
  });
