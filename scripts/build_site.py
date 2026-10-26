#!/usr/bin/env python3
"""生成扩展的在线预览页与离线安装包。

- index.html：newtab.html 的同款预览，右下角加「下载扩展」按钮
- naiwa-wallpaper.zip：可加载的扩展本体

用法：python3 scripts/build_site.py
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANNER = """
<a href="naiwa-wallpaper.zip" download style="position:fixed;right:16px;bottom:16px;z-index:99;
display:inline-flex;align-items:center;gap:8px;padding:9px 16px;border-radius:999px;text-decoration:none;
font:500 13px/1.4 'Noto Sans SC',sans-serif;color:#12100c;background:linear-gradient(165deg,#FFD54F,#D9B45B);
box-shadow:0 8px 24px rgba(0,0,0,.45)">⤓ 下载扩展 · 离线安装</a>
"""

newtab = (ROOT / 'newtab.html').read_text(encoding='utf-8')
(ROOT / 'index.html').write_text(newtab.replace('</body>', BANNER + '</body>'), encoding='utf-8')

zip_path = ROOT / 'naiwa-wallpaper.zip'
if zip_path.exists():
    zip_path.unlink()
subprocess.run(
    ['zip', '-qr', zip_path.name, '.',
     '-x', '.git/*', '-x', 'index.html', '-x', '*.zip', '-x', 'scripts/*'],
    check=True, cwd=ROOT,
)
print('index.html +', zip_path.name, zip_path.stat().st_size // 1024, 'KB')
