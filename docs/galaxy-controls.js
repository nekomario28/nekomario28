"use strict";

// Small interaction layer for touch and keyboard users. It depends on the
// selection/camera primitives supplied by graph.js and galaxy-layout.js.
const focusSelectedButton = document.getElementById("focus-selected");

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
  "Use pointer drag to rearrange. Use plus and minus to zoom, zero to fit all, and Enter to focus the selected project or category.",
);

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
