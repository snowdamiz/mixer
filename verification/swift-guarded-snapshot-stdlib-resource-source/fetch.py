"""Read exact official Rust platform source; no installed toolchain mutation."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

D = Path(__file__).resolve().parent
REVISION = 'b940084d7eb6a299eb4bfeb8e34901bc051e7ac4'
FILES = ['LICENSE-MIT', 'LICENSE-APACHE', 'library/alloc/src/sync.rs',
         'library/alloc/src/boxed.rs', 'library/alloc/src/vec/mod.rs',
         'library/alloc/src/raw_vec/mod.rs', 'library/alloc/src/alloc.rs',
         'library/std/src/fs.rs', 'library/std/src/sys/fs/unix.rs',
         'library/std/src/os/fd/owned.rs', 'library/std/src/io/mod.rs',
         'library/std/src/io/error.rs', 'library/alloc/src/io/error.rs']


def fetch(name):
    url = f'https://raw.githubusercontent.com/rust-lang/rust/{REVISION}/{name}'
    request = urllib.request.Request(url, headers={'User-Agent': 'Mixer-source-evidence/1'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            assert response.url == url
            data = response.read(4 * 1024 * 1024 + 1)
            assert len(data) <= 4 * 1024 * 1024
            content_type = response.headers.get('Content-Type', '')
            assert 'text/plain' in content_type
            data.decode('utf-8')
            row = dict(path=name, url=url, status=response.status, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), content_type=content_type)
        path = D / 'official-source' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        assert not path.exists()
        path.write_bytes(data)
        return row
    except urllib.error.HTTPError as error:
        return dict(path=name, url=url, status=error.code, success=False)


def main():
    assert not (D / 'fetch-receipt.json').exists(), 'one-shot source fetch'
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        rows = list(executor.map(fetch, FILES))
    receipt = dict(schema=1, at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   argv=sys.argv, python_version=sys.version, official_revision=REVISION,
                   files=rows, installed_toolchain_modified=False, product_executed=False,
                   worker_threads_joined=True, scope='Official platform-source discovery only; no work quote or compiled-library correspondence acceptance')
    (D / 'fetch-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(fetched=sum(r.get('status') == 200 for r in rows), selected=len(rows), missing=[r['path'] for r in rows if r.get('status') != 200])))


if __name__ == '__main__':
    main()
