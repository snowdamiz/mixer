#!/usr/bin/env python3
"""Read-only Git blob-size reproduction for the pinned parent commit."""
import collections
import json
import subprocess

REVISION = 'c531cfc81cf89cdd591835fedd1dba5a414d31c9'
result = subprocess.run(['git', 'ls-tree', '-rl', REVISION], capture_output=True, check=True, timeout=30)
groups = collections.Counter()
count = 0
for line in result.stdout.splitlines():
    metadata, _, path = line.partition(b'\t')
    size = metadata.split()[-1]
    if size.isdigit():
        groups[path.split(b'/')[0].decode()] += int(size)
        count += 1
print(json.dumps({'revision': REVISION, 'files': count, 'tracked_regular_bytes': sum(groups.values()),
                  'by_top_directory': dict(groups.most_common())}, indent=2))
