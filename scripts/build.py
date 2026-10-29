#!/usr/bin/env python3
"""Deterministic static Savour builder. No network access."""
import argparse, hashlib, html, json, re, shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import markdown, yaml
from bs4 import BeautifulSoup
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
E = html.escape

def read_posts(root=ROOT):
    posts=[]; ids=set()
    for source in sorted((root/'savour').glob('*/*/*/index.md')):
        raw=source.read_text()
        if not raw.startswith('---\n'): raise ValueError(f'Missing frontmatter: {source}')
        _,head,body=raw.split('---',2)
        m=yaml.safe_load(head)
        for field in ['id','date','status','image']:
            if field not in m: raise ValueError(f'Missing {field}: {source}')
        if m['id'] in ids: raise ValueError(f'Duplicate ID: {m["id"]}')
        ids.add(m['id'])
        date=datetime.fromisoformat(str(m['date']))
        if date.utcoffset() is None: raise ValueError(f'Date needs timezone: {source}')
        if source.parent.name!=m['id'] or source.parent.parent.name!=date.strftime('%m') or source.parent.parent.parent.name!=date.strftime('%Y'):
            raise ValueError(f'ID/date/package mismatch: {source}')
        if m['status'] not in ['published','hidden','draft']: raise ValueError(f'Unknown status: {source}')
        if m['status']!='published': continue
        image=(source.parent/m['image']).resolve()
        if not image.is_relative_to((source.parent/'assets').resolve()) or not image.is_file(): raise ValueError(f'Missing package image: {source}')
        rendered=markdown.markdown(E(body.strip(),quote=False),extensions=['tables','fenced_code','sane_lists'])
        soup=BeautifulSoup(rendered,'html.parser')
        if soup.find('img'): raise ValueError(f'One photo per post; put the photo in frontmatter: {source}')
        for a in soup.select('a[href]'):
            if urlparse(a['href']).scheme not in ['', 'https','http','mailto']:
                del a['href']
        m.update(source=source,image_path=image,body=body.strip(),body_html=str(soup),datetime=date)
        m['route']=f'page/{source.parent.relative_to(root/"savour").as_posix()}/'
        posts.append(m)
    # Equal-second WordPress records have an observed order that is not always
    # numeric ID order. Retain that order from the immutable migration inventory.
    inventory=root/'migration/inventory.json'
    source_order={p['id']:i for i,p in enumerate(json.loads(inventory.read_text())['posts'])} if inventory.exists() else {}
    return sorted(posts,key=lambda p:(p['datetime'],-source_order.get(p['id'],-1),p['id']),reverse=True)

