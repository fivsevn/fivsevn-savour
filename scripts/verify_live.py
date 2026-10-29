#!/usr/bin/env python3
"""Verify deployed bytes before marking a build or clearing its upload inbox."""
import argparse
import concurrent.futures
import hashlib
import json
import ssl
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url):
    for attempt in range(6):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'Savour-deployment-check'}), timeout=60,
                         context=ssl.create_default_context()) as response:
                return response.read()
        except OSError:
            if attempt == 5:
                raise
            time.sleep(5)


def verify(root=ROOT, base_url='https://savour.fivsevn.com', read=fetch, attempts=6, pause=time.sleep):
    root = Path(root)
    site = root / '_site'
    (site / '.verified.json').unlink(missing_ok=True)
    receipt_bytes = (site / 'build-receipt.json').read_bytes()
    receipt = json.loads(receipt_bytes)
    fingerprint = digest(receipt_bytes)
    base_url = base_url.rstrip('/')
    for attempt in range(attempts):
        public_receipt = json.loads(read(base_url + '/build-receipt.json?v=' + fingerprint[:12]))
        if public_receipt == receipt:
            break
        if attempt == attempts - 1:
            raise ValueError('The public deployment still differs from this build; inbox retained. Retry the workflow.')
        pause(5)
    marker = root / '.publishing/deployed.json'
    previous = json.loads(marker.read_text()) if marker.exists() else {}
    previous_files = previous.get('files', {}) if previous.get('url') == base_url else {}
    files = receipt['files']
    required = {path for path, sha in files.items() if previous_files.get(path) != sha}
    required.add('index.html')
    if receipt['pages'] > 1:
        required.add(f'feed/{receipt["pages"]}/index.html')
    # Existing package originals must also remain available before inbox cleanup.
    state_path = root / '.publishing/state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {'events': {}}
    for event in state['events'].values():
        image = root / event['image_path']
        if not image.exists() or not (root / event['upload_path']).is_file():
            continue
        for path in [event['route'] + 'index.html', event['route'] + 'assets/' + image.name]:
            if path in files:
                required.add(path)
    required.discard('.nojekyll')

    def check(path):
        if Path(path).is_absolute() or '..' in Path(path).parts:
            raise ValueError('Unsafe receipt path: ' + path)
        if digest((site / path).read_bytes()) != files[path]:
            raise ValueError('Local artifact changed: ' + path)
        for attempt in range(attempts):
            data = read(base_url + '/' + quote(path, safe='/') + '?v=' + fingerprint[:12])
            if digest(data) == files[path]:
                break
            if attempt == attempts - 1:
                raise ValueError('Public bytes differ: ' + path)
            pause(5)
        return path

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        verified = list(pool.map(check, sorted(required)))
    deployed = {'url': base_url, 'receipt_sha256': fingerprint, 'files': files}
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps(deployed, ensure_ascii=False, indent=2) + '\n')
    (site / '.verified.json').write_text(json.dumps({'receipt_sha256': fingerprint}) + '\n')
    print(f'Verified {len(verified)} public files; build {fingerprint[:12]}.')
    return deployed


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://savour.fivsevn.com')
    args = parser.parse_args()
    verify(base_url=args.url)
