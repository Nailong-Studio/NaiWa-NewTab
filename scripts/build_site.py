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
<a href="dist/naiwa-wallpaper-v%s.zip" download style="position:fixed;right:16px;bottom:74px;z-index:99;
display:inline-flex;align-items:center;gap:8px;padding:9px 16px;border-radius:999px;text-decoration:none;
font:500 13px/1.4 'Noto Sans SC',sans-serif;color:#12100c;background:linear-gradient(165deg,#FFD54F,#D9B45B);
box-shadow:0 8px 24px rgba(0,0,0,.45)">⤓ 下载扩展 v%s · 离线安装</a>
""" % (version, version)

newtab = (ROOT / 'newtab.html').read_text(encoding='utf-8')

# The download banner is a preview-only affordance. It must not cover the
# settings panel footer (shortcut hints, version), so it hides whenever the
# panel is open and shifts out of the way on narrow screens.
CONTROL_SCRIPT = '''
<script>
(function(){
  var banner = document.getElementById('ext-download');
  var panel = document.getElementById('panel');
  if (!banner || !panel) return;
  var sync = function(){ banner.style.opacity = panel.classList.contains('open') ? '0' : '1'; };
  new MutationObserver(sync).observe(panel, {attributes:true, attributeFilter:['class']});
  sync();
})();
</script>
'''

BANNER = BANNER.replace('<a href="dist/', '<a id="ext-download" href="dist/')
BANNER = BANNER.replace('z-index:99;', 'z-index:9;transition:opacity .25s ease;')
(ROOT / 'index.html').write_text(
    newtab.replace('</body>', BANNER + CONTROL_SCRIPT + '</body>'), encoding='utf-8')

DIST.mkdir(exist_ok=True)
zip_path = DIST / ('naiwa-wallpaper-v%s.zip' % version)
if zip_path.exists():
    zip_path.unlink()

# Fixed timestamp for every entry: 1980-01-01, the earliest value the ZIP
# format allows. Chosen so the archive hash depends only on content.
RELEASE_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

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
        # Write through ZipInfo with a fixed timestamp so the package is
        # byte-reproducible: the same tree must yield the same SHA-256, which is
        # what a published release digest is for. Per-file mtimes would make
        # every build differ for no reason.
        info = zipfile.ZipInfo(rel.as_posix(), date_time=RELEASE_TIMESTAMP)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, p.read_bytes(), compresslevel=9)
        count += 1

with zipfile.ZipFile(zip_path) as z:
    assert 'manifest.json' in z.namelist(), 'manifest.json 必须在压缩包根目录'

print('index.html + %s (%d files, %.1f MB)' % (zip_path.name, count, zip_path.stat().st_size / 1e6))