def build(root=ROOT, output=None, base_path=''):
    output=Path(output or root/'_site')
    if output.resolve()==root.resolve() or root.resolve().is_relative_to(output.resolve()): raise ValueError('Unsafe output path')
    base_path='/' + base_path.strip('/') if base_path.strip('/') else ''
    cfg=json.loads((root/'site.json').read_text()); posts=read_posts(root)
    total=max(1,(len(posts)+cfg['page_size']-1)//cfg['page_size'])
    if output.exists(): shutil.rmtree(output)
    output.mkdir(parents=True)
    shutil.copytree(root/'site-assets',output/'site-assets')
    def url(path=''): return base_path+'/'+path
    def feed(n): return url('' if n==1 else f'feed/{n}/')
    def save(path,content):
        dest=output/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(content)
    random_config=dict(random=cfg['random'],base_path=base_path,total_pages=total)
    def shell(content,title=cfg['title'],detail=False):
        return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#131415"><meta name="description" content="五月七日发来一条消息：下滑开始吃。"><title>{E(title)}</title><link rel="icon" href="{url('site-assets/avatar.png')}"><link rel="preload" href="{url('site-assets/fonts/courier-prime.woff2')}" as="font" type="font/woff2" crossorigin><link rel="stylesheet" href="{url('site-assets/style.css')}"></head><body><main id="top" class="timeline{' detail' if detail else ''}">{content}</main><script id="savour-config" type="application/json">{json.dumps(random_config)}</script><script src="{url('site-assets/site.js')}"></script></body></html>'''
    dots='<div class="dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></div>'
    def status(lock=False):
        left='fivsevn' if lock else '<span class="random-time" data-random="time">00:00</span><span>fivsevn</span>'
        return f'<div class="status" aria-label="模拟手机状态栏"><span class="status-side">{left}</span><span class="status-side">{"No Sats" if lock else "2G"} <span class="status-icon">{"⚡️" if lock else "📡"}</span><span class="battery-value" data-random="battery">0</span><span>%</span></span></div>'
    def header(back,detail=False):
        h='h1' if detail else 'h2'
        return f'<div class="chat-header"><a class="plain-control" href="{back}" aria-label="返回列表" {"data-return" if detail else ""}>←</a><{h}><a href="https://fivsevn.com/">五月七日的思考札记</a></{h}><span aria-hidden="true">⋯</span></div>'
    def msg(content,classes=''):
        return f'<div class="message"><img class="avatar" src="{url("site-assets/avatar.png")}" width="31" height="31" alt="五月七日" loading="lazy"><div class="bubble {classes}">{content}</div></div>'
    def composer(text='｜下滑继续吃。'):
        return f'<div class="composer"><span class="composer-symbol" aria-hidden="true">+</span><span class="composer-input">{text}</span><a class="plain-control composer-symbol composer-up" href="#top" aria-label="回到顶部">↑</a></div>'
    progress='<div class="progress"><span>摄取进度</span><span>eating progress</span><span>[</span><span class="green" aria-hidden="true">▏▎▍▌▋▊▉█</span><span>]</span><span class="green progress-value" data-random="progress">000.0000</span><span class="green">%</span></div>'
    for i,p in enumerate(posts):
        p['list_page']=i//cfg['page_size']+1
        dest=output/p['route'];(dest/'assets').mkdir(parents=True,exist_ok=True)
        shutil.copy2(p['image_path'],dest/'assets'/p['image_path'].name)
        with Image.open(p['image_path']) as im:
            im=ImageOps.exif_transpose(im).convert('RGB');p['width'],p['height']=im.size
            im.thumbnail((1400,1400));im.save(dest/'assets/display.webp','WEBP',quality=88,method=6)
        p['display_image']=p['route']+'assets/display.webp'
        p['original_image']=p['route']+'assets/'+p['image_path'].name
    def phone(p,detail=False):
        return_url=feed(p['list_page'])+'#'+p['id']
        photo=f'<img class="food-photo" src="{url(p["display_image"])}" width="{p["width"]}" height="{p["height"]}" alt="{E(p.get("alt",p.get("title","美食照片")),quote=True)}" loading="lazy" decoding="async">'
        if detail: photo=f'<a href="{url(p["original_image"])}" aria-label="查看原图">{photo}</a>'
        else: photo=f'<a class="photo-link" href="{url(p["route"])}" aria-label="打开 {E(p.get("title",p["id"]),quote=True)}">{photo}</a>'
        messages=msg(photo+progress)
        if detail:
            if p['body']:messages+=msg(p['body_html'],'prose')
            messages+=f'<p class="post-date">{E(p.get("title",str(p["date"])))}</p>'
        else:
            messages+=msg(f'<p>五月七日发来一条链接：</p><div class="link-line"><a class="post-link" href="{url(p["route"])}" title="WordPress 发布日期：{E(str(p["date"]))}">{E(p.get("title",str(p["date"])))}</a><span>.com</span></div>','link-message')
        return f'<article class="phone post-phone" id="{p["id"]}" data-published="{E(str(p["date"]))}">{dots}{status()}{header(return_url if detail else feed(1),detail)}<div class="messages" tabindex="0" role="region" aria-label="聊天消息">{messages}</div>{composer("｜吃到了。" if detail else "｜下滑继续吃。")}</article>'
    def lock(end=False):
        notice=('<div class="notification"><span class="emoji">🐽</span><span>吃饱哩！<a class="home-link" href="https://fivsevn.com/">返回主页</a>。</span></div>' if end else (f'<div class="notification"><span class="emoji">🐷</span><span>五月七日饿了，并发来 <a href="#first-post">1</a> 条信息！</span></div>'*2+'<div class="notification"><span class="emoji">😠</span><span>不饿！<a class="home-link" href="https://fivsevn.com/">返回主页</a>。</span></div>'))
        return f'<section class="phone lock {"end" if end else "start"}" aria-label="{"已吃饱" if end else "下滑开始吃"}锁屏">{dots}{status(True)}<div class="lock-symbol" aria-hidden="true">🔒</div><div class="charged"><span class="battery-value" data-random="battery">0</span><span>% Charged</span></div><div class="lock-clock random-time" data-random="time">00:00</div><div class="lock-space" aria-hidden="true"></div><div class="notifications">{notice}</div><a class="swipe" href="{"#top" if end else "#first-post"}">{"已吃饱" if end else "下滑开始吃<br>↓↓↓"}</a></section>'
    def footer_chat():
        messages=''.join(msg(x) for x in ['<p>五月七日发来一条链接：</p><div class="link-line">[ <a href="https://fivsevn.com/">fivsevn</a> .com ]</div>','噢！等等😈','<p>五月七日分享了一个地址：</p><div class="link-line">[ <a href="https://fivsevn.com/57store">五月七日便利店</a> ]</div>','帮我带罐啤酒🍺','还要一个小饭团🍙！！'])
        return f'<section class="phone footer-message" aria-label="五月七日的留言">{dots}{status()}{header(feed(1))}<div class="messages" tabindex="0" role="region" aria-label="聊天消息">{messages}</div>{composer("｜啤酒卖完了。")}</section>'
    def pagination(n):
        links=[]
        if n>1:links.append(f'<a href="{feed(n-1)}" rel="prev" aria-label="上一页">←</a>')
        shown=sorted({1,total,*range(max(1,n-2),min(total,n+2)+1)})
        for j,x in enumerate(shown):
            if j and x-shown[j-1]>1:links.append('<span aria-hidden="true">…</span>')
            links.append(f'<span aria-current="page">{x}</span>' if x==n else f'<a href="{feed(x)}" aria-label="第 {x} 页">{x}</a>')
        if n<total:links.append(f'<a href="{feed(n+1)}" rel="next" aria-label="下一页">→</a>')
        return '<nav class="pagination" aria-label="分页">'+''.join(links)+'</nav>'
    for n in range(1,total+1):
        content=lock()+'<div id="first-post"></div>'+''.join(phone(p) for p in posts[(n-1)*cfg['page_size']:n*cfg['page_size']])+pagination(n)+footer_chat()+lock(True)
        save('index.html' if n==1 else f'feed/{n}/index.html',shell(content))
    for p in posts:
        save(p['route']+'index.html',shell(phone(p,True),p.get('title',p['id'])+' · '+cfg['title'],True))
    def redirect(path,target):
        save(path.rstrip('/')+'/index.html',f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={E(target)}"><title>前往 Savour</title><a href="{E(target)}">前往这则美食分享</a></html>')
    for p in posts:
        if p.get('archive_url'): redirect(urlparse(p['archive_url']).path.strip('/'),url(p['route']))
    save('foodie/index.html',shell('<p class="broken-page"><a href="'+feed(1)+'">下滑开始吃 →</a></p>') .replace('</body>','<script>if(!location.search)location.replace('+json.dumps(feed(1))+');</script></body>'))
    save('404.html',shell('<div class="broken-page">这条消息还没找到。<p><a href="'+feed(1)+'">返回 Savour 继续吃 →</a></p></div>'))
    save('.nojekyll','')
    receipt=dict(posts=len(posts),pages=total,base_path=base_path,ids=[p['id'] for p in posts],files={})
    for f in sorted(output.rglob('*')):
        if f.is_file(): receipt['files'][f.relative_to(output).as_posix()]=hashlib.sha256(f.read_bytes()).hexdigest()
    save('build-receipt.json',json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(f'Built {len(posts)} posts / {total} pages → {output}')
    return receipt

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base-path',default='');parser.add_argument('--output',type=Path)
    args=parser.parse_args();build(output=args.output,base_path=args.base_path)
