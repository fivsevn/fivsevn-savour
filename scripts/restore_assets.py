#!/usr/bin/env python3
"""One-time, checksum-pinned migration copy. Never writes to source services."""
import concurrent.futures as cf, hashlib, json, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if (ROOT/'.migration-assets-complete').exists():
    print('Original migration already completed; normal builds do not download assets.')
    raise SystemExit(0)
manifest=json.loads((ROOT/'migration/assets.json').read_text())
def restore(a):
    dest=ROOT/a['path']
    if not dest.resolve().is_relative_to(ROOT):raise ValueError('Invalid destination')
    data=dest.read_bytes() if dest.exists() else urllib.request.urlopen(a['url'],timeout=120).read()
    if hashlib.sha256(data).hexdigest()!=a['sha256']:raise ValueError('Checksum mismatch: '+a['path'])
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(data)
    return a['path']
with cf.ThreadPoolExecutor(max_workers=6) as pool:
    for path in pool.map(restore,manifest):print('Verified',path)
(ROOT/'.migration-assets-complete').write_text('Original assets verified and copied; never fetch missing files during normal builds.\n')
