"use strict";

// Presentation-only galaxy layer. ?plain=1 leaves graph.js drawing untouched.
const cosmicPlainMode = new URLSearchParams(window.location.search).has("plain");

if (!cosmicPlainMode) {
  const cosmicLayer = { stars: [], seed: 0x6e656b6f };

  function cosmicRandom() {
    cosmicLayer.seed = (Math.imul(cosmicLayer.seed, 1664525) + 1013904223) >>> 0;
    return cosmicLayer.seed / 0x100000000;
  }

  const layers = [
    { count: 62, radius: [0.45, 0.95], depth: 0.05, alpha: [0.10, 0.22] },
    { count: 38, radius: [0.7, 1.25], depth: 0.10, alpha: [0.14, 0.30] },
    { count: 18, radius: [1.0, 1.65], depth: 0.17, alpha: [0.18, 0.38] },
  ];
  for (const layer of layers) {
    for (let index = 0; index < layer.count; index += 1) {
      cosmicLayer.stars.push({
        x: cosmicRandom(),
        y: cosmicRandom(),
        radius: layer.radius[0] + cosmicRandom() * (layer.radius[1] - layer.radius[0]),
        depth: layer.depth,
        alpha: layer.alpha[0] + cosmicRandom() * (layer.alpha[1] - layer.alpha[0]),
        phase: cosmicRandom() * Math.PI * 2,
      });
    }
  }

  function drawStars(colors) {
    for (const star of cosmicLayer.stars) {
      const parallaxX = motionMedia.matches ? 0 : state.offsetX * star.depth;
      const parallaxY = motionMedia.matches ? 0 : state.offsetY * star.depth;
      const x = ((star.x * state.width + parallaxX) % state.width + state.width) % state.width;
      const y = ((star.y * state.height + parallaxY) % state.height + state.height) % state.height;
      const twinkle = motionMedia.matches ? 1 : 0.88 + Math.sin(state.time / 1450 + star.phase) * 0.12;
      context.fillStyle = colorWithAlpha(colors.text, star.alpha * twinkle);
      context.beginPath();
      context.arc(x, y, star.radius, 0, Math.PI * 2);
      context.fill();
    }
  }

  function drawOwnerHalo(colors) {
    const owner = state.nodes.find((node) => node.type === "owner");
    if (!owner) return;
    const point = worldToScreen(owner.x, owner.y);
    const radius = clamp(175 * state.scale, 90, 250);
    const gradient = context.createRadialGradient(point.x, point.y, 8, point.x, point.y, radius);
    gradient.addColorStop(0, colorWithAlpha(colors.owner, themeMedia.matches ? 0.055 : 0.035));
    gradient.addColorStop(0.55, colorWithAlpha(colors.owner, 0.018));
    gradient.addColorStop(1, colorWithAlpha(colors.owner, 0));
    context.fillStyle = gradient;
    context.beginPath();
    context.arc(point.x, point.y, radius, 0, Math.PI * 2);
    context.fill();
  }

  function drawCategoryNebulae(colors) {
    for (const group of state.nodes.filter((node) => node.type === "group")) {
      const point = worldToScreen(group.x, group.y);
      const radius = clamp(82 * state.scale, 42, 120);
      const gradient = context.createRadialGradient(point.x, point.y, 3, point.x, point.y, radius);
      gradient.addColorStop(0, colorWithAlpha(colors.group, themeMedia.matches ? 0.085 : 0.045));
      gradient.addColorStop(0.6, colorWithAlpha(colors.owner, 0.018));
      gradient.addColorStop(1, colorWithAlpha(colors.group, 0));
      context.fillStyle = gradient;
      context.beginPath();
      context.arc(point.x, point.y, radius, 0, Math.PI * 2);
      context.fill();
    }
  }

  function drawOrbitGuides(colors) {
    if (typeof galaxyOrbits === "undefined" || !galaxyOrbits.initialized || galaxyOrbitMotionDisabled()) return;
    const owner = galaxyOrbits.owner;
    if (!owner) return;
    const ownerPoint = worldToScreen(owner.x, owner.y);

    context.save();
    context.setLineDash([2, 7]);
    context.lineWidth = 0.8;
    context.strokeStyle = colorWithAlpha(colors.owner, themeMedia.matches ? 0.12 : 0.075);
    for (const group of state.nodes.filter((node) => node.type === "group")) {
      const radius = Math.hypot(group.x - owner.x, group.y - owner.y) * state.scale;
      if (radius < 8) continue;
      context.beginPath();
      context.arc(ownerPoint.x, ownerPoint.y, radius, 0, Math.PI * 2);
      context.stroke();
    }

    context.strokeStyle = colorWithAlpha(colors.group, themeMedia.matches ? 0.105 : 0.065);
    for (const [repositoryId, parent] of galaxyOrbits.parentByRepository) {
      const node = state.nodeById.get(repositoryId);
      if (!node) continue;
      const center = worldToScreen(parent.x, parent.y);
      const radius = Math.hypot(node.x - parent.x, node.y - parent.y) * state.scale;
      if (radius < 8) continue;
      context.beginPath();
      context.arc(center.x, center.y, radius, 0, Math.PI * 2);
      context.stroke();
    }
    context.restore();
  }

  drawBackground = function drawGalaxyBackground(colors) {
    context.fillStyle = colors.background;
    context.fillRect(0, 0, state.width, state.height);
    drawStars(colors);
    drawOwnerHalo(colors);
  };

  draw = function drawGalaxyMap() {
    if (!context) return;
    const colors = palette();
    context.clearRect(0, 0, state.width, state.height);
    drawBackground(colors);
    drawCategoryNebulae(colors);
    drawOrbitGuides(colors);
    drawLinks(colors);
    for (const node of state.nodes) drawNode(node, colors);
    context.globalAlpha = 1;
  };
}
