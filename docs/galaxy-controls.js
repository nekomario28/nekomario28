"use strict";

// Small interaction layer for touch and keyboard users. It depends on the
// selection/camera primitives supplied by graph.js and galaxy-layout.js.
const focusSelectedButton = document.getElementById("focus-selected");

const galaxyClusterDrag = {
  group: null,
  members: [],
  lastX: 0,
  lastY: 0,
};
let galaxyDragRecoveryNode = null;

function syncGalaxyFocusControl() {
  if (!focusSelectedButton) return;
  const node = state.selected;
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

canvas.setAttribute("tabindex", "0");
canvas.setAttribute(
  "aria-description",
  "Use pointer drag to rearrange. Dragging a category moves its project cluster. Use plus and minus to zoom, zero to fit all, and Enter to focus the selected project or category.",
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

requestAnimationFrame(syncGalaxyFocusControl);
