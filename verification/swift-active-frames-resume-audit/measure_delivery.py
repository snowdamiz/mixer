#!/usr/bin/env python3
"""Measure original packets without extraction, compression, mutation or deletion."""
from pathlib import Path
import collections
import hashlib
import json
import tarfile

ROOT = Path(__file__).resolve().parents[2]
roots = [ROOT / 'verification/swift-active-frames-implementation',
         ROOT / 'verification/swift-active-frames-implementation-review']
groups = collections.defaultdict(list)
files = {}
archives = {}
archive_members = collections.defaultdict(list)
archive_paths = []
for root in roots:
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        name = str(path.relative_to(ROOT))
        files[name] = digest
        groups[digest].append(dict(path=name, bytes=len(data)))
        if path.name.endswith('.tar.gz'):
            archives.setdefault(digest, path)
            archive_paths.append(dict(path=name, sha256=digest, bytes=len(data)))
for path in archives.values():
    with tarfile.open(path) as stream:
        for member in stream:
            if member.isfile():
                data = stream.extractfile(member).read()
                archive_members[hashlib.sha256(data).hexdigest()].append(len(data))
total = sum(item['bytes'] for group in groups.values() for item in group)
unique = sum(group[0]['bytes'] for group in groups.values())
enc = lambda obj: (json.dumps(obj, sort_keys=True, indent=2) + '\n').encode()
result = dict(schema=1, scope='Original producer/reviewer packets only; archived member counts use each unique outer archive once',
              originalFiles=len(files), originalBytes=total, uniqueWholeFileBlobs=len(groups),
              uniqueWholeFileBytes=unique, duplicateWholeFileBytes=total-unique,
              allFilesManifestTreeSHA256=hashlib.sha256(enc(files)).hexdigest(),
              outerArchives=len(archive_paths), uniqueOuterArchives=len(archives),
              tarFileMembers=sum(map(len, archive_members.values())),
              tarFileMemberBytes=sum(sum(group) for group in archive_members.values()),
              uniqueTarFileMembers=len(archive_members),
              uniqueTarFileMemberBytes=sum(group[0] for group in archive_members.values()),
              duplicateTarFileMemberBytes=sum(sum(group)-group[0] for group in archive_members.values()),
              largestFile=max((dict(path=item['path'], bytes=item['bytes']) for group in groups.values() for item in group), key=lambda item:item['bytes']),
              everyFileBelow100MiB=all(item['bytes'] < 100*1024*1024 for group in groups.values() for item in group),
              archives=archive_paths,
              decision='Deliver unchanged original sealed packets directly with an exact allowlist; preserve all historical bytes. No custom pack or materializer. Git compression and remote object size are measured separately by root.')
print(json.dumps(result, sort_keys=True, indent=2))
