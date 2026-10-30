#!/usr/bin/env python3
"""Each input image becomes a separate editable post package."""
import argparse,hashlib
from pathlib import Path
from datetime import datetime
from image_codec import convert_image
from site_post_metadata import dump_frontmatter, normalize_metadata, validate_metadata
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('images',type=Path,nargs='+');p.add_argument('--date',required=True,help='ISO 8601 with timezone');p.add_argument('--text-file',type=Path);p.add_argument('--status',choices=['published','hidden','draft'],default='published');a=p.parse_args()
date=datetime.fromisoformat(a.date)
if date.utcoffset() is None:p.error('--date requires a timezone, e.g. +08:00')
text=a.text_file.read_text() if a.text_file else ''
for source in a.images:
    converted=convert_image(source.read_bytes(),source.name)
    id=f'{date:%Y-%m-%d-%H%M%S}-{hashlib.sha256(source.read_bytes()).hexdigest()[:12]}'
    package=ROOT/f'savour/{date:%Y/%m}/{id}'
    if package.exists():raise SystemExit(f'Package already exists (not overwritten): {package}')
    (package/'assets').mkdir(parents=True)
    name='photo.webp';(package/'assets'/name).write_bytes(converted)
    meta=dict(id=id,date=a.date,title=date.strftime('%d %b, %Y %H:%M'),author='五月七日',status=a.status,image='assets/'+name,alt='五月七日分享的美食')
    meta=normalize_metadata(meta,site='savour')
    validate_metadata(meta,site='savour',schema_dir=ROOT/'schemas')
    (package/'index.md').write_text(dump_frontmatter(meta)+'\n'+text.strip()+'\n')
    print(package.relative_to(ROOT))
