#!/usr/bin/env python3
"""Tiny deterministic vector-text renderer for host-constrained README SVGs.

This intentionally does not embed or redistribute a font. It renders a compact
alphanumeric stick alphabet from repository-owned segment geometry. The visible
shape is deterministic across clients while the exact source string remains in
textual accessibility metadata.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass


class UnsupportedGlyph(ValueError):
    pass


# Normalized 14-ish segment geometry. A glyph is a set of named strokes.
_SEGMENTS = {
    "a": ((0.16, 0.04), (0.84, 0.04)),
    "b": ((0.88, 0.08), (0.88, 0.46)),
    "c": ((0.88, 0.54), (0.88, 0.92)),
    "d": ((0.16, 0.96), (0.84, 0.96)),
    "e": ((0.12, 0.54), (0.12, 0.92)),
    "f": ((0.12, 0.08), (0.12, 0.46)),
    "g": ((0.16, 0.50), (0.84, 0.50)),
    "h": ((0.16, 0.08), (0.48, 0.46)),
    "i": ((0.84, 0.08), (0.52, 0.46)),
    "j": ((0.16, 0.92), (0.48, 0.54)),
    "k": ((0.84, 0.92), (0.52, 0.54)),
    "l": ((0.50, 0.08), (0.50, 0.46)),
    "m": ((0.50, 0.54), (0.50, 0.92)),
    "dot": ((0.50, 0.90), (0.50, 0.91)),
    "comma": ((0.50, 0.88), (0.42, 1.00)),
    "slash": ((0.82, 0.08), (0.18, 0.92)),
    "backslash": ((0.18, 0.08), (0.82, 0.92)),
    "under": ((0.16, 1.04), (0.84, 1.04)),
    "quote": ((0.38, 0.06), (0.34, 0.24)),
    "apostrophe": ((0.58, 0.06), (0.54, 0.24)),
}

_GLYPHS = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
    "5": "afgcd", "6": "afgecd", "7": "abc", "8": "abcdefg", "9": "abfgcd",
    "A": "abcefg", "B": "fgecd", "C": "afed", "D": "bgecd", "E": "afged",
    "F": "afge", "G": "afedcg", "H": "fegbc", "I": "adlm", "J": "bced",
    "K": "feik", "L": "fed", "M": "fbhi", "N": "fbhk", "O": "abcdef",
    "P": "abfge", "Q": "abcdefk", "R": "abfgek", "S": "afgcd", "T": "alm",
    "U": "febcd", "V": "fjk", "W": "febcjk", "X": "hijk", "Y": "him", "Z": "aidj",
    "-": "g", "_": "under", ".": "dot", ",": "comma", "/": "slash", "\\": "backslash",
    "'": "apostrophe", '"': "quoteapostrophe", ":": "dot", "+": "glm", "=": "gunder",
    "&": "hijkgd",
}

_TEXT_BLOCK_RE = re.compile(r"<text\b(?P<attrs>[^>]*)>(?P<body>.*?)</text>", re.S | re.I)
_ANY_TEXT_RE = re.compile(r"<text\b", re.I)
_TSPAN_RE = re.compile(r"<tspan\b[^>]*>([^<>]*)</tspan>", re.S | re.I)
_ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*(['\"])(.*?)\2", re.S)


@dataclass(frozen=True)
class TextStyle:
    x: float
    y: float
    size: float
    anchor: str
    color: str
    opacity: str | None
    weight: float


def _attrs(source: str) -> dict[str, str]:
    return {match.group(1): html.unescape(match.group(3)) for match in _ATTR_RE.finditer(source)}


def _number(value: str | None, *, field: str) -> float:
    if value is None:
        raise UnsupportedGlyph(f"safe vector text requires numeric {field}")
    match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*", value)
    if not match:
        raise UnsupportedGlyph(f"safe vector text requires numeric {field}, got {value!r}")
    return float(match.group(1))


def _font_size(attrs: dict[str, str]) -> float:
    if "font-size" in attrs:
        return _number(attrs["font-size"], field="font-size")
    style = attrs.get("style", "")
    match = re.search(r"(?:^|[;\s])(?:font\s*:[^;]*?\s)?(\d+(?:\.\d+)?)px(?:[/;\s]|$)", style)
    if match:
        return float(match.group(1))
    match = re.search(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", style)
    if match:
        return float(match.group(1))
    raise UnsupportedGlyph("safe vector text requires explicit px/font-size geometry")


def _style(attrs: dict[str, str]) -> TextStyle:
    weight_raw = attrs.get("font-weight", "500")
    try:
        weight = float(weight_raw)
    except ValueError:
        weight = 700.0 if weight_raw.lower() in {"bold", "bolder"} else 500.0
    return TextStyle(
        x=_number(attrs.get("x"), field="x"),
        y=_number(attrs.get("y"), field="y"),
        size=_font_size(attrs),
        anchor=attrs.get("text-anchor", "start"),
        color=attrs.get("fill", "currentColor"),
        opacity=attrs.get("opacity"),
        weight=weight,
    )


def _normalize_visible(value: str) -> str:
    value = html.unescape(value)
    return value.replace("…", "...").replace("·", ".")


def _flatten_simple_body(body: str) -> str:
    """Flatten plain text plus simple text-only tspans; reject richer inline markup."""
    parts: list[str] = []
    cursor = 0
    for match in _TSPAN_RE.finditer(body):
        prefix = body[cursor:match.start()]
        if "<" in prefix or ">" in prefix:
            raise UnsupportedGlyph("safe vector mode encountered unsupported nested text markup")
        parts.append(prefix)
        parts.append(match.group(1))
        cursor = match.end()
    suffix = body[cursor:]
    if "<" in suffix or ">" in suffix:
        raise UnsupportedGlyph("safe vector mode encountered unsupported nested text markup")
    parts.append(suffix)
    flattened = "".join(parts)
    if "<" in flattened or ">" in flattened:
        raise UnsupportedGlyph("safe vector mode encountered unsupported nested text markup")
    return flattened


def _glyph_strokes(char: str) -> tuple[str, ...]:
    if char == " ":
        return ()
    pattern = _GLYPHS.get(char.upper())
    if pattern is None:
        raise UnsupportedGlyph(f"unsupported visible safe-mode glyph U+{ord(char):04X} {char!r}")
    names: list[str] = []
    cursor = 0
    multi = sorted(_SEGMENTS, key=len, reverse=True)
    while cursor < len(pattern):
        match = next((name for name in multi if pattern.startswith(name, cursor)), None)
        if match is None:
            raise AssertionError(f"invalid internal glyph pattern for {char!r}: {pattern!r}")
        names.append(match)
        cursor += len(match)
    return tuple(names)


def _vector_group(source_text: str, attrs_source: str, *, adaptive: bool) -> str:
    visible = _normalize_visible(source_text)
    attrs = _attrs(attrs_source)
    style = _style(attrs)
    advance = style.size * 0.68
    glyph_width = style.size * 0.58
    glyph_height = style.size * 0.90
    total_width = max(0.0, advance * len(visible) - (advance - glyph_width))
    if style.anchor == "middle":
        start_x = style.x - total_width / 2
    elif style.anchor == "end":
        start_x = style.x - total_width
    elif style.anchor == "start":
        start_x = style.x
    else:
        raise UnsupportedGlyph(f"unsupported text-anchor {style.anchor!r}")
    top = style.y - style.size * 0.78
    stroke_width = style.size * (0.080 if style.weight < 600 else 0.095)

    commands: list[str] = []
    for index, char in enumerate(visible):
        origin = start_x + index * advance
        for segment_name in _glyph_strokes(char):
            (x1, y1), (x2, y2) = _SEGMENTS[segment_name]
            commands.append(
                f"M{origin + x1 * glyph_width:.2f},{top + y1 * glyph_height:.2f} "
                f"L{origin + x2 * glyph_width:.2f},{top + y2 * glyph_height:.2f}"
            )

    escaped = html.escape(source_text, quote=True)
    opacity = f' opacity="{html.escape(style.opacity, quote=True)}"' if style.opacity else ""
    adaptive_attrs = (
        f' class="v9-adaptive-vector-text" color="#f0f6fc" '
        f'data-vector-original-color="{html.escape(style.color, quote=True)}"'
        if adaptive else ""
    )
    stroke = "currentColor" if adaptive else style.color
    if not commands:
        return (
            f'<g data-vector-text="v1" aria-label="{escaped}"{adaptive_attrs}>'
            f'<title>{html.escape(source_text)}</title></g>'
        )
    return (
        f'<g data-vector-text="v1" aria-label="{escaped}"{opacity}{adaptive_attrs}>'
        f'<title>{html.escape(source_text)}</title>'
        f'<path d="{" ".join(commands)}" fill="none" stroke="{html.escape(stroke, quote=True)}" '
        f'stroke-width="{stroke_width:.2f}" stroke-linecap="round" stroke-linejoin="round"/>'
        f'</g>'
    )


def vectorize_visible_text(svg: str, *, adaptive: bool = False) -> tuple[str, int]:
    """Replace supported visible SVG <text> nodes with deterministic vector strokes.

    `adaptive=True` uses `currentColor` plus a stable dark fallback so the caller
    can attach a host appearance policy without introducing client font authority.
    """
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        source = _flatten_simple_body(match.group("body"))
        count += 1
        return _vector_group(source, match.group("attrs"), adaptive=adaptive)

    result = _TEXT_BLOCK_RE.sub(replace, svg)
    if _ANY_TEXT_RE.search(result):
        remaining = _ANY_TEXT_RE.search(result)
        snippet = result[max(0, remaining.start() - 80):remaining.start() + 240] if remaining else ""
        raise UnsupportedGlyph(f"safe vector mode left unsupported <text> markup: {snippet!r}")
    return result, count


def suppress_visible_text(svg: str) -> tuple[str, int]:
    """Remove visible <text> nodes while leaving <title>/<desc>/aria metadata intact."""
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return ""

    result = _TEXT_BLOCK_RE.sub(replace, svg)
    if _ANY_TEXT_RE.search(result):
        raise UnsupportedGlyph("minimal mode could not suppress all visible <text> markup")
    return result, count


def visible_text_count(svg: str) -> int:
    return len(_ANY_TEXT_RE.findall(svg))
