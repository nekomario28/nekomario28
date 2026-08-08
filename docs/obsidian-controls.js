"use strict";

// Interaction accessibility layer for the base force graph. It deliberately does
// not change node forces, anchors, grouping, or drag semantics. The goal is to
// keep the graph behavior Obsidian-like while making touch and small screens usable.
const detailsPanel = document.getElementById("details");

function syncObsidianSelectionUi() {
  const hasSelection = Boolean(state.selected);
  detailsPanel?.classList.toggle("has-selection", hasSelection);
  document.body.classList.toggle("map-has-selection", hasSelection);
}

const selectNodeBase = selectNode;
selectNode = function selectNodeWithResponsiveUi(node) {
  selectNodeBase(node);
  syncObsidianSelectionUi();
};

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
  "Drag individual nodes to rearrange the force graph. Drag empty space to pan, pinch or scroll to zoom, press zero to fit all, and press Enter to open the selected repository.",
);

const obsidianTouch = {
  pointers: new Map(),
  pinching: false,
  consumed: false,
  lastDistance: 0,
  lastMidpoint: null,
};

function obsidianCanvasPoint(event) {
  const rect = canvas.getBoundingClientRect();
  return { x: event.clientX - rect.left, y: event.clientY - rect.top };
}

function obsidianTouchPair() {
  const values = [...obsidianTouch.pointers.values()];
  if (values.length < 2) return null;
  const first = values[0];
  const second = values[1];
  return {
    midpoint: { x: (first.x + second.x) / 2, y: (first.y + second.y) / 2 },
    distance: Math.max(1, Math.hypot(second.x - first.x, second.y - first.y)),
  };
}

function obsidianReleaseBaseGesture() {
  const node = state.dragging;
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
}

canvas.addEventListener(
  "pointerdown",
  (event) => {
    if (event.pointerType !== "touch") return;
    obsidianTouch.pointers.set(event.pointerId, obsidianCanvasPoint(event));
    if (obsidianTouch.pointers.size < 2) return;

    canvas.setPointerCapture(event.pointerId);
    obsidianTouch.pinching = true;
    obsidianTouch.consumed = true;
    obsidianReleaseBaseGesture();
    const pair = obsidianTouchPair();
    obsidianTouch.lastDistance = pair?.distance || 1;
    obsidianTouch.lastMidpoint = pair?.midpoint || null;
    hideInteractionHint();
    event.preventDefault();
    event.stopImmediatePropagation();
  },
  { capture: true, passive: false },
);

canvas.addEventListener(
  "pointermove",
  (event) => {
    if (event.pointerType !== "touch" || !obsidianTouch.pointers.has(event.pointerId)) return;
    obsidianTouch.pointers.set(event.pointerId, obsidianCanvasPoint(event));
    if (!obsidianTouch.pinching || obsidianTouch.pointers.size < 2) return;

    const pair = obsidianTouchPair();
    const previousMidpoint = obsidianTouch.lastMidpoint;
    if (!pair || !previousMidpoint) return;

    const worldUnderGesture = screenToWorld(previousMidpoint.x, previousMidpoint.y);
    const factor = pair.distance / Math.max(1, obsidianTouch.lastDistance);
    state.scale = clamp(state.scale * factor, 0.25, 3.5);
    const after = worldToScreen(worldUnderGesture.x, worldUnderGesture.y);
    state.offsetX += pair.midpoint.x - after.x;
    state.offsetY += pair.midpoint.y - after.y;
    obsidianTouch.lastDistance = pair.distance;
    obsidianTouch.lastMidpoint = pair.midpoint;
    draw();
    event.preventDefault();
    event.stopImmediatePropagation();
  },
  { capture: true, passive: false },
);

function obsidianFinishTouch(event) {
  if (event.pointerType !== "touch" || !obsidianTouch.pointers.has(event.pointerId)) return;
  const consume = obsidianTouch.consumed;
  obsidianTouch.pointers.delete(event.pointerId);
  if (obsidianTouch.pointers.size < 2) {
    obsidianTouch.pinching = false;
    obsidianTouch.lastDistance = 0;
    obsidianTouch.lastMidpoint = null;
    obsidianReleaseBaseGesture();
  }
  if (obsidianTouch.pointers.size === 0) obsidianTouch.consumed = false;
  if (!consume) return;
  event.preventDefault();
  event.stopImmediatePropagation();
}

canvas.addEventListener("pointerup", obsidianFinishTouch, { capture: true, passive: false });
canvas.addEventListener("pointercancel", obsidianFinishTouch, { capture: true, passive: false });

canvas.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && state.selected?.url) {
    event.preventDefault();
    window.open(state.selected.url, "_blank", "noopener");
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

// Preserve the current camera when mobile browser chrome changes only the viewport
// height. Refit only for an orientation change or a substantial width change.
const obsidianResizeBase = resize;
window.removeEventListener("resize", obsidianResizeBase);
let obsidianResizeFrame = 0;
let obsidianViewportShape = state.width >= state.height;

resize = function resizeObsidianViewport() {
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.max(1, window.devicePixelRatio || 1);
  const previousWidth = state.width;
  const previousHeight = state.height;
  const hadViewport = previousWidth > 1 && previousHeight > 1;
  const nextWidth = Math.max(1, rect.width);
  const nextHeight = Math.max(1, rect.height);
  const nextShape = nextWidth >= nextHeight;
  const orientationChanged = hadViewport && nextShape !== obsidianViewportShape;
  const substantialWidthChange = hadViewport && Math.abs(nextWidth - previousWidth) > Math.max(96, previousWidth * 0.18);

  state.width = nextWidth;
  state.height = nextHeight;
  obsidianViewportShape = nextShape;
  canvas.width = Math.floor(nextWidth * ratio);
  canvas.height = Math.floor(nextHeight * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);

  if (state.nodes.length && (!hadViewport || orientationChanged || substantialWidthChange)) fitView(false);
  draw();
};

function scheduleObsidianResize() {
  if (obsidianResizeFrame) cancelAnimationFrame(obsidianResizeFrame);
  obsidianResizeFrame = requestAnimationFrame(() => {
    obsidianResizeFrame = 0;
    resize();
  });
}

window.addEventListener("resize", scheduleObsidianResize, { passive: true });
window.visualViewport?.addEventListener("resize", scheduleObsidianResize, { passive: true });

requestAnimationFrame(() => {
  syncObsidianSelectionUi();
  resize();
});
