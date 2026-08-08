"use strict";

// Optional presentation layer for the project map. It deliberately leaves graph
// layout, collision handling, selection, search and interaction logic untouched.
const cosmicLayer = {
  stars: [],
  seed: 0x6e656b6f,
};

function cosmicRandom() {
  cosmicLayer.seed = (Math.imul(cosmicLayer.seed, 1664525) + 1013904223) >>> 0;
  return cosmicLayer.seed / 0x100000000;
}

function buildCosmicStars() {
  cosmicLayer.seed = 0x6e656b6f;
  cosmicLayer.stars = [];
  const layers = [
    { count: 62, radius: [0.45, 0.95], depth: 0.055, alpha: [0.10, 0.22] },
    { count: 38, radius: [0.7, 1.25], depth: 0.11, alpha: [0.14, 0.30] },
    { count: 18, radius: [1.0, 1.65], depth: 0.18, alpha: [0.18, 0.38] },
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
}

buildCosmicStars();

function drawCosmicStarField(colors) {
  for (const star of cosmicLayer.stars) {
    const parallaxX = motionMedia.matches ? 0 : state.offsetX * star.depth;
    const parallaxY = motionMedia.matches ? 0 : state.offsetY * star.depth;
    const rawX = star.x * state.width + parallaxX;
    const rawY = star.y * state.height + parallaxY;
    const x = ((rawX % state.width) + state.width) % state.width;
    const y = ((rawY % state.height) + state.height) % state.height;
    const twinkle = motionMedia.matches ? 1 : 0.88 + Math.sin(state.time / 1450 + star.phase) * 0.12;
    const depthBoost = 0.72 + star.depth * 1.55;

    context.fillStyle = colorWithAlpha(colors.text, star.alpha * twinkle * depthBoost);
    context.beginPath();
    context.arc(x, y, star.radius, 0, Math.PI * 2);
    context.fill();
  }
}

function drawGalaxyArms(colors) {
  const owner = state.nodes.find((node) => node.type === "owner");
  if (!owner) return;
  const point = worldToScreen(owner.x, owner.y);
  const baseOpacity = themeMedia.matches ? 0.10 : 0.055;

  context.save();
  context.translate(point.x, point.y);
  context.rotate(-0.22);
  context.lineCap = "round";

  for (let arm = 0; arm < 3; arm += 1) {
    context.save();
    context.rotate((arm * Math.PI * 2) / 3);
    context.strokeStyle = colorWithAlpha(colors.owner, baseOpacity * (1 - arm * 0.08));
    context.lineWidth = 1.1;
    context.beginPath();
    context.ellipse(0, 0, 155 * state.scale, 62 * state.scale, 0, -0.65, 1.55);
    context.stroke();
    context.restore();
  }
  context.restore();
}

function drawCategoryNebulae(colors) {
  const groups = state.nodes.filter((node) => node.type === "group");
  groups.forEach((node, index) => {
    const point = worldToScreen(node.x, node.y);
    const selected = node === state.selected;
    const faded = state.selected && !connectedToSelected(node);
    const queryFaded = state.query && !matchesQuery(node);
    const radius = clamp(112 * state.scale, 58, 150);
    let intensity = selected ? 1 : 0.62;
    if (faded || queryFaded) intensity = 0.20;
    const coreAlpha = (themeMedia.matches ? 0.105 : 0.065) * intensity;

    context.save();
    context.translate(point.x, point.y);
    context.rotate((index * 0.83 + node.phase * Math.PI) % Math.PI);
    context.scale(1.42, 0.78);

    const gradient = context.createRadialGradient(0, 0, 4, 0, 0, radius);
    gradient.addColorStop(0, colorWithAlpha(colors.group, coreAlpha));
    gradient.addColorStop(0.42, colorWithAlpha(colors.owner, coreAlpha * 0.58));
    gradient.addColorStop(0.76, colorWithAlpha(colors.group, coreAlpha * 0.16));
    gradient.addColorStop(1, colorWithAlpha(colors.group, 0));

    context.fillStyle = gradient;
    context.beginPath();
    context.arc(0, 0, radius, 0, Math.PI * 2);
    context.fill();
    context.restore();
  });
}

function drawProjectOrbits(colors) {
  if (typeof galaxyMotion === "undefined" || !galaxyMotion.initialized) return;

  const seen = new Set();
  context.save();
  context.lineWidth = 1;
  context.setLineDash([2.5, 8]);
  context.lineDashOffset = motionMedia.matches ? 0 : -(state.time / 90) % 18;

  for (const orbit of galaxyMotion.repositories.values()) {
    if (orbit.detached || !orbit.parent) continue;
    const roundedRadius = Math.round(orbit.radius / 36) * 36;
    const key = `${orbit.parent.id}:${roundedRadius}`;
    if (seen.has(key)) continue;
    seen.add(key);

    const center = worldToScreen(orbit.parent.x, orbit.parent.y);
    const selectedCluster = state.selected === orbit.parent || galaxyMotionClusterId(state.selected) === orbit.parent.id;
    const opacity = selectedCluster ? (themeMedia.matches ? 0.24 : 0.16) : (themeMedia.matches ? 0.105 : 0.07);

    context.strokeStyle = colorWithAlpha(colors.group, opacity);
    context.beginPath();
    context.ellipse(
      center.x,
      center.y,
      roundedRadius * state.scale,
      roundedRadius * orbit.flatten * state.scale,
      0,
      0,
      Math.PI * 2,
    );
    context.stroke();
  }

  context.restore();
}

// Replace only the presentation functions from graph.js. Graph physics and state
// remain owned by graph.js, which keeps this layer easy to remove or tune later.
drawBackground = function drawCosmicBackground(colors) {
  context.fillStyle = colors.background;
  context.fillRect(0, 0, state.width, state.height);
  drawCosmicStarField(colors);
  drawGalaxyArms(colors);
};

draw = function drawCosmicMap() {
  if (!context) return;
  const colors = palette();
  context.clearRect(0, 0, state.width, state.height);
  drawBackground(colors);
  drawCategoryNebulae(colors);
  drawProjectOrbits(colors);
  drawLinks(colors);
  for (const node of state.nodes) drawNode(node, colors);
  context.globalAlpha = 1;
};
