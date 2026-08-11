"use strict";

// Presentation-only galaxy layer for the redesign branch. ?plain=1 leaves the
// force-only graph untouched. Physics lives in galaxy-structure.js.
const cosmicPlainMode = new URLSearchParams(window.location.search).has("plain");

if (!cosmicPlainMode) {
  const cosmicLayer = { particles: [], seed: 0x6e656b6f };

  function cosmicRandom() {
    cosmicLayer.seed = (Math.imul(cosmicLayer.seed, 1664525) + 1013904223) >>> 0;
    return cosmicLayer.seed / 0x100000000;
  }

  for (let index = 0; index < 190; index += 1) {
    cosmicLayer.particles.push({
      radius: 70 + Math.sqrt(cosmicRandom()) * 500,
      armSeed: Math.floor(cosmicRandom() * 16),
      armOffset: (cosmicRandom() - 0.5) * 0.62,
      size: 0.38 + cosmicRandom() * 0.92,
      alpha: 0.045 + cosmicRandom() * 0.14,
      phase: cosmicRandom() * Math.PI * 2,
    });
  }

  function drawDiskParticles(colors) {
    if (typeof galaxyStructure === "undefined" || !galaxyStructure.initialized || !galaxyStructure.owner) return;
    const owner = galaxyStructure.owner;
    const categories = Array.from(galaxyStructure.categories.values());
    if (!categories.length) return;

    for (const particle of cosmicLayer.particles) {
      const category = categories[particle.armSeed % categories.length];
      const spiral = ((particle.radius - 220) / 285) * 0.42;
      const angle = category.armPhase + spiral + particle.armOffset;
      const point = worldToScreen(
        owner.x + Math.cos(angle) * particle.radius,
        owner.y + Math.sin(angle) * particle.radius,
      );
      if (point.x < -4 || point.y < -4 || point.x > state.width + 4 || point.y > state.height + 4) continue;
      const twinkle = motionMedia.matches ? 1 : 0.94 + Math.sin(state.time / 2400 + particle.phase) * 0.06;
      context.fillStyle = colorWithAlpha(colors.text, particle.alpha * twinkle);
      context.beginPath();
      context.arc(point.x, point.y, Math.max(0.35, particle.size * Math.sqrt(state.scale)), 0, Math.PI * 2);
      context.fill();
    }
  }

  function drawGalacticNucleus(colors) {
    const owner = typeof galaxyStructure !== "undefined" ? galaxyStructure.owner : null;
    if (!owner) return;
    const point = worldToScreen(owner.x, owner.y);
    const radius = clamp(150 * state.scale, 74, 220);
    const gradient = context.createRadialGradient(point.x, point.y, 4, point.x, point.y, radius);
    gradient.addColorStop(0, colorWithAlpha(colors.owner, themeMedia.matches ? 0.13 : 0.075));
    gradient.addColorStop(0.18, colorWithAlpha(colors.owner, themeMedia.matches ? 0.06 : 0.034));
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
    context.lineWidth = 0.5;
    context.strokeStyle = colorWithAlpha(colors.muted, themeMedia.matches ? 0.075 : 0.052);
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
    let first = true;
    context.beginPath();
    for (let radius = 165; radius <= 545; radius += 9) {
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
      traceSpiralArm(category);
      context.strokeStyle = colorWithAlpha(colors.group, themeMedia.matches ? 0.024 : 0.014);
      context.lineWidth = clamp(24 * state.scale, 8, 28);
      context.stroke();

      traceSpiralArm(category);
      context.strokeStyle = colorWithAlpha(colors.group, themeMedia.matches ? 0.105 : 0.06);
      context.lineWidth = 0.65;
      context.stroke();
    }
    context.restore();
  }

  function drawGalaxyLinks(colors) {
    for (const link of state.links) {
      const source = worldToScreen(link.source.x, link.source.y);
      const target = worldToScreen(link.target.x, link.target.y);
      const structural = link.type !== "relation";
      let opacity = structural ? 0.045 : 0.72;

      if (state.selected && (link.source === state.selected || link.target === state.selected)) {
        opacity = structural ? 0.34 : 0.94;
      } else if (state.selected) {
        opacity = structural ? 0.018 : 0.10;
      }
      if (state.query && !(matchesQuery(link.source) || matchesQuery(link.target))) opacity *= 0.35;

      context.strokeStyle = colorWithAlpha(link.type === "relation" ? colors.relation : colors.edge, opacity);
      context.lineWidth = link.type === "relation" ? 1.45 : 0.65;
      context.setLineDash([]);
      context.beginPath();
      context.moveTo(source.x, source.y);
      context.lineTo(target.x, target.y);
      context.stroke();
    }
  }

  function drawCategorySectorNode(node, colors) {
    const point = worldToScreen(node.x, node.y);
    const highlighted = node === state.selected || node === state.hovered;
    let opacity = 0.82;
    if (state.selected && !connectedToSelected(node)) opacity = 0.16;
    if (state.query && !matchesQuery(node)) opacity = 0.09;

    context.save();
    context.globalAlpha = opacity;
    context.strokeStyle = highlighted ? colors.selected : colorWithAlpha(colors.group, 0.82);
    context.lineWidth = highlighted ? 1.6 : 1;
    context.beginPath();
    context.arc(point.x, point.y, highlighted ? 6.5 : 5, 0, Math.PI * 2);
    context.stroke();

    const fontSize = clamp(11.5 * state.scale, 9, 13);
    context.font = `600 ${fontSize}px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif`;
    context.textAlign = "center";
    context.textBaseline = "middle";
    const labelY = point.y + clamp(17 * state.scale, 13, 20);
    context.strokeStyle = colorWithAlpha(colors.background, 0.94);
    context.lineWidth = 3;
    context.strokeText(displayLabel(node), point.x, labelY);
    context.fillStyle = colors.text;
    context.fillText(displayLabel(node), point.x, labelY);
    context.restore();
  }

  function drawOwnerNucleusNode(node, colors) {
    const point = worldToScreen(node.x, node.y);
    const highlighted = node === state.selected || node === state.hovered;
    context.save();
    context.fillStyle = colors.owner;
    context.beginPath();
    context.arc(point.x, point.y, highlighted ? 8 : 6.5, 0, Math.PI * 2);
    context.fill();
    context.strokeStyle = colorWithAlpha(colors.owner, highlighted ? 0.95 : 0.58);
    context.lineWidth = 1;
    context.beginPath();
    context.arc(point.x, point.y, highlighted ? 14 : 11.5, 0, Math.PI * 2);
    context.stroke();

    const fontSize = clamp(12 * state.scale, 9.5, 14);
    context.font = `600 ${fontSize}px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif`;
    context.textAlign = "center";
    context.textBaseline = "middle";
    const labelY = point.y + clamp(23 * state.scale, 17, 27);
    context.strokeStyle = colorWithAlpha(colors.background, 0.95);
    context.lineWidth = 3.5;
    context.strokeText(displayLabel(node), point.x, labelY);
    context.fillStyle = colors.text;
    context.fillText(displayLabel(node), point.x, labelY);
    context.restore();
  }

  function drawGalaxyNode(node, colors) {
    if (node.type === "group") {
      drawCategorySectorNode(node, colors);
      return;
    }
    if (node.type === "owner") {
      drawOwnerNucleusNode(node, colors);
      return;
    }
    drawNode(node, colors);
  }

  function drawSafeGalaxyDecorations(colors) {
    try {
      context.fillStyle = colors.background;
      context.fillRect(0, 0, state.width, state.height);
      drawDiskParticles(colors);
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
    drawGalaxyLinks(colors);
    for (const node of state.nodes) drawGalaxyNode(node, colors);
    context.globalAlpha = 1;
  };
}
