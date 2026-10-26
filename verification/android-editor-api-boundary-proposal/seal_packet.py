#!/usr/bin/env python3
"""Seal this unselected source/contract packet, never production or native support."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    source_map = json.loads((HERE / 'source-map.json').read_text())
    drift = {}
    for relative, expected in source_map['files'].items():
        assert identity(HERE / 'inputs' / relative) == expected, relative
        if identity(ROOT / relative) != expected:
            drift[relative] = {'frozen': expected, 'current': identity(ROOT / relative)}
    (HERE / 'live-drift.json').write_text(json.dumps({'scope': 'Only enumerated source inputs; not live root metadata',
                                                   'drift': drift}, indent=2) + '\n')
    official = json.loads((HERE / 'official-inputs.json').read_text())
    for record in official['installed'] + official['remote']:
        if 'snapshot' in record:
            assert identity(HERE / record['snapshot']) == {'bytes': record['bytes'], 'sha256': record['sha256']}, record
    jdk = '/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'
    argv = ['/opt/homebrew/share/android-commandlinetools/build-tools/37.0.0/d8', '--version']
    version = subprocess.run(argv, text=True, capture_output=True, env=os.environ | {'JAVA_HOME': jdk})
    assert version.returncode == 0, version.stderr
    (HERE / 'd8-version.stdout.txt').write_text(version.stdout)
    (HERE / 'd8-version.stderr.txt').write_text(version.stderr)
    controls = json.loads((HERE / 'controls.json').read_text())
    cross = json.loads((HERE / 'cross-compile.json').read_text())
    assert controls['negative_contract_controls'] == 9 and controls['state_model_cases'] == 52
    assert controls['official_methods'] == 38 and controls['signature_classes'] == 9
    assert all(record['exit'] == 0 for record in cross['commands'])
    assert not cross['Android_runtime_or_classloading_or_OTA_authorization']
    for relative in ['collect.stderr.txt', 'cross-compile.stderr.txt', 'check.stderr.txt', 'index.stderr.txt']:
        assert not (HERE / relative).read_bytes(), relative
    receipt = {
        'schema': 1, 'at': datetime.datetime.now(datetime.UTC).isoformat(),
        'python': sys.version, 'command': ['python3', 'verification/android-editor-api-boundary-proposal/seal_packet.py'],
        'context_revision': source_map['context_revision'], 'hashes_authoritative_revision_contextual': True,
        'decision': 'Seal proposal only. Component implementation selection blocked on exact-target close/batch cleanup contract.',
        'proposal': identity(HERE / 'proposal.md'), 'contract': identity(HERE / 'contract.json'),
        'source_map': identity(HERE / 'source-map.json'), 'source_files': len(source_map['files']),
        'source_drift_count': len(drift),
        'exact_profile4_acceptance_sha256': '83f83c42d53b8bc5df50eaf84f751236f39d3fa66c827bf4e55635a4d424eea7',
        'exact_native_acceptance_sha256': '0c15ca808c2f5684d768125674cdfc0bf48bff672193f79fcaaee47726bf2478',
        'official_source_files': len(official['remote']),
        'tool_version_command': {'argv': argv, 'JAVA_HOME': jdk, 'exit': version.returncode,
                                 'stdout': 'd8-version.stdout.txt', 'stderr': 'd8-version.stderr.txt'},
        'executed': [
            {'argv': ['python3', 'verification/android-editor-api-boundary-proposal/collect_official.py'],
             'exit': 0, 'scope': 'Named official metadata/source reads and javap; versions/subcommands pinned in official-inputs.json',
             'stdout': 'collect.stdout.txt', 'stderr': 'collect.stderr.txt'},
            {'argv': ['python3', 'verification/android-editor-api-boundary-proposal/build_contract.py'],
             'exit': 0, 'scope': 'Independently enumerated contract writer; no product edits', 'stdout': '', 'stderr': ''},
            {'argv': ['python3', 'verification/android-editor-api-boundary-proposal/cross_compile.py'],
             'exit': 0, 'scope': 'UNSELECTED signature shapes only; exact JDK/SDK/D8 argv/streams in cross-compile.json',
             'stdout': 'cross-compile.stdout.txt', 'stderr': 'cross-compile.stderr.txt'},
            {'argv': ['python3', 'verification/android-editor-api-boundary-proposal/check_contract.py'],
             'exit': 0, 'scope': 'Contract/metadata/classfile and finite specification-model controls only',
             'stdout': 'check.stdout.txt', 'stderr': 'check.stderr.txt'},
            {'argv': ['python3', 'verification/android-editor-api-boundary-proposal/index_evidence.py'],
             'exit': 0, 'scope': '28 named frozen source spans; selectors are documentary',
             'stdout': 'index.stdout.txt', 'stderr': 'index.stderr.txt'}],
        'failed_attempts_retained': ['check-attempt-1.stderr.txt', 'check-attempt-2.stderr.txt', 'index-attempt-1.stderr.txt'],
        'checks': {'negative_contract_controls': 9, 'state_model_cases': 52, 'official_methods': 38,
                   'signature_classes': 9, 'compiled_Java17_SDK37': True, 'D8_min28': True,
                   'dex_class_defs': cross['dex_class_defs']},
        'current_API36_findings': ['old connection can regain authored authority at same focused Record',
                                  'platform close nesting flag is not universal operation revocation',
                                  'inherited menu has native batch prefix/suffix outside field hook',
                                  'native target reads/monitoring/spell/cursor/bounds lack wrapper fences',
                                  'nonnull immutable target already prevents setTarget',
                                  'super EditorInfo advertises some refused operations'],
        'cleanup_selection_blocker': ['stale-close skip can leave native batch ownership',
                                      'old-close can alter successor composition',
                                      'sealed close callbacks lack an existing used scoped cleanup path',
                                      'field CLOSING/exact target/renderer quarantine and active-edit unwind require root amendment'],
        'new_rendering_contexts': False, 'both_sdk36_guards_preserved': True,
        'component_implemented_or_usable': False, 'source_profile_selected': False,
        'public_V2_selected': False, 'native_or_OTA_or_GA_authorized': False,
        'prototypes_unselected_never_execute_or_package': True,
        'dependencies_credentials_publication_git_root_metadata_edits': False,
        'no_UI_capture_native_runtime_or_process_inventory': True,
        'cleanup': 'Only named host tool children; all command subprocesses exited and compiler-owned TemporaryDirectory removed. No native/capture process started.',
        'pending': ['Root exact-target close/quarantine/unwind and ancillary-async policy selection',
                    'Independent actual-source implementation/leaves and profile migration review',
                    'Whole product native linkage and API28..37 ART/runtime/IME/batch cleanup',
                    'TalkBack/design parity/physical acceptance matrix',
                    'Public V2/immutable published separate-repository FieldLog/OTA/signing/store/operations/GA']}
    (HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    files = {str(path.relative_to(HERE)): identity(path) for path in sorted(HERE.rglob('*'))
             if path.is_file() and path != HERE / 'manifest.json'}
    manifest = {'schema': 1, 'scope': 'Unselected Android editor boundary proposal only', 'files': files}
    (HERE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'manifest': identity(HERE / 'manifest.json'), 'receipt': identity(HERE / 'receipt.json'),
                      'members': len(files), 'member_bytes': sum(v['bytes'] for v in files.values()),
                      'source_drift_count': len(drift), 'component_selected': False}, indent=2))


if __name__ == '__main__':
    main()
