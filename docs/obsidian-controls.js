"use strict";

// Accessibility and touch layer only. It does not modify force settings, node
// positions, graph grouping, or drag semantics beyond coordinating pinch gestures.
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

const touchState = {
  pointers: new Map(),
  pinching: false,
  consumed: false,
  lastDistance: 0,
  lastMidpoint: null,
};

function canvasPoint(event) {
  const rect = canvas.getBoundingClientRect();
  return { x: event.clientX - rect.left, y: event.clientY - rect.top };
}

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
