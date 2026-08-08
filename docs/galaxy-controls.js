"use strict";

// Interaction and responsive behavior layered on top of graph.js and
// galaxy-layout.js. Keeping it separate makes the mobile/gesture experiment easy
// to tune without coupling it to graph physics.
const focusSelectedButton = document.getElementById("focus-selected");
const detailsPanel = document.getElementById("details");

const galaxyClusterDrag = {
  group: null,
  members: [],
  lastX: 0,
  lastY: 0,
};
let galaxyDragRecoveryNode = null;

const galaxyTouchGesture = {
  pointers: new Map(),
  pinching: false,
  consumed: false,
  lastDistance: 0,
  lastMidpoint: null,
};

function syncGalaxyFocusControl() {
  if (!focusSelectedButton) return;
  const node = state.selected;
  const hasSelection = Boolean(node);
  detailsPanel?.classList.toggle("has-selection", hasSelection);
  document.body.classList.toggle("map-has-selection", hasSelection);

  if (!node || node.type === "owner") {
    focusSelectedButton.hidden = true;
    return;
  }
  focusSelectedButton.hidden = false;
  focusSelectedButton.textContent = node.type === "group" ? "Focus this cluster" : "Center this project";
  focusSelectedButton.setAttribute(
    "aria-label",
    node.type === "group" ? `Focus ${node.label} cluster` : `Center ${node.label}`,
  );
}

const selectNodeBase = selectNode;
selectNode = function selectNodeWithGalaxyControl(node) {
  selectNodeBase(node);
  syncGalaxyFocusControl();
};

focusSelectedButton?.addEventListener("click", () => {
  if (!state.selected) return;
  hideInteractionHint();
  galaxyFocusNode(state.selected);
  canvas.focus({ preventScroll: true });
});

if (detailsPanel) {
  const detailsCloseButton = document.createElement("button");
  detailsCloseButton.type = "button";
  detailsCloseButton.className = "details-close";
  detailsCloseButton.setAttribute("aria-label", "Close project details");
  detailsCloseButton.textContent = "×";
  detailsCloseButton.addEventListener("click", () => {
    selectNode(null);
    canvas.focus({ preventScroll: true });
  });
  detailsPanel.prepend(detailsCloseButton);
}

canvas.setAttribute("tabindex", "0");
canvas.setAttribute(
  "aria-description",
  "Use pointer drag to rearrange. Dragging a category moves its project cluster. Pinch to zoom on touch screens. Use plus and minus to zoom, zero to fit all, and Enter to focus the selected project or category.",
);

// graph.js handles the primary drag. These listeners run afterwards and make a
// category behave like a movable solar system instead of leaving its projects behind.
canvas.addEventListener("pointerdown", () => {
  galaxyDragRecoveryNode = state.dragging;
  if (state.dragging?.type !== "group") {
    galaxyClusterDrag.group = null;
    galaxyClusterDrag.members = [];
    return;
  }

  galaxyClusterDrag.group = state.dragging;
  galaxyClusterDrag.members = galaxyGroupMembers(state.dragging);
  galaxyClusterDrag.lastX = state.dragging.x;
  galaxyClusterDrag.lastY = state.dragging.y;
});

canvas.addEventListener("pointermove", () => {
  const group = galaxyClusterDrag.group;
  if (!group || state.dragging !== group) return;

  const dx = group.x - galaxyClusterDrag.lastX;
  const dy = group.y - galaxyClusterDrag.lastY;
  if (Math.abs(dx) < 0.0001 && Math.abs(dy) < 0.0001) return;

  for (const member of galaxyClusterDrag.members) {
    member.x += dx;
    member.y += dy;
    member.anchorX += dx;
    member.anchorY += dy;
    member.vx = 0;
    member.vy = 0;
  }

  galaxyClusterDrag.lastX = group.x;
  galaxyClusterDrag.lastY = group.y;
  state.alpha = Math.max(state.alpha, 0.34);
});

canvas.addEventListener("pointerup", () => {
  galaxyClusterDrag.group = null;
  galaxyClusterDrag.members = [];
  galaxyDragRecoveryNode = null;
});

canvas.addEventListener("pointercancel", () => {
  // The base handler clears state.dragging before this listener runs. Mirror its
  // normal pointerup release so a cancelled touch gesture cannot leave a node fixed.
  const node = galaxyDragRecoveryNode;
  if (node) {
    node.fixed = node.fixedBeforeDrag || node.type === "owner";
    if (!node.fixed) {
      node.anchorX = node.x;
      node.anchorY = node.y;
    }
    delete node.fixedBeforeDrag;
  }
  galaxyClusterDrag.group = null;
  galaxyClusterDrag.members = [];
  galaxyDragRecoveryNode = null;
});

function galaxyCanvasPoint(event) {
  const rect = canvas.getBoundingClientRect();
  return { x: event.clientX - rect.left, y: event.clientY - rect.top };
}

function galaxyTouchPair() {
  const values = [...galaxyTouchGesture.pointers.values()];
  if (values.length < 2) return null;
  const first = values[0];
  const second = values[1];
  return {
    midpoint: { x: (first.x + second.x) / 2, y: (first.y + second.y) / 2 },
    distance: Math.max(1, Math.hypot(second.x - first.x, second.y - first.y)),
  };
}

function galaxyReleaseBaseDrag() {
  const node = state.dragging || galaxyDragRecoveryNode;
  if (node) {
    node.fixed = node.fixedBeforeDrag || node.type === "owner";
    if (!node.fixed) {
      node.anchorX = node.x;
      node.anchorY = node.y;
    }
    delete node.fixedBeforeDrag;
  }
  state.dragging = null;
  state.panning = false;
  state.pointerStart = null;
  state.lastPointer = null;
  canvas.classList.remove("dragging");
  galaxyClusterDrag.group = null;
  galaxyClusterDrag.members = [];
  galaxyDragRecoveryNode = null;
}

