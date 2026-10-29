#!/usr/bin/env python3
"""Each input image becomes a separate editable post package."""
import argparse,hashlib,shutil
from pathlib import Path
from datetime import datetime
import yaml
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('images',type=Path,nargs='+');p.add_argument('--date',required=True,help='ISO 8601 with timezone');p.add_argument('--text-file',type=Path);p.add_argument('--status',choices=['published','hidden','draft'],default='published');a=p.parse_args()
date=datetime.fromisoformat(a.date)
if date.utcoffset() is None:p.error('--date requires a timezone, e.g. +08:00')
text=a.text_file.read_text() if a.text_file else ''
for source in a.images:
    with Image.open(source) as im:im.verify()
    id=f'{date:%Y-%m-%d-%H%M%S}-{hashlib.sha256(source.read_bytes()).hexdigest()[:12]}'
    package=ROOT/f'savour/{date:%Y/%m}/{id}'
    if package.exists():raise SystemExit(f'Package already exists (not overwritten): {package}')
    (package/'assets').mkdir(parents=True)
    name='photo'+source.suffix.lower();shutil.copy2(source,package/'assets'/name)
    meta=dict(id=id,date=a.date,title=date.strftime('%d %b, %Y %H:%M'),author='五月七日',status=a.status,image='assets/'+name,alt='五月七日分享的美食')
    (package/'index.md').write_text('---\n'+yaml.safe_dump(meta,allow_unicode=True,sort_keys=False)+'---\n\n'+text.strip()+'\n')
    print(package.relative_to(ROOT))
