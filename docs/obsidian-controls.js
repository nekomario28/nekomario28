"use strict";

// Accessibility and touch layer only. It does not modify force settings, node
// positions, graph grouping, or drag semantics beyond coordinating gestures and
// preventing a simple selection click from being mistaken for a forceful drag.
const detailsPanel = document.getElementById("details");

function syncSelectionUi() {
  const hasSelection = Boolean(state.selected);
  detailsPanel?.classList.toggle("has-selection", hasSelection);
  document.body.classList.toggle("map-has-selection", hasSelection);
}

const selectNodeBase = selectNode;
selectNode = function selectNodeWithResponsiveUi(node) {
  selectNodeBase(node);
  syncSelectionUi();
};

if (detailsPanel) {
  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.className = "details-close";
  closeButton.setAttribute("aria-label", "Close project details");
  closeButton.textContent = "×";
  closeButton.addEventListener("click", () => {
    selectNode(null);
    canvas.focus({ preventScroll: true });
  });
  detailsPanel.prepend(closeButton);
}

canvas.setAttribute("tabindex", "0");
canvas.setAttribute(
  "aria-description",
  "Force graph. Drag a node to move it, drag empty space to pan, pinch or scroll to zoom, press zero to fit all, and press Enter to open a selected repository.",
);

function canvasPoint(event) {
  const rect = canvas.getBoundingClientRect();
  return { x: event.clientX - rect.left, y: event.clientY - rect.top };
}

// graph.js starts a drag as soon as pointerdown lands on a node. Preserve that
// baseline behavior for compatibility, but distinguish a click from a real drag at
// the control layer. A click must only select: it must not reheat the entire force
// simulation or erase the node's orbital velocity.
const selectionGesture = {
  pointerId: null,
  start: null,
  candidate: null,
  velocity: null,
  moved: false,
};

function clearSelectionGesture() {
  selectionGesture.pointerId = null;
  selectionGesture.start = null;
  selectionGesture.candidate = null;
  selectionGesture.velocity = null;
  selectionGesture.moved = false;
}

const responsiveReheatBase = reheat;
reheat = function reheatWithoutClickShock(value = 0.72) {
  if (selectionGesture.pointerId !== null) {
    if (!selectionGesture.moved) return;
    return responsiveReheatBase(Math.min(value, 0.12));
  }
  return responsiveReheatBase(value);
};

canvas.addEventListener(
  "pointerdown",
  (event) => {
    if (!event.isPrimary) return;
    const point = canvasPoint(event);
    const candidate = hitTest(point.x, point.y);
    selectionGesture.pointerId = event.pointerId;
    selectionGesture.start = point;
    selectionGesture.candidate = candidate;
    selectionGesture.velocity = candidate ? { vx: candidate.vx || 0, vy: candidate.vy || 0 } : null;
    selectionGesture.moved = false;
  },
  { capture: true, passive: true },
);

canvas.addEventListener(
  "pointermove",
  (event) => {
    if (event.pointerId !== selectionGesture.pointerId || !selectionGesture.start) return;
    const point = canvasPoint(event);
    if (Math.hypot(point.x - selectionGesture.start.x, point.y - selectionGesture.start.y) >= 6) {
      selectionGesture.moved = true;
    }
  },
  { capture: true, passive: true },
);

function finishSelectionGesture(event, cancelled = false) {
  if (event.pointerId !== selectionGesture.pointerId) return;
  const candidate = selectionGesture.candidate;
  const velocity = selectionGesture.velocity;
  const wasClick = !cancelled && !selectionGesture.moved;

  // This listener is registered after graph.js, so the base pointerup handler has
  // already cleared the temporary drag and zeroed velocity. Restore the velocity for
  // a true click so selecting a project does not visibly interrupt its orbit.
  if (wasClick && candidate && velocity) {
    candidate.vx = velocity.vx;
    candidate.vy = velocity.vy;
  }

  clearSelectionGesture();
}

canvas.addEventListener("pointerup", (event) => finishSelectionGesture(event, false));
canvas.addEventListener("pointercancel", (event) => finishSelectionGesture(event, true));

