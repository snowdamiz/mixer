#!/usr/bin/env python3
"""Record exact offline replacement evidence and preserve the first preaccess seal."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PREACCESS = HERE.parent
ROOT = PREACCESS.parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parent_seal_path = PREACCESS / 'preaccess-seal.json'
    parent_bytes = parent_seal_path.read_bytes()
    assert sha(parent_bytes) == '60305ff555f5a0c26f87b2f57ca9ffa5e2a771a0f67a0f7e9f74787d0d65681f'
    parent = json.loads(parent_bytes)
    assert len(parent['members']) == 53
    for row in parent['members']:
        data = (PREACCESS / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256'], row['path']
    original = ROOT / 'verification/android-inputconnection-authority-audit'
    collection = json.loads((original / 'collection.json').read_text())
    sources = []
    for name, ranges in (
        ('TextView.java', [(2023,2027),(2617,2619),(7268,7270),(7330,7399),
                           (7440,7466),(7480,7543),(12742,12744),(12778,12795),
                           (12831,12860),(14934,14942),(15005,15021)]),
        ('Editor.java', [(1922,1939),(8109,8113),(8199,8207),(8388,8392)]),
        ('EditableInputConnection.java', [(81,87),(124,134)]),
        ('BaseInputConnection.java', [(204,208)]),
    ):
        relative = 'official/aosp36/' + name
        row = next(row for row in collection['official'] if row['path'] == relative)
        data = (original / relative).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
        sources.append({**row, 'source_path': str((original / relative).relative_to(ROOT)),
                        'reviewed_line_ranges': ranges})
    view = ROOT / 'verification/android-editor-cleanup-contract/official/View.java'
    data = view.read_bytes()
    assert sha(data) == 'ceb24df845d5304ba82422d828f0bd3af8f9da93c33ce898935850df875c7ac2'
    sources.append({'source_path': str(view.relative_to(ROOT)), 'bytes': len(data),
                    'sha256': sha(data), 'reviewed_line_ranges': [[16094,16100]],
                    'source': 'https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/core/java/android/view/View.java?format=TEXT'})
    edit = json.loads((HERE / 'EditText-source-receipt.json').read_text())
    data = (HERE / 'EditText.android-16.0.0_r1.java').read_bytes()
    assert len(data) == edit['bytes'] and sha(data) == edit['sha256']
    sources.append({**edit, 'source_path': str((HERE / 'EditText.android-16.0.0_r1.java').relative_to(ROOT)),
                    'reviewed_line_ranges': [[169,185]]})
    canonical = PREACCESS / 'inputs/native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java'
    sources.append({'source_path': str(canonical.relative_to(ROOT)), 'bytes': canonical.stat().st_size,
                    'sha256': sha(canonical.read_bytes()),
                    'reviewed_line_ranges': [[195,205],[347,351],[761,771]]})
    observations = {
        'schema': 1, 'at': datetime.datetime.now(datetime.UTC).isoformat(),
        'argv': sys.argv, 'python': sys.version,
        'scope': 'Source-backed replacement continuation preparation only; no candidate read or execution',
        'sources': sources,
        'official_sequence': ['View delegate/internal accessibility route',
                              'TextView SET_TEXT enabled/editable check',
                              'final one-arg to virtual two-arg setter',
                              'EditText forces EDITABLE',
                              'filters and beforeTextChanged before new Editable',
                              'new Editable and mText swap',
                              'movement selection before on/afterTextChanged',
                              'native manager/cursor/input invalidation before setter return',
                              'SET_TEXT final selection after setter return'],
        'safe_ordering_proposed_not_selected': ['reserve exact outer replacement before generic native widget entry',
                                               'revoke and exact-close predecessor on old buffer or retain precise no-target state',
                                               'restore/drop old cleanup scope then revalidate original live facts',
                                               'one no-target field replacement continuation across new buffer',
                                               'known finite callbacks and final action selection suffix',
                                               'final exact validation then one synchronous feature notification'],
        'implementation_compatibility_gap_not_native_pending': True,
        'original_preaccess_seal_sha256': sha(parent_bytes),
        'original_preaccess_members_verified_unchanged': 53,
        'candidate_reads': 0, 'candidate_executions': 0,
        'product_or_model_code_added': False,
        'native_capture_ui_device_or_process_inventory': False,
        'git_canonical_or_root_metadata_mutated': False,
        'pending': ['root replacement/event/promotion selection', 'sealed actual-source producer witness review',
                    'actual candidate implementation/host qualification', 'native qualification when resumed'],
    }
    (HERE / 'source-observations.json').write_text(json.dumps(observations, indent=2) + '\n')
    print(json.dumps({'parent_members_unchanged': 53, 'source_files_verified': len(sources),
                      'candidate_reads': 0, 'candidate_executions': 0}))


if __name__ == '__main__':
    main()
