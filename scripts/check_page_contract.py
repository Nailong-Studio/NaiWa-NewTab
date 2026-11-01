#!/usr/bin/env python3
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if len(__import__('sys').argv) > 1:
    ROOT = Path(__import__('sys').argv[1]).resolve()
MANIFEST = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
ITEMS = json.loads((ROOT / 'wallpapers' / 'list.json').read_text(encoding='utf-8'))
HTML = (ROOT / 'newtab.html').read_text(encoding='utf-8')
CSS = (ROOT / 'css' / 'newtab.css').read_text(encoding='utf-8')
BUILD = (ROOT / 'scripts' / 'build_site.py').read_text(encoding='utf-8')

errors = []

def require(condition, message):
    if not condition:
        errors.append(message)

require(MANIFEST.get('version') == '1.7.2', 'manifest version must be 1.7.2')
require(len(ITEMS) == 212, 'wallpaper list must contain 212 items')
require('bottom:74px' in BUILD, 'preview download banner must stay above the action bar')
require('class="motion-decor"' in HTML, 'motion decoration layer is missing')
require('aria-hidden="true"' in HTML, 'motion decoration must be hidden from assistive technology')
require('pointer-events: none' in CSS, 'motion decoration must not intercept pointer input')
require('.motion-decor' in CSS, 'motion decoration styles are missing')
require('@media (prefers-reduced-motion: reduce)' in CSS, 'reduced-motion fallback is missing')
require('.center {\n  position: fixed;\n  z-index: 5;' in CSS, 'main controls must stack above motion decoration')
require('.meta {\n  position: fixed;\n  z-index: 6;' in CSS, 'footer controls must stack above motion decoration')
require(not re.search(r'<(?:img|video|audio|iframe)\b', HTML, flags=re.I), 'newtab entry must not add external media elements')

zip_paths = sorted((ROOT / 'dist').glob('naiwa-wallpaper-v*.zip'))
require(len(zip_paths) == 1, 'build must produce exactly one extension package')
if zip_paths:
    with zipfile.ZipFile(zip_paths[0]) as package:
        names = set(package.namelist())
        require('manifest.json' in names, 'manifest.json must be at package root')
        require('wallpapers/list.json' in names, 'wallpaper list must be packaged')
        if 'manifest.json' in names:
            packaged_manifest = json.loads(package.read('manifest.json'))
            require(packaged_manifest.get('version') == MANIFEST.get('version'), 'packaged manifest version must match source')
        if 'wallpapers/list.json' in names:
            packaged_items = json.loads(package.read('wallpapers/list.json'))
            require(len(packaged_items) == 212, 'packaged wallpaper list must contain 212 items')
            require(all(item.get('file') in names for item in packaged_items), 'packaged wallpaper files must exist')
            require(all(not item.get('thumb') or item['thumb'] in names for item in packaged_items), 'packaged thumbnails must exist')

if errors:
    for error in errors:
        print('FAIL:', error)
    raise SystemExit(1)

print('PASS: page contract, motion layer, inventory, and package integrity')
