"use strict";

// Presentation-only galaxy layer for the redesign branch. ?plain=1 leaves the
// force-only graph untouched. Physics lives in galaxy-structure.js.
const cosmicPlainMode = new URLSearchParams(window.location.search).has("plain");

if (!cosmicPlainMode) {
  const cosmicLayer = { stars: [], seed: 0x6e656b6f };

  function cosmicRandom() {
    cosmicLayer.seed = (Math.imul(cosmicLayer.seed, 1664525) + 1013904223) >>> 0;
    return cosmicLayer.seed / 0x100000000;
  }

  const starLayers = [
    { count: 58, radius: [0.4, 0.9], depth: 0.04, alpha: [0.08, 0.18] },
    { count: 34, radius: [0.65, 1.15], depth: 0.08, alpha: [0.10, 0.24] },
    { count: 14, radius: [0.9, 1.45], depth: 0.12, alpha: [0.14, 0.30] },
  ];
  for (const layer of starLayers) {
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
      const twinkle = motionMedia.matches ? 1 : 0.91 + Math.sin(state.time / 1900 + star.phase) * 0.09;
      context.fillStyle = colorWithAlpha(colors.text, star.alpha * twinkle);
      context.beginPath();
      context.arc(x, y, star.radius, 0, Math.PI * 2);
      context.fill();
    }
  }

  function drawGalacticNucleus(colors) {
    const owner = typeof galaxyStructure !== "undefined" ? galaxyStructure.owner : null;
    if (!owner) return;
    const point = worldToScreen(owner.x, owner.y);
    const radius = clamp(150 * state.scale, 74, 220);
    const gradient = context.createRadialGradient(point.x, point.y, 4, point.x, point.y, radius);
    gradient.addColorStop(0, colorWithAlpha(colors.owner, themeMedia.matches ? 0.12 : 0.07));
    gradient.addColorStop(0.18, colorWithAlpha(colors.owner, themeMedia.matches ? 0.055 : 0.032));
    gradient.addColorStop(0.62, colorWithAlpha(colors.owner, 0.012));
    gradient.addColorStop(1, colorWithAlpha(colors.owner, 0));
    context.fillStyle = gradient;
    context.beginPath();
    context.arc(point.x, point.y, radius, 0, Math.PI * 2);
    context.fill();
  }

  function mergeNearbyRadii(radii, threshold = 42) {
    const sorted = radii.filter(Number.isFinite).sort((a, b) => a - b);
    const clusters = [];
    for (const radius of sorted) {
      const cluster = clusters[clusters.length - 1];
      if (!cluster || Math.abs(radius - cluster.average) > threshold) {
        clusters.push({ total: radius, count: 1, average: radius });
      } else {
        cluster.total += radius;
        cluster.count += 1;
        cluster.average = cluster.total / cluster.count;
      }
    }
    return clusters.map((cluster) => cluster.average);
  }

  function drawGalactocentricRings(colors) {
    if (typeof galaxyStructure === "undefined" || !galaxyStructure.initialized || galaxyStructureMotionDisabled()) return;
    const owner = galaxyStructure.owner;
    if (!owner) return;
    const center = worldToScreen(owner.x, owner.y);
    const radii = mergeNearbyRadii(
      Array.from(galaxyStructure.repositories.values(), (target) => target.targetRadius),
      46,
    );

    context.save();
    context.setLineDash([]);
    context.lineWidth = 0.55;
    context.strokeStyle = colorWithAlpha(colors.muted, themeMedia.matches ? 0.095 : 0.07);
    for (const radius of radii) {
      const screenRadius = radius * state.scale;
      if (screenRadius < 18) continue;
      context.beginPath();
      context.arc(center.x, center.y, screenRadius, 0, Math.PI * 2);
      context.stroke();
    }
    context.restore();
  }

  function traceSpiralArm(category) {
    const owner = galaxyStructure.owner;
    if (!owner) return;
    const inner = 175;
    const outer = 535;
    let first = true;
    context.beginPath();
    for (let radius = inner; radius <= outer; radius += 10) {
      const angle = category.armPhase + ((radius - 220) / 285) * 0.42;
      const point = worldToScreen(
        owner.x + Math.cos(angle) * radius,
        owner.y + Math.sin(angle) * radius,
      );
      if (first) {
        context.moveTo(point.x, point.y);
        first = false;
      } else {
        context.lineTo(point.x, point.y);
      }
    }
  }

  function drawSpiralSectors(colors) {
    if (typeof galaxyStructure === "undefined" || !galaxyStructure.initialized || galaxyStructureMotionDisabled()) return;

    context.save();
    context.lineCap = "round";
    context.lineJoin = "round";
    for (const category of galaxyStructure.categories.values()) {
      // Broad low-alpha density band first, then one restrained centerline. The band
      // encodes a semantic sector without turning the category into a separate body.
      traceSpiralArm(category);
      context.strokeStyle = colorWithAlpha(colors.group, themeMedia.matches ? 0.028 : 0.018);
      context.lineWidth = clamp(22 * state.scale, 8, 26);
      context.stroke();

      traceSpiralArm(category);
      context.strokeStyle = colorWithAlpha(colors.group, themeMedia.matches ? 0.13 : 0.075);
      context.lineWidth = 0.7;
      context.stroke();
    }
    context.restore();
  }

  function drawSafeGalaxyDecorations(colors) {
    try {
      context.fillStyle = colors.background;
      context.fillRect(0, 0, state.width, state.height);
      drawStars(colors);
      drawGalacticNucleus(colors);
      drawGalactocentricRings(colors);
      drawSpiralSectors(colors);
    } catch (error) {
      console.warn("Galaxy decoration layer failed; rendering the core graph without decorations.", error);
      context.clearRect(0, 0, state.width, state.height);
      context.fillStyle = colors.background;
      context.fillRect(0, 0, state.width, state.height);
      context.setLineDash([]);
      context.globalAlpha = 1;
    }
  }

  draw = function drawGalaxyMap() {
    if (!context) return;
    const colors = palette();
    context.clearRect(0, 0, state.width, state.height);
    drawSafeGalaxyDecorations(colors);
    drawLinks(colors);
    for (const node of state.nodes) drawNode(node, colors);
    context.globalAlpha = 1;
  };
}
