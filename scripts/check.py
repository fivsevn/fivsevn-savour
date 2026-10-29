#!/usr/bin/env python3
"""Check source integrity and all generated internal references."""
import argparse,hashlib,json
from pathlib import Path
from urllib.parse import urlparse,unquote
from bs4 import BeautifulSoup
from build import ROOT,read_posts

def check(output,base_path):
    posts=read_posts()
    inventory=json.loads((ROOT/'migration/inventory.json').read_text())
    manifests=json.loads((ROOT/'migration/assets.json').read_text())
    missing=[]
    for a in manifests:
        f=ROOT/a['path']
        # Removal/hiding is supported after migration, but shared assets stay required.
        if not f.exists():
            if a['role']=='post' and not (f.parent.parent/'index.md').exists(): continue
            missing.append(a['path']);continue
        if hashlib.sha256(f.read_bytes()).hexdigest()!=a['sha256']:
            raise AssertionError('Original asset changed: '+a['path'])
    assert not missing,missing
    errors=[];html_count=0
    for f in output.rglob('*.html'):
        html_count+=1;soup=BeautifulSoup(f.read_text(),'html.parser')
        assert not soup.select('[rel="tag"]'),f'Tags rendered: {f}'
        for e in soup.select('[src], [href]'):
            value=e.get('src',e.get('href','')); u=urlparse(value)
            if u.scheme or u.netloc:
                if e.has_attr('src') or e.name=='link' and e.get('rel')==['stylesheet']:errors.append(f'External runtime asset: {value}')
                continue
            if not u.path:
                if u.fragment and not soup.find(id=unquote(u.fragment)):errors.append(f'Missing anchor: {f} {value}')
                continue
            if u.path.startswith('/'):
                if base_path and not u.path.startswith(base_path+'/'):errors.append(f'Base path lost: {f} {value}');continue
                dest=output/unquote(u.path[len(base_path):].lstrip('/'))
            else:dest=f.parent/unquote(u.path)
            if dest.is_dir(): dest=dest/'index.html'
            if not dest.exists():errors.append(f'Broken internal link: {f} {value}')
        if 'post-phone' in f.read_text() and '/page/' in f.as_posix():
            assert len(soup.select('.post-phone'))==1,f
            assert len(soup.select('.food-photo'))==1,f
    assert not errors,'\n'.join(errors)
    print(json.dumps(dict(published_posts=len(posts),audited_old_posts=len(inventory['posts']),verified_assets=len(manifests),html_pages=html_count,broken_links=0,external_runtime_assets=0),ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'_site');p.add_argument('--base-path',default='');a=p.parse_args();check(a.output,a.base_path.rstrip('/'))
