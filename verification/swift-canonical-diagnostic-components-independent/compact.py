#!/usr/bin/env python3
"""Losslessly retain the verified immutable source copy as one bounded archive."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile

OUT=Path(__file__).resolve().parent
def sha(data):
    return hashlib.sha256(data).hexdigest()
def write(path,value):
    path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def member(path):
    assert path.is_file() and not path.is_symlink()
    data=path.read_bytes()
    return {'path':str(path.relative_to(OUT)),'bytes':len(data),'sha256':sha(data)}

def main():
    previous=(OUT/'seal.json').read_bytes()
    previous_seal=json.loads(previous)
    for row in previous_seal['members']:
        assert member(OUT/row['path'])==row
    source=OUT/'source'
    assert source.parent==OUT and not source.is_symlink()
    expected=json.loads((OUT/'source-manifest.json').read_text())
    archive=OUT/'source.tar.gz'
    assert not archive.exists()
    with archive.open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=9) as compressed:
            with tarfile.open(fileobj=compressed,mode='w',format=tarfile.PAX_FORMAT) as tar:
                for row in expected['members']:
                    data=(source/row['path']).read_bytes()
                    assert len(data)==row['bytes'] and sha(data)==row['sha256']
                    info=tarfile.TarInfo(row['path'])
                    info.mode=0o444
                    info.size=len(data)
                    info.mtime=0
                    info.uid=info.gid=0
                    tar.addfile(info,io.BytesIO(data))
    actual=[]
    with tarfile.open(archive,'r:gz') as tar:
        for entry in tar.getmembers():
            assert entry.isfile() and not Path(entry.name).is_absolute() and '..' not in Path(entry.name).parts
            data=tar.extractfile(entry).read()
            actual.append({'path':entry.name,'bytes':len(data),'sha256':sha(data)})
    assert actual==expected['members']
    assert sha(json.dumps(actual,sort_keys=True,separators=(',',':')).encode())==expected['tree_sha256']
    retained={'schema':1,'archive':member(archive),'source_members':len(actual),
              'uncompressed_source_bytes':sum(row['bytes'] for row in actual),
              'source_tree_sha256':expected['tree_sha256'],
              'archive_contents_independently_rehashed_against_execution_manifest':True,
              'previous_uncompressed_packet_seal_sha256':sha(previous),
              'compilation_source_path_historical':str(source),
              'canonical_pre_and_post_manifests_retained':True,
              'source_archive_is_data_only_no_code_executed_during_compaction':True}
    shutil.rmtree(source)
    assert not source.exists()
    write(OUT/'source-retention.json',retained)
    for name in ['result.json','source-custody.json']:
        path=OUT/name
        value=json.loads(path.read_text())
        value['retained_source_archive']=retained['archive']
        value['source_copy_archived_after_verification']=True
        write(path,value)
    path=OUT/'cleanup.json'
    cleanup=json.loads(path.read_text())
    cleanup['verified_source_copy_archived_then_unpacked_copy_removed']=str(source)
    cleanup['retained_source_archive']=retained['archive']
    cleanup['cleanup_scope']='Only this packet owned scratch, Python bytecode cache and losslessly archived source copy'
    write(path,cleanup)
    path=OUT/'README.md'
    text=path.read_text()
    text=text.replace('Source custody and directly generated accepted-source diffs are retained.',
                      'The exact source copy is losslessly retained in `source.tar.gz`; all 136 archived members are independently rehashed against the execution manifest before removing the unpacked copy. Source custody and directly generated accepted-source diffs are retained.')
    text += '\nReproduction entry points are `review.py setup`, `review.py tests`, `supplement.py prepare`, `supplement.py boundaries`, `supplement.py privacy`, `finalize.py`, then `compact.py`; invoke with the recorded Python tool and fresh evidence ownership. Their subprocess argv/environment/output receipts are retained under `commands/`. The setup refuses to overwrite an existing source freeze or command record.\n'
    path.write_text(text)
    members=[member(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p!=OUT/'seal.json']
    seal={'schema':1,'member_count':len(members),'member_bytes':sum(row['bytes'] for row in members),
          'members':members,'tree_sha256':sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode()),
          'scope':'Independent source136 host library, exact scalar/fixture extraction and privacy review only; immutable source archive; root acceptance separate'}
    write(OUT/'seal.json',seal)
    print(json.dumps({'status':'independent-bounded-host-review-pass','member_count':len(members),
                      'member_bytes':seal['member_bytes'],'source_archive_bytes':archive.stat().st_size,
                      'source_members_reverified':len(actual),'seal_sha256':sha((OUT/'seal.json').read_bytes()),
                      'tree_sha256':seal['tree_sha256']}),flush=True)

if __name__=='__main__':
    main()
