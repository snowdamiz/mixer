#!/usr/bin/env python3
"""Capture only committed owned sources for independent Android generator review."""
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import tarfile

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[1]
revision = subprocess.check_output(['git', 'rev-parse', sys.argv[1] + '^{commit}'], cwd=ROOT, text=True).strip()
label = '-' + sys.argv[2] if len(sys.argv) > 2 else ''
source = OUT / ('.local/source' + label)
if source.exists():
    raise RuntimeError('Refusing to replace existing frozen source; retain each review attempt.')
source.mkdir(parents=True)
archive = subprocess.check_output(['git', 'archive', '--format=tar', revision, 'cli', 'sdk', 'updates', 'native/android'], cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
    stream.extractall(source, filter='data')
manifest = {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source.rglob('*')) if p.is_file()}
text = ''.join(digest + '  ' + path + '\n' for path, digest in manifest.items())
(OUT / ('frozen-source' + label + '.sha256')).write_text(text)
receipt = {'revision': revision, 'git_tree': subprocess.check_output(['git', 'rev-parse', revision + '^{tree}'], cwd=ROOT, text=True).strip(), 'command': ['git', 'archive', '--format=tar', revision, 'cli', 'sdk', 'updates', 'native/android'], 'archive_sha256': hashlib.sha256(archive).hexdigest(), 'source_manifest_sha256': hashlib.sha256(text.encode()).hexdigest(), 'source_files': len(manifest), 'scope': 'Independent committed source copy; no live mutable implementation files used for review execution.'}
(OUT / ('freeze' + label + '.json')).write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
