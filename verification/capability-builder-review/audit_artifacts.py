#!/usr/bin/env python3
"""Independently audit retained builder evidence without invoking builds/devices."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'experimental-capability-runtime/build-verification/2026-10-23-final-v3'
PIN = 'b25e3b7de2391a80d12e7fd75e60903495bec120'
BUILDER_SHA = 'e7e34079d7af7d26162ccfc0c43cc6d269fb500ed42bd5e1aef91765e2fee076'
RECEIPT_SHA = '2744db5cb31d67286b4cf81bbfe9b8be6df8db95f7feb9d6e246801eb20f8b91'
HARNESS_SHA = '2a3b41c099e206bf7447f3a600c7448fefce2e9108d08ff2ae77cbafd416a79c'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def match(path, expected):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), f'not regular: {path}')
    raw = path.read_bytes()
    require(digest(raw) == expected, f'hash mismatch: {path}')
    return raw


def manifest(files):
    return ''.join(f'{sha}  {name}\n' for name, sha in sorted(files.items())).encode()


def main():
    receipt = json.loads(match(EVIDENCE / 'receipt.json', RECEIPT_SHA))
    require(receipt['source_revision'] == PIN and receipt['actual_native_revision_frozen'], 'native pin')
    require(receipt['qualification_source_unchanged'] and not receipt['device_commands'], 'scope')
    require(len(receipt['source_files']) == 5, 'qualification input count')
    for name, sha in receipt['source_files'].items():
        match(ROOT / name, sha)
    require(digest(manifest(receipt['source_files'])) == receipt['source_manifest_sha256'], 'input manifest')
    match(HERE / 'builder-candidate.py', BUILDER_SHA)
    match(HERE / 'test_public_builder.py', HARNESS_SHA)
    public_log = (HERE / 'final-public-cli.log').read_text()
    require(f'candidate_sha256={BUILDER_SHA}' in public_log, 'public candidate pin')
    require(f'harness_sha256={HARNESS_SHA}' in public_log, 'public harness pin')
    require(re.search(r'Ran 13 tests in [0-9.]+s\s+OK\s*\Z', public_log), 'public suite outcome')
    require(len(receipt['commands']) == 22 and len(receipt['evidence_files']) == 63, 'evidence counts')
    for name, sha in receipt['evidence_files'].items():
        match(EVIDENCE / name, sha)
    for command in receipt['commands']:
        require(command['exit_code'] == 0 and command['problem'] is None, 'outer command outcome')
        match(EVIDENCE / command['log'], command['sha256'])
    for mode in ('normal', 'optimized'):
        require(re.search(r'Ran 22 tests in [0-9.]+s\s+OK\s*\Z',
                          (EVIDENCE / f'tests-{mode}.log').read_text()), 'owned suite outcome')
    require('passed27 status/alias checks' in (EVIDENCE / 'host-c-smoke.log').read_text(), 'native C smoke outcome')
    require('passed52 checks' in (EVIDENCE / 'mixed-registry-run.log').read_text(), 'mixed C outcome')
    tree = subprocess.check_output(['git', 'ls-tree', '-rz', PIN], cwd=ROOT)
    git_entries = {}
    for entry in tree.split(b'\0'):
        if entry:
            meta, name = entry.split(b'\t', 1)
            mode, kind, blob = meta.decode().split()
            git_entries[name.decode()] = (mode, kind, blob)
    targets = {}
    for target, result in receipt['targets'].items():
        copied = match(EVIDENCE / result['builder_receipt'], result['builder_receipt_sha256'])
        build = json.loads(copied)
        stage = Path(result['library']['path']).parent.parent
        require((stage / 'receipt.json').read_bytes() == copied, 'copied receipt drift')
        require(build['source_revision'] == PIN and build['builder_sha256'] == BUILDER_SHA, 'builder pins')
        require(build['feature'] == 'experimental-capability-native', 'feature')
        require(not build['mutable_SDK_source_consumed'], 'mutable source')
        require(result['executed'] == (target == 'host'), 'target scope')
        require(sorted(p.name for p in (stage / 'lib').iterdir()) ==
                ['libmixer_vm_capability_experimental.a'], 'archive inventory')
        require(sorted(p.name for p in (stage / 'include').iterdir()) ==
                ['mixer_vm.h', 'mixer_vm_capability.h'], 'header inventory')
        archive = match(result['library']['path'], result['library']['sha256'])
        require(len(archive) == result['library']['bytes'] and archive.startswith(b'!<arch>\n'), 'archive format')
        for header in result['headers'].values():
            match(header['path'], header['sha256'])
        match(stage / 'capability-smoke', result['client_sha256'])
        match(stage / 'capability-layout.o', result['layout_object_sha256'])
        if target == 'host':
            match(stage / 'mixed-registry', receipt['host_tests']['mixed_client_sha256'])
        require(len(build['source_blobs']) == 81, 'source count')
        actual_names = {str(p.relative_to(stage / 'source')) for p in (stage / 'source').rglob('*') if p.is_file()}
        require(actual_names == set(build['source_blobs']), 'source export inventory')
        sources = {}
        for name, source in build['source_blobs'].items():
            mode, kind, blob = git_entries[name]
            require(mode in ('100644', '100755') and kind == 'blob' and blob == source['git_blob'], 'git blob identity')
            git_raw = subprocess.check_output(['git', 'cat-file', 'blob', blob], cwd=ROOT)
            require(digest(git_raw) == source['sha256'] and len(git_raw) == source['bytes'], 'git source bytes')
            require(match(stage / 'source' / name, source['sha256']) == git_raw, 'export bytes')
            sources[name] = source['sha256']
        require((stage / 'source-manifest.sha256').read_bytes() == manifest(sources), 'source manifest bytes')
        require(digest(manifest(sources)) == result['source_manifest_sha256'] == build['source_manifest_sha256'], 'source manifest hash')
        match(stage / 'source.tar', result['source_archive_sha256'])
        with tarfile.open(stage / 'source.tar') as bundle:
            members = bundle.getmembers()
            require(len(members) == len(sources) and {m.name for m in members} == set(sources), 'tar inventory')
            for member in members:
                require(member.isfile(), 'nonregular tar member')
                require(digest(bundle.extractfile(member).read()) == sources[member.name], 'tar bytes')
        for command in build['commands']:
            require(command['exit_code'] == 0 and command['problem'] is None, 'builder command outcome')
            match(stage / command['log'], command['sha256'])
            match(EVIDENCE / f"{target}-{command['log']}", command['sha256'])
        cargo = next(c for c in build['commands'] if c['name'] == 'cargo-build')
        require(all(flag in cargo['argv'] for flag in ('--locked', '--offline', '--release', '--lib', '--no-default-features')), 'cargo isolation flags')
        require(cargo['argv'][cargo['argv'].index('--features') + 1] == 'experimental-capability-native', 'cargo feature')
        require(cargo['cwd'] == '/', 'cargo cwd')
        for tool in build['tools'].values():
            match(tool['resolved_path'], tool['sha256'])
        nm_text = (stage / 'archive-symbols.log').read_text()
        symbols = sorted(set(re.findall(r'\b_?(mixer_vm_[A-Za-z0-9_]+)\b', nm_text)))
        require(symbols == sorted(build['public_C_symbols']) and len(symbols) == 27, 'public symbol inventory')
        targets[target] = {'archive_sha256': result['library']['sha256'], 'source_files': 81,
                           'builder_commands': len(build['commands']), 'scope': 'C execution' if target == 'host' else 'C layout compile and link only'}
    require(set(targets) == {'host', 'ios', 'ios-simulator', 'android'}, 'targets')
    for failed in receipt['prior_qualification_failures']:
        base = Path(failed['path'])
        match(base / 'failure.json', failed['failure_sha256'])
        match(base / 'mixed-registry-run.log', failed['log_sha256'])
        match(base / 'mixed_registry.fixture.c', failed['original_fixture_sha256'])
    old = receipt['retained_initial_failure']
    base = Path(old['output'])
    match(base / 'failure.json', old['failure_sha256'])
    match(base / 'archive-symbols.log', old['archive_symbols_log_sha256'])
    match(base / 'cargo-build.log', old['successful_cargo_log_sha256'])
    require(not (base / 'receipt.json').exists(), 'historical failed build completion')
    report = {
        'schema': 1, 'observed_at': datetime.now(timezone.utc).isoformat(),
        'audit_script_sha256': digest(Path(__file__).read_bytes()),
        'source_revision': PIN, 'builder_sha256': BUILDER_SHA,
        'implementation_receipt_sha256': RECEIPT_SHA,
        'independent_public_cli': {'harness_sha256': HARNESS_SHA,
            'log_sha256': digest((HERE / 'final-public-cli.log').read_bytes()),
            'test_functions': 13, 'modes_per_function': ['normal', 'optimized'],
            'scope': 'negative public CLI fixture executions, not real compiler qualification'},
        'matched': {'qualification_inputs': 5, 'outer_command_logs': 22, 'evidence_files': 63,
                    'committed_source_files_per_target': 81, 'target_archives': targets,
                    'normal_boundary_functions': 22, 'optimized_boundary_functions': 22,
                    'native_C_checks': 27, 'mixed_registry_checks': 52,
                    'prior_C_fixture_failures': 2, 'prior_nm_failure': 1},
        'result': 'All recorded input, artifact, source export, Git blob, tool and log hashes matched; independent CLI probes passed.',
        'limitations': ['No Swift bridge, release identity, signed activation or published packaging qualification.',
                       'Cross targets were compiled and linked only. No simulator or physical device execution.',
                       'Installed official tools and coordinated owned cache are trusted; no hostile same-user sandbox or binary reproducibility claim.',
                       'Existing VM profile, allocation and full Swift/FieldLog execution limits remain.']}
    (HERE / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
