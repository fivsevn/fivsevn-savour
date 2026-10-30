import copy,importlib.util,json,tempfile,unittest
from pathlib import Path
import yaml
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
