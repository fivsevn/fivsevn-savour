import copy,importlib.util,json,tempfile,unittest
from pathlib import Path
import yaml
import xml.etree.ElementTree as ET
from PIL import Image
from build import ROOT,read_posts,build
from site_post_metadata import dump_frontmatter, normalize_metadata, read_frontmatter

class ContentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.meta=dict(id='2026-10-29-120000-test',date='2026-10-29T12:00:00+08:00',status='published',image='assets/a.jpg')
        self.package=self.root/'savour/2026/10'/self.meta['id'];(self.package/'assets').mkdir(parents=True)
        (self.package/'assets/a.jpg').write_bytes(b'test')
    def tearDown(self):self.tmp.cleanup()
    def write(self,body=''):
        meta=normalize_metadata(self.meta,site='savour')
        (self.package/'index.md').write_text(dump_frontmatter(meta)+'\n'+body)
    def test_markdown_and_links(self):
        self.write('**晚饭**\n\n[主页](https://fivsevn.com/)');p=read_posts(self.root)[0]
        self.assertIn('<strong>晚饭</strong>',p['body_html']);self.assertIn('href="https://fivsevn.com/"',p['body_html'])
    def test_empty_caption(self):self.write();self.assertEqual(read_posts(self.root)[0]['body_html'],'')
    def test_hidden(self):self.meta['status']='hidden';self.write();self.assertEqual(read_posts(self.root),[])
    def test_missing_photo(self):self.write();(self.package/'assets/a.jpg').unlink();self.assertRaises(ValueError,read_posts,self.root)
    def test_additional_photo_rejected(self):self.write('![extra](second.jpg)');self.assertRaises(ValueError,read_posts,self.root)
    def test_timezone_required(self):
        self.write()
        source=self.package/'index.md';meta,body=read_frontmatter(source)
        meta['extra']['published_at']='2026-10-29T12:00:00'
        source.write_text(dump_frontmatter(meta)+body)
        self.assertRaises(ValueError,read_posts,self.root)
    def test_profile_is_validated_before_rendering(self):
        self.write()
        source=self.package/'index.md';meta,body=read_frontmatter(source)
        del meta['extra']['image']
        source.write_text(dump_frontmatter(meta)+body)
        self.assertRaises(ValueError,read_posts,self.root)
    def test_public_active_statuses_count_only_real_posts_in_eleven_post_pages(self):
        (self.root/'site-assets').mkdir()
        for name in ['style.css','site.js']:(self.root/'site-assets'/name).write_text('')
        (self.root/'site.json').write_text(json.dumps({'title':'test','page_size':11,'random':{}}))
        for i in range(15):
            ident=f'2026-10-29-1200{i:02d}-post'
            package=self.root/'savour/2026/10'/ident;(package/'assets').mkdir(parents=True)
            Image.new('RGB',(20,20),'red').save(package/'assets/photo.webp','WEBP')
            meta=normalize_metadata(dict(id=ident,date=f'2026-10-29T12:00:{i:02d}+08:00',
                  title=f'Post {i}',status=['active','publish','published'][i%3],image='assets/photo.webp'),site='savour')
            if i==13:meta['status']='draft'
            if i==14:meta['visibility']='private'
            (package/'index.md').write_text(dump_frontmatter(meta))
        receipt=build(root=self.root)
        self.assertEqual(receipt['posts'],13);self.assertEqual(receipt['pages'],2)
        for route,count in [('index.html',11),('feed/2/index.html',2)]:
            from bs4 import BeautifulSoup
            soup=BeautifulSoup((self.root/'_site'/route).read_text(),'html.parser')
            self.assertEqual(len(soup.select('.post-phone')),count)
            self.assertEqual(len(soup.select('.lock')),2)
            self.assertEqual(len(soup.select('.footer-message')),1)
    def test_iphone_multiframe_photo_still_gets_a_webp_display(self):
        Image.new('RGB',(20,20),'red').save(self.package/'assets/a.jpg',format='MPO',save_all=True,append_images=[Image.new('RGB',(20,20),'blue')])
        self.write()
        (self.root/'site-assets').mkdir()
        for name in ['style.css','site.js']:(self.root/'site-assets'/name).write_text('')
        (self.root/'site.json').write_text(json.dumps({'title':'test','page_size':11,'random':{}}))
        output=self.root/'output'
        build(root=self.root,output=output)
        route=read_posts(self.root)[0]['route']
        self.assertTrue((output/route/'assets/display.webp').is_file())
    def test_search_metadata_and_discovery_use_public_canonical_routes(self):
        from bs4 import BeautifulSoup
        self.meta.update(title='晚饭 & "朋友"',image='assets/a.webp')
        Image.new('RGB',(20,20),'red').save(self.package/'assets/a.webp','WEBP')
        (self.package/'assets/a.jpg').unlink()
        self.write('原有配文')
        for i in range(13):
            ident=f'2026-10-29-1300{i:02d}-post'
            package=self.root/'savour/2026/10'/ident;(package/'assets').mkdir(parents=True)
            Image.new('RGB',(20,20),'blue').save(package/'assets/photo.webp','WEBP')
            meta=normalize_metadata(dict(id=ident,date=f'2026-10-29T13:00:{i:02d}+08:00',
                  title=f'Post {i}',status='hidden' if i==12 else 'published',image='assets/photo.webp'),site='savour')
            (package/'index.md').write_text(dump_frontmatter(meta))
        (self.root/'site-assets').mkdir()
        for name in ['style.css','site.js']:(self.root/'site-assets'/name).write_text('')
        (self.root/'site.json').write_text(json.dumps({'title':'test','page_size':11,'random':{}}))
        (self.root/'site-data').mkdir()
        (self.root/'site-data/history.json').write_text(json.dumps({'order':[],'aliases':{'old-note':self.meta['id']}}))
        (self.root/'CNAME').write_text('food.example\n')
        output=self.root/'output';build(root=self.root,output=output,base_path='/preview')
        route=next(p for p in read_posts(self.root) if p['id']==self.meta['id'])['route']
        origin='https://food.example'
        for path,canonical,kind in [('index.html',origin+'/', 'website'),('feed/2/index.html',origin+'/feed/2/','website'),
                                    (route+'index.html',origin+'/'+route,'article'),('old-note/index.html',origin+'/'+route,'website')]:
            soup=BeautifulSoup((output/path).read_text(),'html.parser')
            self.assertEqual(canonical,soup.select_one('link[rel=canonical]')['href'])
            self.assertEqual(canonical,soup.select_one('meta[property="og:url"]')['content'])
            self.assertEqual(kind,soup.select_one('meta[property="og:type"]')['content'])
            self.assertEqual(soup.title.string,soup.select_one('meta[property="og:title"]')['content'])
            self.assertEqual('summary',soup.select_one('meta[name="twitter:card"]')['content'])
            self.assertEqual('五月七日发来一条消息：下滑开始吃。',soup.select_one('meta[name=description]')['content'])
        soup=BeautifulSoup((output/route/'index.html').read_text(),'html.parser')
        self.assertEqual(origin+'/'+route+'assets/a.webp',soup.select_one('meta[property="og:image"]')['content'])
        self.assertEqual('food.example\n',(output/'CNAME').read_text())
        sitemap=ET.parse(output/'sitemap.xml');locations=[node.text for node in sitemap.findall('.//{*}loc')]
        self.assertEqual(15,len(locations))
        self.assertIn(origin+'/feed/2/',locations)
        self.assertIn(origin+'/'+route,locations)
        self.assertFalse(any('old-note' in location or '404.html' in location or 'foodie' in location or ident in location for location in locations))
        self.assertEqual([],sitemap.findall('.//{*}lastmod'))
        self.assertIn('Sitemap: '+origin+'/sitemap.xml',(output/'robots.txt').read_text())
    def test_archived_webp_is_served_without_another_lossy_copy(self):
        self.meta['image']='assets/a.webp'
        Image.new('RGB',(20,20),'red').save(self.package/'assets/a.webp','WEBP',quality=85)
        original=(self.package/'assets/a.webp').read_bytes()
        self.write()
        (self.root/'site-assets').mkdir()
        for name in ['style.css','site.js']:(self.root/'site-assets'/name).write_text('')
        (self.root/'site.json').write_text(json.dumps({'title':'test','page_size':11,'random':{}}))
        output=self.root/'output'
        build(root=self.root,output=output)
        route=read_posts(self.root)[0]['route']
        self.assertEqual((output/route/'assets/a.webp').read_bytes(),original)
        self.assertFalse((output/route/'assets/display.webp').exists())
        self.assertIn(route+'assets/a.webp',(output/'index.html').read_text())
    def test_large_webp_keeps_archive_and_builds_smaller_display(self):
        self.meta['image']='assets/display.webp'
        Image.new('RGB',(1600,900),'red').save(self.package/'assets/display.webp','WEBP',quality=85)
        original=(self.package/'assets/display.webp').read_bytes()
        self.write()
        (self.root/'site-assets').mkdir()
        for name in ['style.css','site.js']:(self.root/'site-assets'/name).write_text('')
        (self.root/'site.json').write_text(json.dumps({'title':'test','page_size':11,'random':{}}))
        output=self.root/'output'
        build(root=self.root,output=output)
        route=read_posts(self.root)[0]['route']
        self.assertEqual((output/route/'assets/display.webp').read_bytes(),original)
        with Image.open(output/route/'assets/display-preview.webp') as image:self.assertEqual(image.width,1400)
    def test_transparent_webp_display_does_not_get_an_opaque_background(self):
        self.meta['image']='assets/a.webp'
        photo=Image.new('RGBA',(1600,800),(25,50,75,0))
        photo.paste((255,0,0,255),(400,200,1200,600))
        photo.save(self.package/'assets/a.webp','WEBP',lossless=True,exact=True)
        self.write()
        (self.root/'site-assets').mkdir()
        for name in ['style.css','site.js']:(self.root/'site-assets'/name).write_text('')
        (self.root/'site.json').write_text(json.dumps({'title':'test','page_size':11,'random':{}}))
        output=self.root/'output';build(root=self.root,output=output)
        route=read_posts(self.root)[0]['route']
        with Image.open(output/route/'assets/display.webp') as image:
            self.assertEqual(image.size,(1400,700))
            self.assertEqual(image.convert('RGBA').getpixel((0,0))[3],0)
            self.assertEqual(image.convert('RGBA').getpixel((700,350)),(255,0,0,255))
    def test_body_edit_preserves_route(self):
        self.write('one');a=read_posts(self.root)[0]['route'];self.write('two');self.assertEqual(a,read_posts(self.root)[0]['route'])
    def test_historical_order_and_local_assets(self):
        history=json.loads((ROOT/'site-data/history.json').read_text())
        self.assertEqual(len(history['order']),125)
        posts=read_posts()
        expected=[ident for ident in history['order'] if any(p['id']==ident for p in posts)]
        self.assertEqual([p['id'] for p in posts if p['id'] in history['order']],expected)
        self.assertTrue(all('date' in p and 'image' in p for p in posts))
        self.assertTrue(all(p['image_path'].is_relative_to(ROOT/'savour') for p in posts))

if __name__=='__main__':unittest.main()