// Capture-phase touch handling wins before graph.js' one-pointer handlers when a
// second finger arrives. One-finger drag remains unchanged; two fingers become a
// stable pinch+pan gesture centered under the fingers.
canvas.addEventListener(
  "pointerdown",
  (event) => {
    if (event.pointerType !== "touch") return;
    galaxyTouchGesture.pointers.set(event.pointerId, galaxyCanvasPoint(event));
    if (galaxyTouchGesture.pointers.size < 2) return;

    canvas.setPointerCapture(event.pointerId);
    galaxyTouchGesture.pinching = true;
    galaxyTouchGesture.consumed = true;
    galaxyReleaseBaseDrag();
    const pair = galaxyTouchPair();
    galaxyTouchGesture.lastDistance = pair?.distance || 1;
    galaxyTouchGesture.lastMidpoint = pair?.midpoint || null;
    hideInteractionHint();
    event.preventDefault();
    event.stopImmediatePropagation();
  },
  { capture: true, passive: false },
);

canvas.addEventListener(
  "pointermove",
  (event) => {
    if (event.pointerType !== "touch" || !galaxyTouchGesture.pointers.has(event.pointerId)) return;
    galaxyTouchGesture.pointers.set(event.pointerId, galaxyCanvasPoint(event));
    if (!galaxyTouchGesture.pinching || galaxyTouchGesture.pointers.size < 2) return;

    const pair = galaxyTouchPair();
    const previousMidpoint = galaxyTouchGesture.lastMidpoint;
    if (!pair || !previousMidpoint) return;

    const worldUnderGesture = screenToWorld(previousMidpoint.x, previousMidpoint.y);
    const factor = pair.distance / Math.max(1, galaxyTouchGesture.lastDistance);
    state.scale = clamp(state.scale * factor, 0.25, 3.5);
    const after = worldToScreen(worldUnderGesture.x, worldUnderGesture.y);
    state.offsetX += pair.midpoint.x - after.x;
    state.offsetY += pair.midpoint.y - after.y;
    galaxyTouchGesture.lastDistance = pair.distance;
    galaxyTouchGesture.lastMidpoint = pair.midpoint;
    draw();
    event.preventDefault();
    event.stopImmediatePropagation();
  },
  { capture: true, passive: false },
);

function galaxyFinishTouchPointer(event) {
  if (event.pointerType !== "touch" || !galaxyTouchGesture.pointers.has(event.pointerId)) return;
  const consume = galaxyTouchGesture.consumed;
  galaxyTouchGesture.pointers.delete(event.pointerId);
  if (galaxyTouchGesture.pointers.size < 2) {
    galaxyTouchGesture.pinching = false;
    galaxyTouchGesture.lastDistance = 0;
    galaxyTouchGesture.lastMidpoint = null;
    galaxyReleaseBaseDrag();
  }
  if (galaxyTouchGesture.pointers.size === 0) galaxyTouchGesture.consumed = false;
  if (!consume) return;
  event.preventDefault();
  event.stopImmediatePropagation();
}

canvas.addEventListener("pointerup", galaxyFinishTouchPointer, { capture: true, passive: false });
canvas.addEventListener("pointercancel", galaxyFinishTouchPointer, { capture: true, passive: false });

canvas.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && state.selected) {
    event.preventDefault();
    galaxyFocusNode(state.selected);
    return;
  }
  if (event.key === "0") {
    event.preventDefault();
    fitView(false);
    return;
  }
  if (event.key !== "+" && event.key !== "=" && event.key !== "-") return;
  event.preventDefault();
  const factor = event.key === "-" ? 1 / 1.16 : 1.16;
  state.scale = clamp(state.scale * factor, 0.25, 3.5);
  draw();
});

// Mobile browser chrome can repeatedly change viewport height while scrolling.
// Preserve the current camera for height-only changes; only refit when the width
// changes substantially or the device orientation changes.
const graphResizeBase = resize;
window.removeEventListener("resize", graphResizeBase);
let galaxyResizeFrame = 0;
let galaxyViewportShape = state.width >= state.height;

resize = function resizeGalaxyViewport() {
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.max(1, window.devicePixelRatio || 1);
  const previousWidth = state.width;
  const previousHeight = state.height;
  const hadViewport = previousWidth > 1 && previousHeight > 1;
  const nextWidth = Math.max(1, rect.width);
  const nextHeight = Math.max(1, rect.height);
  const nextShape = nextWidth >= nextHeight;
  const orientationChanged = hadViewport && nextShape !== galaxyViewportShape;
  const substantialWidthChange = hadViewport && Math.abs(nextWidth - previousWidth) > Math.max(96, previousWidth * 0.18);

  state.width = nextWidth;
  state.height = nextHeight;
  galaxyViewportShape = nextShape;
  canvas.width = Math.floor(nextWidth * ratio);
  canvas.height = Math.floor(nextHeight * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);

  if (state.nodes.length && (!hadViewport || orientationChanged || substantialWidthChange)) fitView(false);
  draw();
};

function scheduleGalaxyResize() {
  if (galaxyResizeFrame) cancelAnimationFrame(galaxyResizeFrame);
  galaxyResizeFrame = requestAnimationFrame(() => {
    galaxyResizeFrame = 0;
    resize();
  });
}

window.addEventListener("resize", scheduleGalaxyResize, { passive: true });
window.visualViewport?.addEventListener("resize", scheduleGalaxyResize, { passive: true });

requestAnimationFrame(() => {
  syncGalaxyFocusControl();
  resize();
});
