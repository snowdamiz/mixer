#!/usr/bin/env python3
"""Bounded read-only archive inspection; does not execute archived code."""
import datetime
import hashlib
import json
import pathlib
import stat
import sys
import time
import zipfile

BASE = pathlib.Path(__file__).resolve().parent

def main():
    start = time.monotonic()
    packet = pathlib.Path(sys.argv[1]).resolve()
    assert packet.parent == BASE.parent
    cache = packet.name == 'cache-controls-pass-review'
    cap = (128 if cache else 64) * 1024 * 1024
    archive = packet / 'artifact.zip'
    acquisition = json.loads((packet / 'acquisition.json').read_bytes())
    assert archive.stat().st_size == acquisition['zip_bytes'] <= 8 * 1024 * 1024
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == acquisition['sha256']
    selected = packet / 'selected'
    selected.mkdir()
    rows, seen, folded, total = [], set(), set(), 0
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist()
        assert len(entries) <= 4096
        declared = sum(r.file_size for r in entries)
        assert declared <= cap
        for row in entries:
            name = row.filename
            path = pathlib.PurePosixPath(name)
            assert name == str(path) and not path.is_absolute()
            assert not {'..', '.', '.git'} & set(path.parts)
            assert '\\' not in name and '\x00' not in name
            assert name not in seen and name.casefold() not in folded
            seen.add(name); folded.add(name.casefold())
            assert stat.S_IFMT(row.external_attr >> 16) in {0, stat.S_IFREG}
            assert not row.is_dir() and not row.flag_bits & 1
            retain = not cache or name in {'check_cache_state.py','test_runner.py','README.md','pack/manifest.json'} or name.startswith('logs/') or name.endswith('/receipt.json')
            sha, count, chunks = hashlib.sha256(), 0, []
            with source.open(row) as stream:
                while chunk := stream.read(1024 * 1024):
                    count += len(chunk); total += len(chunk)
                    assert count <= row.file_size and total <= cap
                    sha.update(chunk)
                    if retain: chunks.append(chunk)
            assert count == row.file_size
            kind = ('copied-historical-run' if name.startswith('runs/host-resource-ci-repair-root-1/') else
                    'current-run' if name.startswith('runs/ci-40740023152-1/') else
                    'current-controls' if name.startswith('logs/') else 'fixture-source-at-run') if cache else 'current-phoenix-packet'
            rows.append({'path': name, 'bytes': count, 'sha256': sha.hexdigest(), 'crc32':f'{row.CRC:08x}', 'classification':kind, 'retained':retain})
            if retain:
                target = selected.joinpath(*path.parts)
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as out: out.write(b''.join(chunks))
    result = {'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive_sha256':acquisition['sha256'],'entry_count':len(rows),'expanded_bytes':total,'declared_expanded_bytes':declared,'zip_cap_bytes':8*1024*1024,'expanded_cap_bytes':cap,'all_entries_streamed_for_crc_size_sha256':True,'entries':rows,'review_python':sys.version,'elapsed_seconds':round(time.monotonic()-start,6),'artifact_code_executed':False}
    with (packet / 'zip-manifest.json').open('x') as out: out.write(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ['entry_count','expanded_bytes','expanded_cap_bytes','artifact_code_executed']}))

if __name__ == '__main__': main()
