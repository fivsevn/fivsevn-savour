#!/usr/bin/env python3
"""Normalize saved photo packages to WebP without changing post identities.

All inputs, metadata and converted files are validated before installation.
Original files remain in a transaction backup until every replacement succeeds.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile

from PIL import Image
from image_codec import convert_image
from site_post_metadata import (dump_frontmatter, metadata_view, normalize_metadata,
                                read_frontmatter, validate_metadata)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'site-data/originals.json'
STATE = '.publishing/state.json'
RECEIPT = '.publishing/webp-conversion.json'
FRONTMATTER = re.compile(r'\A---\r?\n(.*?)\r?\n---(?=\r?\n|\Z)', re.S)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def safe(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or '\x00' in value:
        raise ValueError('Invalid photo path')
    relative = PurePosixPath(value)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Unsafe photo path: ' + value)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Photo path follows a symlink: ' + value)
    if not current.resolve().is_relative_to(root):
        raise ValueError('Photo path leaves the repository: ' + value)
    return current


def parse_post(data: bytes, source: Path) -> tuple[str, re.Match, dict]:
    text = data.decode('utf-8')
    match = FRONTMATTER.match(text)
    if not match:
        raise ValueError('Missing post frontmatter: ' + str(source))
    raw, _ = read_frontmatter(text)
    meta = metadata_view(raw)
    if not isinstance(meta.get('image'), str):
        raise ValueError('Missing post image: ' + str(source))
    return text, match, meta


def replace_image(data: bytes, source: Path, image: str) -> bytes:
    text, match, _ = parse_post(data, source)
    raw, _ = read_frontmatter(text)
    meta = normalize_metadata(raw, site='savour', post_id=source.parent.name)
    meta['extra']['image'] = image
    validate_metadata(meta, site='savour', schema_dir=ROOT / 'schemas')
    return (dump_frontmatter(meta).rstrip('\n') + text[match.end():]).encode('utf-8')


def normalize(root: Path = ROOT, workers: int = 4) -> dict:
    root = Path(root).resolve()
    manifest_path = safe(root, MANIFEST)
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, list):
        raise ValueError('Invalid saved-image manifest')
    jobs: dict[str, dict] = {}
    posts: list[dict] = []

    def add_image(path: Path) -> None:
        name = path.relative_to(root).as_posix()
        checked = safe(root, name)
        if not checked.is_file():
            raise ValueError('Saved photo is missing: ' + name)
        jobs.setdefault(name, {'path': name, 'source': checked,
                              'source_sha256': file_digest(checked), 'before_bytes': checked.stat().st_size})

    # Include hidden and draft packages as well as published posts.
    for source in sorted((root / 'savour').rglob('index.md')):
        source = safe(root, source.relative_to(root).as_posix())
        data = source.read_bytes()
        _, _, meta = parse_post(data, source)
        image_name = PurePosixPath(meta['image'])
        if image_name.is_absolute() or '..' in image_name.parts or image_name.parts[:1] != ('assets',):
            raise ValueError('Post image must stay inside its own assets folder: ' + str(source))
        image = safe(root, (source.parent.relative_to(root) / Path(*image_name.parts)).as_posix())
        if not image.resolve().is_relative_to((source.parent / 'assets').resolve()):
            raise ValueError('Post image escapes its package: ' + str(source))
        add_image(image)
        posts.append({'source': source, 'bytes': data, 'image': image.relative_to(root).as_posix()})

    # Check every known old photo before starting any conversion. Known images
    # no longer selected by a post are also normalized instead of left as raw copies.
    seen = set()
    for item in manifest:
        if not isinstance(item, dict) or not isinstance(item.get('path'), str):
            raise ValueError('Invalid saved-image manifest entry')
        if item['path'] in seen:
            raise ValueError('Duplicate saved-image manifest path: ' + item['path'])
        seen.add(item['path'])
        if item.get('role') not in {'post', 'unassigned'}:
            continue
        path = safe(root, item['path'])
        if not path.exists() and item.get('role') == 'post' and not (path.parent.parent / 'index.md').exists():
            continue  # A deliberately deleted post need not be restored.
        if (not path.is_file() or file_digest(path) != item.get('sha256')
                or path.stat().st_size != item.get('bytes')):
            raise ValueError('Saved photo differs from its checksum manifest: ' + item['path'])
        add_image(path)

    state_path = safe(root, STATE)
    state_bytes = state_path.read_bytes() if state_path.exists() else None
    state = json.loads(state_bytes) if state_bytes is not None else None
    if state is not None and (not isinstance(state, dict) or not isinstance(state.get('events'), dict)):
        raise ValueError('Invalid publishing state')

    with tempfile.TemporaryDirectory(prefix='.savour-normalize-', dir=root) as temporary:
        staging = Path(temporary)

        def prepare(pair):
            number, item = pair
            data = item['source'].read_bytes()
            if digest(data) != item['source_sha256']:
                raise ValueError('Saved photo changed during conversion: ' + item['path'])
            converted = convert_image(data, item['path'])
            with Image.open(BytesIO(converted)) as image:
                if image.format != 'WEBP':
                    raise ValueError('Photo conversion did not produce WebP: ' + item['path'])
            # Already-valid WebP files keep their bytes and spelling unchanged.
            destination = item['source'] if item['source'].suffix.lower() == '.webp' else item['source'].with_suffix('.webp')
            target_name = destination.relative_to(root).as_posix()
            safe(root, target_name)
            changed = destination != item['source'] or converted != data
            output = staging / f'photo-{number}.webp'
            if changed:
                output.write_bytes(converted)
            return dict(item, target=destination, target_path=target_name, file_sha256=digest(converted),
                        after_bytes=len(converted), changed=changed, output=output)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(workers, 4))) as pool:
            prepared = list(pool.map(prepare, enumerate(jobs.values())))
        changed = sorted((item for item in prepared if item['changed']), key=lambda item: item['path'])
        stats = {'count': len(changed), 'before_bytes': sum(item['before_bytes'] for item in changed),
                 'after_bytes': sum(item['after_bytes'] for item in changed), 'photo_count': len(prepared),
                 'unchanged_count': len(prepared) - len(changed),
                 'total_before_bytes': sum(item['before_bytes'] for item in prepared),
                 'total_after_bytes': sum(item['after_bytes'] for item in prepared)}
        if not changed:
            return stats
        targets = set()
        for item in changed:
            if item['target_path'] in targets:
                raise ValueError('Two saved photos map to the same WebP: ' + item['target_path'])
            targets.add(item['target_path'])
            if item['target'] != item['source'] and item['target'].exists():
                raise ValueError('Refusing to overwrite an existing WebP: ' + item['target_path'])
        mapping = {item['path']: item for item in changed}
        updated_manifest = copy.deepcopy(manifest)
        for item in updated_manifest:
            converted = mapping.get(item['path'])
            if converted:
                item.update(path=converted['target_path'], sha256=converted['file_sha256'], bytes=converted['after_bytes'])

        metadata: dict[Path, tuple[bytes | None, bytes]] = {}
        for post in posts:
            converted = mapping.get(post['image'])
            if converted and converted['path'] != converted['target_path']:
                image = converted['target'].relative_to(post['source'].parent).as_posix()
                metadata[post['source']] = (post['bytes'], replace_image(post['bytes'], post['source'], image))
        manifest_after = (json.dumps(updated_manifest, ensure_ascii=False, indent=2) + '\n').encode()
        if manifest_after != manifest_bytes:
            metadata[manifest_path] = (manifest_bytes, manifest_after)
        if state is not None:
            updated_state = copy.deepcopy(state)
            for event in updated_state['events'].values():
                converted = mapping.get(event.get('image_path'))
                if converted:
                    event.update(image_path=converted['target_path'], file_sha256=converted['file_sha256'])
            if updated_state != state:
                metadata[state_path] = (state_bytes, (json.dumps(updated_state, ensure_ascii=False, indent=2) + '\n').encode())
        receipt_path = safe(root, RECEIPT)
        receipt_before = receipt_path.read_bytes() if receipt_path.exists() else None
        receipt = {'version': 1, **stats, 'files': [
            {key: item[key] for key in ['path', 'target_path', 'source_sha256', 'file_sha256', 'before_bytes', 'after_bytes']}
            for item in changed]}
        metadata[receipt_path] = (receipt_before, (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode())

        # Refuse concurrent local edits before the transactional install starts.
        for item in prepared:
            safe(root, item['path'])
            safe(root, item['target_path'])
            if file_digest(item['source']) != item['source_sha256']:
                raise ValueError('Saved photo changed during conversion: ' + item['path'])
        for path, (before, _) in metadata.items():
            safe(root, path.relative_to(root).as_posix())
            if (path.read_bytes() if path.exists() else None) != before:
                raise ValueError('Metadata changed during conversion: ' + str(path))
        for item in changed:
            if item['target'] != item['source'] and item['target'].exists():
                raise ValueError('WebP destination changed during conversion: ' + item['target_path'])

        installed_photos = []
        installed_metadata = []
        created_parents = []
        try:
            for number, item in enumerate(changed):
                backup = staging / f'original-{number}'
                os.replace(item['source'], backup)
                installed_photos.append((item['source'], item['target'], backup))
                os.replace(item['output'], item['target'])
            for number, (path, (before, after)) in enumerate(metadata.items()):
                absent = []
                parent = path.parent
                while parent != root and not parent.exists():
                    absent.append(parent)
                    parent = parent.parent
                path.parent.mkdir(parents=True, exist_ok=True)
                created_parents.extend(reversed(absent))
                pending = staging / f'metadata-{number}'
                pending.write_bytes(after)
                backup = staging / f'metadata-old-{number}' if before is not None else None
                if backup is not None:
                    os.replace(path, backup)
                installed_metadata.append((path, backup))
                os.replace(pending, path)
        except BaseException:
            for path, backup in reversed(installed_metadata):
                path.unlink(missing_ok=True)
                if backup is not None:
                    os.replace(backup, path)
            for source, target, backup in reversed(installed_photos):
                target.unlink(missing_ok=True)
                os.replace(backup, source)
            for parent in reversed(created_parents):
                if parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
            raise
    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(normalize(args.root), ensure_ascii=False))
