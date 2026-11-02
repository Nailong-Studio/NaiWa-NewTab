#!/usr/bin/env python3
"""Verify the extension's page contract, motion layer, inventory and package.

This is the repository's quality gate: it must be able to fail. Every check
below compares two independent sources of truth — the manifest against the
packaged copy, the wallpaper list against the files on disk, the version
against the changelog — rather than restating a constant that can drift.

Usage:
    python scripts/check_page_contract.py [repo-root]

Exit code 0 only when every check passes.
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent

# Declared inventory size. Kept in one place so growing the wallpaper pack is a
# single edit; the checks below then enforce that list.json, the ZIP and the
# files on disk all agree with it.
EXPECTED_WALLPAPERS = 212

problems: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        problems.append(message)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


manifest = json.loads(read(ROOT / "manifest.json"))
items = json.loads(read(ROOT / "wallpapers" / "list.json"))
html = read(ROOT / "newtab.html")
css = read(ROOT / "css" / "newtab.css")
newtab_js = read(ROOT / "js" / "newtab.js")
build_script = read(ROOT / "scripts" / "build_site.py")
changelog = read(ROOT / "CHANGELOG.md")

version = manifest.get("version", "")
require(bool(re.match(r"^\d+\.\d+\.\d+$", version)),
        f"manifest version is not MAJOR.MINOR.PATCH: {version!r}")

# --- version agreement -------------------------------------------------------
require(f"## v{version}" in changelog, f"CHANGELOG.md has no entry for v{version}")
require('id="ver"' in html, "version placeholder missing from the page")

# --- inventory ---------------------------------------------------------------
require(len(items) == EXPECTED_WALLPAPERS,
        f"wallpaper list has {len(items)} items, expected {EXPECTED_WALLPAPERS}")

by_category: dict[str, int] = {}
for item in items:
    by_category[item["category"]] = by_category.get(item["category"], 0) + 1
    require(bool(item.get("file")), f"item without file: {item.get('title')!r}")
    require(bool(item.get("thumb")), f"item without thumb: {item.get('title')!r}")
    require((ROOT / item["file"]).exists(), f"wallpaper file missing on disk: {item['file']}")
    require((ROOT / item["thumb"]).exists(), f"thumbnail missing on disk: {item['thumb']}")

for required_category in ("desktop", "vertical", "square", "4k", "poses"):
    require(by_category.get(required_category, 0) > 0,
            f"category {required_category} is empty")

# --- page contract -----------------------------------------------------------
require('class="motion-decor"' in html, "motion decoration layer is missing")
require('aria-hidden="true"' in html, "motion decoration must be hidden from assistive technology")
require("pointer-events: none" in css, "motion decoration must not intercept pointer input")
require(".motion-decor" in css, "motion decoration styles are missing")
require("@media (prefers-reduced-motion: reduce)" in css, "reduced-motion fallback is missing")
require(".center {\n  position: fixed;\n  z-index: 5;" in css,
        "main controls must stack above motion decoration")
require(".meta {\n  position: fixed;\n  z-index: 6;" in css,
        "footer controls must stack above motion decoration")
require(not re.search(r"<(?:img|video|audio|iframe)\b", html, flags=re.I),
        "newtab entry must not add external media elements")

# The bundled pack must be painted immediately: a first paint that waits on a
# network fetch flashes the gradient fallback on every open. Assert on the
# actual body of init(), not on strings that appear elsewhere in the file.
def function_body(source: str, signature: str) -> str:
    """Return the brace-matched body of a function, or '' when not found."""
    start = source.find(signature)
    if start == -1:
        return ""
    brace = source.find("{", start)
    if brace == -1:
        return ""
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace : i + 1]
    return ""


init_body = function_body(newtab_js, "async function init()")
require(bool(init_body), "newtab.js has no async function init()")
if init_body:
    require("settings.source === 'naiwa'" in init_body,
            "init() must special-case the bundled Naiwa source before the first paint")
    require("fetchNaiwaList" in init_body,
            "init() must load the bundled list before falling back to a gradient")
    gradient_at = init_body.find("pickGradient()")
    naiwa_at = init_body.find("fetchNaiwaList")
    require(naiwa_at != -1 and (gradient_at == -1 or naiwa_at < gradient_at),
            "init() must consult the bundled list before any gradient fallback")

# --- preview banner ----------------------------------------------------------
compact_build = build_script.replace(" ", "")
require("bottom:74px" in build_script, "preview download banner must stay above the action bar")
require("ext-download" in build_script,
        "preview banner needs an id so it can yield to the settings panel")
require("z-index:9" in compact_build, "preview banner must stack below the settings panel")

# --- reproducible package ----------------------------------------------------
require("RELEASE_TIMESTAMP" in build_script,
        "build_site.py must pin zip entry timestamps so the package is reproducible")

# --- package -----------------------------------------------------------------
zip_paths = sorted((ROOT / "dist").glob("naiwa-wallpaper-v*.zip"))
require(len(zip_paths) == 1,
        f"build must produce exactly one extension package, found {len(zip_paths)}")

if zip_paths:
    package_name = zip_paths[0].name
    require(package_name == f"naiwa-wallpaper-v{version}.zip",
            f"package name {package_name} does not match manifest version {version}")
    with zipfile.ZipFile(zip_paths[0]) as package:
        names = set(package.namelist())
        require("manifest.json" in names, "manifest.json must be at package root")
        require("wallpapers/list.json" in names, "wallpaper list must be packaged")
        if "manifest.json" in names:
            packaged_manifest = json.loads(package.read("manifest.json"))
            require(packaged_manifest.get("version") == version,
                    "packaged manifest version must match source")
        if "wallpapers/list.json" in names:
            packaged_items = json.loads(package.read("wallpapers/list.json"))
            require(len(packaged_items) == EXPECTED_WALLPAPERS,
                    f"packaged wallpaper list must contain {EXPECTED_WALLPAPERS} items")
            require(all(item.get("file") in names for item in packaged_items),
                    "packaged wallpaper files must exist")
            require(all(not item.get("thumb") or item["thumb"] in names for item in packaged_items),
                    "packaged thumbnails must exist")

if problems:
    for problem in problems:
        print("FAIL:", problem)
    raise SystemExit(1)

print(f"PASS: page contract, motion layer, {EXPECTED_WALLPAPERS}-item inventory, "
      f"package integrity (v{version})")