const touchState = {
  pointers: new Map(),
  pinching: false,
  consumed: false,
  lastDistance: 0,
  lastMidpoint: null,
};

function touchPair() {
  const values = [...touchState.pointers.values()];
  if (values.length < 2) return null;
  const first = values[0];
  const second = values[1];
  return {
    midpoint: { x: (first.x + second.x) / 2, y: (first.y + second.y) / 2 },
    distance: Math.max(1, Math.hypot(second.x - first.x, second.y - first.y)),
  };
}

function releaseBaseGesture() {
  if (state.dragging) {
    state.dragging.fixed = false;
    state.dragging.vx = 0;
    state.dragging.vy = 0;
    reheat(0.5);
  }
  state.dragging = null;
  state.panning = false;
  state.pointerStart = null;
  state.lastPointer = null;
  canvas.classList.remove("dragging");
}

canvas.addEventListener(
  "pointerdown",
  (event) => {
    if (event.pointerType !== "touch") return;
    touchState.pointers.set(event.pointerId, canvasPoint(event));
    if (touchState.pointers.size < 2) return;

    touchState.pinching = true;
    touchState.consumed = true;
    releaseBaseGesture();
    const pair = touchPair();
    touchState.lastDistance = pair?.distance || 1;
    touchState.lastMidpoint = pair?.midpoint || null;
    hideInteractionHint();
    event.preventDefault();
    event.stopImmediatePropagation();
  },
  { capture: true, passive: false },
);

canvas.addEventListener(
  "pointermove",
  (event) => {
    if (event.pointerType !== "touch" || !touchState.pointers.has(event.pointerId)) return;
    touchState.pointers.set(event.pointerId, canvasPoint(event));
    if (!touchState.pinching || touchState.pointers.size < 2) return;

    const pair = touchPair();
    const previous = touchState.lastMidpoint;
    if (!pair || !previous) return;
    const world = screenToWorld(previous.x, previous.y);
    const factor = pair.distance / Math.max(1, touchState.lastDistance);
    state.scale = clamp(state.scale * factor, 0.25, 3.5);
    const after = worldToScreen(world.x, world.y);
    state.offsetX += pair.midpoint.x - after.x;
    state.offsetY += pair.midpoint.y - after.y;
    touchState.lastDistance = pair.distance;
    touchState.lastMidpoint = pair.midpoint;
    draw();
    event.preventDefault();
    event.stopImmediatePropagation();
  },
  { capture: true, passive: false },
);

function finishTouch(event) {
  if (event.pointerType !== "touch" || !touchState.pointers.has(event.pointerId)) return;
  const consume = touchState.consumed;
  touchState.pointers.delete(event.pointerId);
  if (touchState.pointers.size < 2) {
    touchState.pinching = false;
    touchState.lastDistance = 0;
    touchState.lastMidpoint = null;
    releaseBaseGesture();
  }
  if (touchState.pointers.size === 0) touchState.consumed = false;
  if (consume) {
    event.preventDefault();
    event.stopImmediatePropagation();
  }
}

canvas.addEventListener("pointerup", finishTouch, { capture: true, passive: false });
canvas.addEventListener("pointercancel", finishTouch, { capture: true, passive: false });

canvas.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && state.selected?.type === "repository" && state.selected.url) {
    event.preventDefault();
    window.open(state.selected.url, "_blank", "noopener");
    return;
  }
  if (event.key === "0") {
    event.preventDefault();
    fitView(false);
    return;
  }
  if (!["+", "=", "-"].includes(event.key)) return;
  event.preventDefault();
  state.scale = clamp(state.scale * (event.key === "-" ? 1 / 1.16 : 1.16), 0.25, 3.5);
  draw();
});

// Mobile browser chrome often changes only viewport height. Resize the backing
// canvas without resetting the force graph or camera.
let resizeFrame = 0;
function scheduleResize() {
  if (resizeFrame) cancelAnimationFrame(resizeFrame);
  resizeFrame = requestAnimationFrame(() => {
    resizeFrame = 0;
    resize();
  });
}
window.visualViewport?.addEventListener("resize", scheduleResize, { passive: true });

requestAnimationFrame(syncSelectionUi);
