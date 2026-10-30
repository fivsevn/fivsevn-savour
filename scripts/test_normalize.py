import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import yaml

from normalize_images import normalize
from site_post_metadata import metadata_view, read_frontmatter, validate_metadata


def image_bytes(fmt='PNG', color='red'):
    data = BytesIO()
    Image.new('RGB', (32, 24), color).save(data, format=fmt)
    return data.getvalue()


def sha(data):
    return hashlib.sha256(data).hexdigest()


class NormalizeImagesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'site-data').mkdir()
        self.manifest = []
        self.manifest_path = self.root / 'site-data/originals.json'
        self.save_manifest()

    def save_manifest(self):
        self.manifest_path.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=2) + '\n')

    def add_manifest(self, path, data, role='post'):
        self.manifest.append({'path': path.relative_to(self.root).as_posix(), 'sha256': sha(data),
                              'bytes': len(data), 'role': role})
        self.save_manifest()

    def post(self, suffix='png', number=0, status='published', known=True, data=None):
        ident = f'2026-10-29-1200{number:02d}-test{number}'
        package = self.root / f'savour/2026/10/{ident}'
        photo = package / f'assets/photo.{suffix}'
        photo.parent.mkdir(parents=True)
        data = image_bytes('JPEG' if suffix.lower() in {'jpg', 'jpeg'} else 'PNG') if data is None else data
        photo.write_bytes(data)
        body = '\n\n测试 **正文**。\n\n[主页](https://example.test)\n'
        head = (f'---\nid: {ident}\ndate: \'2026-10-29T12:00:{number:02d}+08:00\'\n'
                f'title: \'手工标题 {number}\'\n# Keep this comment.\nauthor: 五月七日\nstatus: {status}\n'
                f'image: assets/photo.{suffix}\nalt: 自己填写的说明\n---')
        source = package / 'index.md'
        source.write_bytes((head + body).encode())
        if known:
            self.add_manifest(photo, data)
        return source, photo

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file() and not p.is_symlink()}

    def test_converts_saved_and_unpublished_photos_preserving_metadata_and_body(self):
        source, photo = self.post(suffix='JPEG')
        before = source.read_bytes()
        unassigned = self.root / 'unpublished/old.png'
        unassigned.parent.mkdir()
        unassigned.write_bytes(image_bytes('PNG', 'blue'))
        self.add_manifest(unassigned, unassigned.read_bytes(), 'unassigned')
        shared = self.root / 'site-assets/avatar.png'
        shared.parent.mkdir()
        shared_data = image_bytes('PNG', 'green')
        shared.write_bytes(shared_data)
        self.add_manifest(shared, shared_data, 'avatar')
        stats = normalize(self.root)
        self.assertEqual(stats['count'], 2)
        self.assertEqual(stats['photo_count'], 2)
        self.assertFalse(photo.exists())
        self.assertFalse(unassigned.exists())
        for p in [photo.with_suffix('.webp'), unassigned.with_suffix('.webp')]:
            with Image.open(p) as image:
                self.assertEqual(image.format, 'WEBP')
                self.assertEqual(image.size, (32, 24))
        self.assertEqual(shared.read_bytes(), shared_data)
        after = source.read_bytes()
        old_meta,old_body=read_frontmatter(before.decode())
        new_meta,new_body=read_frontmatter(after.decode())
        validate_metadata(new_meta,site='savour')
        view=metadata_view(new_meta)
        for key,value in old_meta.items():
            self.assertEqual(view[key],'assets/photo.webp' if key=='image' else value)
        self.assertEqual(new_body,old_body)
        self.assertNotIn('image',new_meta)
        for item in json.loads(self.manifest_path.read_text()):
            p = self.root / item['path']
            self.assertEqual(item['sha256'], sha(p.read_bytes()))
            self.assertEqual(item['bytes'], p.stat().st_size)
        receipt = json.loads((self.root / '.publishing/webp-conversion.json').read_text())
        self.assertEqual(receipt['count'], 2)
        self.assertEqual(len(receipt['files']), 2)

    def test_idempotent_and_existing_webp_bytes_are_not_reencoded(self):
        source, photo = self.post()
        first = normalize(self.root)
        self.assertEqual(first['count'], 1)
        snapshot = self.snapshot()
        second = normalize(self.root)
        self.assertEqual(second['count'], 0)
        self.assertEqual(second['unchanged_count'], 1)
        self.assertEqual(self.snapshot(), snapshot)
        self.assertTrue(photo.with_suffix('.webp').exists())

    def test_hidden_draft_and_new_manual_packages_are_normalized(self):
        sources = [self.post(number=number, status=status, known=False)
                   for number, status in enumerate(['published', 'hidden', 'draft'])]
        self.assertEqual(normalize(self.root)['count'], 3)
        for status, (source, photo) in zip(['published', 'hidden', 'draft'], sources):
            meta = yaml.safe_load(source.read_text().split('---', 2)[1])
            self.assertEqual(meta['status'], status)
            self.assertEqual(meta['extra']['image'], 'assets/photo.webp')
            self.assertFalse(photo.exists())

    def test_manifest_mismatch_leaves_every_original_and_metadata_untouched(self):
        self.post(number=0)
        _, changed = self.post(number=1)
        changed.write_bytes(image_bytes('PNG', 'blue'))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'checksum manifest'):
            normalize(self.root)
        self.assertEqual(self.snapshot(), before)

    def test_invalid_manual_photo_fails_the_whole_batch(self):
        self.post(number=0)
        self.post(number=1, known=False, data=b'broken image')
        before = self.snapshot()
        with self.assertRaises(ValueError):
            normalize(self.root)
        self.assertEqual(self.snapshot(), before)

    def test_existing_destination_is_not_overwritten(self):
        _, photo = self.post()
        data = BytesIO()
        Image.new('RGB', (10, 10), 'blue').save(data, format='WEBP')
        photo.with_suffix('.webp').write_bytes(data.getvalue())
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            normalize(self.root)
        self.assertEqual(self.snapshot(), before)

    def test_ledger_retains_source_digest_and_records_saved_webp_digest(self):
        _, photo = self.post()
        original = photo.read_bytes()
        (self.root / '.publishing').mkdir()
        state_path = self.root / '.publishing/state.json'
        state = {'version': 1, 'cursor': 'keep-cursor', 'events': {'event': {
            'image_path': photo.relative_to(self.root).as_posix(),
            'sha256': sha(original), 'upload_path': 'trigger_imgs/photo.png',
            'route': 'keep-route', 'id': 'keep-id'}}}
        state_path.write_text(json.dumps(state))
        normalize(self.root)
        updated = json.loads(state_path.read_text())
        event = updated['events']['event']
        self.assertEqual(updated['cursor'], state['cursor'])
        self.assertEqual(event['sha256'], sha(original))
        self.assertEqual(event['file_sha256'], sha(photo.with_suffix('.webp').read_bytes()))
        self.assertEqual(event['image_path'], photo.with_suffix('.webp').relative_to(self.root).as_posix())
        self.assertEqual(event['route'], 'keep-route')
        self.assertEqual(event['id'], 'keep-id')

    def test_failed_metadata_install_rolls_back_files_and_all_metadata(self):
        self.post()
        before = self.snapshot()
        replace = os.replace
        failed = False

        def fail_once(source, target):
            nonlocal failed
            if Path(target).resolve() == self.manifest_path.resolve() and not failed:
                failed = True
                raise OSError('simulated metadata failure')
            return replace(source, target)

        with patch('normalize_images.os.replace', side_effect=fail_once):
            with self.assertRaisesRegex(OSError, 'metadata failure'):
                normalize(self.root)
        self.assertTrue(failed)
        self.assertEqual(self.snapshot(), before)

    def test_symlink_photo_is_rejected_without_following_it(self):
        source, photo = self.post(known=False)
        outside = self.root.parent / (self.root.name + '-outside.png')
        outside.write_bytes(photo.read_bytes())
        self.addCleanup(outside.unlink)
        photo.unlink()
        photo.symlink_to(outside)
        before = source.read_bytes()
        with self.assertRaisesRegex(ValueError, 'symlink'):
            normalize(self.root)
        self.assertEqual(source.read_bytes(), before)
        self.assertTrue(photo.is_symlink())


if __name__ == '__main__':
    unittest.main()
