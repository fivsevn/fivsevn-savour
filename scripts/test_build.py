import copy,importlib.util,json,tempfile,unittest
from pathlib import Path
import yaml
from build import ROOT,read_posts

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
    def test_body_edit_preserves_route(self):
        self.write('one');a=read_posts(self.root)[0]['route'];self.write('two');self.assertEqual(a,read_posts(self.root)[0]['route'])
    def test_migration_accounting(self):
        data=json.loads((ROOT/'migration/inventory.json').read_text())
        self.assertEqual(data['total_pages'],12);self.assertEqual(data['page_counts'],[11]*11+[4,0]);self.assertEqual(len(data['posts']),125)
        self.assertTrue(all(len(p['images'])==len(p['detail_images'])==1 and not any(p['detail_text']) for p in data['posts']))

if __name__=='__main__':unittest.main()
