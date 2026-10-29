import copy,importlib.util,json,tempfile,unittest
from pathlib import Path
import yaml
from PIL import Image
from build import ROOT,read_posts,build

class ContentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.meta=dict(id='2026-10-29-120000-test',date='2026-10-29T12:00:00+08:00',status='published',image='assets/a.jpg')
        self.package=self.root/'savour/2026/10'/self.meta['id'];(self.package/'assets').mkdir(parents=True)
        (self.package/'assets/a.jpg').write_bytes(b'test')
    def tearDown(self):self.tmp.cleanup()
    def write(self,body=''):(self.package/'index.md').write_text('---\n'+yaml.safe_dump(self.meta)+'---\n'+body)
    def test_markdown_and_links(self):
        self.write('**晚饭**\n\n[主页](https://fivsevn.com/)');p=read_posts(self.root)[0]
        self.assertIn('<strong>晚饭</strong>',p['body_html']);self.assertIn('href="https://fivsevn.com/"',p['body_html'])
    def test_empty_caption(self):self.write();self.assertEqual(read_posts(self.root)[0]['body_html'],'')
    def test_hidden(self):self.meta['status']='hidden';self.write();self.assertEqual(read_posts(self.root),[])
    def test_missing_photo(self):self.write();(self.package/'assets/a.jpg').unlink();self.assertRaises(ValueError,read_posts,self.root)
    def test_additional_photo_rejected(self):self.write('![extra](second.jpg)');self.assertRaises(ValueError,read_posts,self.root)
    def test_timezone_required(self):self.meta['date']='2026-10-29T12:00:00';self.write();self.assertRaises(ValueError,read_posts,self.root)
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
    def test_body_edit_preserves_route(self):
        self.write('one');a=read_posts(self.root)[0]['route'];self.write('two');self.assertEqual(a,read_posts(self.root)[0]['route'])
    def test_historical_order_and_local_assets(self):
        history=json.loads((ROOT/'site-data/history.json').read_text())
        self.assertEqual(len(history['order']),125)
        posts=read_posts()
        expected=[ident for ident in history['order'] if any(p['id']==ident for p in posts)]
        self.assertEqual([p['id'] for p in posts if p['id'] in history['order']],expected)
        self.assertTrue(all('archive_url' not in p and 'legacy' not in p for p in posts))
        self.assertTrue(all(p['image_path'].is_relative_to(ROOT/'savour') for p in posts))

if __name__=='__main__':unittest.main()
