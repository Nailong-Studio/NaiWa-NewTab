#!/usr/bin/env python3
"""生成扩展的在线预览页与离线安装包。

- index.html：newtab.html 的同款预览，右下角加「下载扩展」按钮
- dist/naiwa-wallpaper-v<version>.zip：可直接在 chrome://extensions 加载的扩展本体
  （manifest.json 必须在压缩包根目录，否则「加载已解压的扩展程序」会报错）

用法：python3 scripts/build_site.py
"""
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'

manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
version = manifest['version']

BANNER = """
<a href="dist/naiwa-wallpaper-v%s.zip" download style="position:fixed;right:16px;bottom:16px;z-index:99;
display:inline-flex;align-items:center;gap:8px;padding:9px 16px;border-radius:999px;text-decoration:none;
font:500 13px/1.4 'Noto Sans SC',sans-serif;color:#12100c;background:linear-gradient(165deg,#FFD54F,#D9B45B);
box-shadow:0 8px 24px rgba(0,0,0,.45)">⤓ 下载扩展 v%s · 离线安装</a>
""" % (version, version)

newtab = (ROOT / 'newtab.html').read_text(encoding='utf-8')
(ROOT / 'index.html').write_text(newtab.replace('</body>', BANNER + '</body>'), encoding='utf-8')

DIST.mkdir(exist_ok=True)
zip_path = DIST / ('naiwa-wallpaper-v%s.zip' % version)
if zip_path.exists():
    zip_path.unlink()

SKIP_DIRS = {'.git', 'scripts', 'dist', 'node_modules', '__pycache__'}
SKIP_FILES = {'index.html', '.gitignore'}

count = 0
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        if rel.name in SKIP_FILES or rel.name.endswith('.zip'):
            continue
        z.write(p, rel.as_posix())
        count += 1

with zipfile.ZipFile(zip_path) as z:
    assert 'manifest.json' in z.namelist(), 'manifest.json 必须在压缩包根目录'

print('index.html + %s (%d files, %.1f MB)' % (zip_path.name, count, zip_path.stat().st_size / 1e6))
