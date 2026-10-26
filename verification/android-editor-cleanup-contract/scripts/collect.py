#!/usr/bin/env python3
"""Offline, bounded evidence collection. Never imports or executes frozen packets."""
from pathlib import Path
import hashlib, json, platform, shutil, sys

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
EXPECTED = {
    'verification/android-editor-api-boundary-proposal/manifest.json': '4ad1b8edebf913308484c4600282c5d8af0af00efbc67fa4f75962967b4cc08e',
    'verification/android-inputconnection-authority-audit/seal.json': 'c7fa78e51d301418479c0d2eab214211ac653800a9c747126e89a0b3b7756e82',
    'native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java': 'a217d0b178869f3e5c3fc2d80f30f559a22c76a303195e62bfcb73d3cce91cce',
    'native/android/app/src/dev/mixer/android/NativeRenderer.java': 'fa523aa1c9cd2f11a77022b008a5e983c8fda697a93e2a76585c01f79f50d725',
}

def sha(data): return hashlib.sha256(data).hexdigest()
def meta(path):
    d = path.read_bytes()
    return {'bytes': len(d), 'sha256': sha(d)}

def main():
    for name, expected in EXPECTED.items():
        assert meta(ROOT / name)['sha256'] == expected, name
    verified = []
    for name, count in [('verification/android-editor-api-boundary-proposal/manifest.json', 95),
                        ('verification/android-inputconnection-authority-audit/seal.json', 108)]:
        base = (ROOT / name).parent
        index = json.loads((ROOT / name).read_text())
        members = index.get('files', index.get('members'))
        entries = members.items() if isinstance(members, dict) else ((m['path'], m) for m in members)
        assert len(members) == count
        for relative, expected in entries:
            p = base / relative
            assert not p.is_symlink() and p.is_file(), relative
            assert meta(p) == {k: expected[k] for k in ('bytes', 'sha256')}, relative
        verified.append({'index': name, 'members': count, **meta(ROOT / name)})
    names = ['AGENTS.md', 'mixer-product-plan.md'] + [
        'native/android/app/src/dev/mixer/android/' + n + '.java'
        for n in ['NativeAppearanceViewsV2', 'NativeRenderer', 'NativeOwnerV2', 'NativeCoordinatorV2', 'NativeEnvironmentV2']]
    inputs = {}
    for name in names:
        dest = PACK / 'inputs' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
        inputs[name] = meta(dest)
    # Only exact official files actually used by this review are copied.
    for name in ['BaseInputConnection', 'EditableInputConnection', 'InputConnection', 'TextView', 'Editor']:
        src = ROOT / 'verification/android-inputconnection-authority-audit/official/aosp36' / (name + '.java')
        dest = PACK / 'official' / (name + '.java')
        shutil.copyfile(src, dest)
    digest = sha(json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode())
    report = {'schema': 1, 'scope': 'Design evidence only, no canonical changes or native execution',
              'command': 'python3 verification/android-editor-cleanup-contract/scripts/collect.py',
              'python': sys.version, 'platform': platform.platform(), 'frozen_packets': verified,
              'inputs': inputs, 'source_tree_digest': digest,
              'source_revision': 'No Git command used; exact bounded source hashes identify this tree',
              'official_snapshots': {p.name: meta(p) for p in sorted((PACK / 'official').glob('*.java'))}}
    (PACK / 'collection.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'frozen_members_verified': 203, 'source_tree_digest': digest, 'scope': report['scope']}))

if __name__ == '__main__': main()
