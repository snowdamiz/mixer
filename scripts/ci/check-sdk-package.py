#!/usr/bin/env python3
"""Check that public Git packaging and local SDK development expose one target graph."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]

def manifest(path):
    return json.loads(subprocess.check_output(
        ['swift', 'package', '--package-path', str(path), 'dump-package'], text=True))

public, development = manifest(ROOT), manifest(ROOT / 'sdk')
for key in ('name', 'products', 'platforms', 'dependencies', 'swiftLanguageVersions', 'toolsVersion',
            'cLanguageStandard', 'cxxLanguageStandard'):
    if public.get(key) != development.get(key):
        raise SystemExit('Public/development SDK manifest mismatch: ' + key)
if len(public['targets']) != len(development['targets']):
    raise SystemExit('Public/development SDK target count mismatch')
for exported, local in zip(public['targets'], development['targets']):
    local = dict(local)
    default = ('Tests' if local['type'] == 'test' else 'Sources') + '/' + local['name']
    local['path'] = 'sdk/' + local.get('path', default)
    if exported != local:
        raise SystemExit('Public/development SDK target mismatch: ' + local['name'])
print('Public Git and development SDK products, target graph, settings and source paths match.')
