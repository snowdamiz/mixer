#!/usr/bin/env python3
"""Host-only receipt for the nondefault streaming validation experiment."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
FROZEN = '64123c509e861ddd522631b293eadebdaca11341'
ABI_PATHS = ['vm/include/mixer_vm.h', 'contracts/vm-profile-v1.json',
             'vm/profiles/numeric-v2.json', 'vm/profiles/table-memory-v3.json',
             'contracts/vm-session-v1.json']


def digest(data):
    return hashlib.sha256(data).hexdigest()


def manifest():
    paths = [p for p in (ROOT / 'vm').rglob('*') if p.is_file()
             and not {'target', 'verification', '__pycache__'}.intersection(p.relative_to(ROOT / 'vm').parts)
             and p.name != '.DS_Store']
    paths += [ROOT / p for p in ABI_PATHS if not p.startswith('vm/')]
    return {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in sorted(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True, help='fresh receipt directory name under vm/verification/stream-validation')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.name):
        parser.error('name must contain only letters, digits, underscores and hyphens')
    out = ROOT / 'vm/verification/stream-validation' / args.name
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    env['PATH'] = '/opt/homebrew/opt/rustup/bin:' + env.get('PATH', '')
    env['CARGO_TARGET_DIR'] = str(ROOT / 'vm/target/stream-validation-verification')
    target = pathlib.Path(env['CARGO_TARGET_DIR'])
    commands = []

    def run(name, cmd):
        began = time.monotonic()
        result = subprocess.run(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        output = result.stdout
        log = out / (name + '.log')
        log.write_text(output)
        commands.append({'name': name, 'argv': cmd, 'exit_code': result.returncode,
                         'elapsed_host_development_seconds': round(time.monotonic() - began, 6),
                         'output': log.relative_to(ROOT).as_posix(),
                         'output_sha256': digest(output.encode())})
        if result.returncode:
            raise RuntimeError(f'{name} failed, see {log}')
        print(name + ': passed', flush=True)
        return output

    start = manifest()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    # Compare public contracts/header and every original Rust production file.
    # The only permitted original lib edit is the nondefault module declaration.
    frozen_files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', FROZEN,
                                           '--', 'vm/src'], cwd=ROOT, text=True).splitlines()
    frozen_hashes = {}
    for path in frozen_files + ABI_PATHS:
        old = subprocess.check_output(['git', 'show', FROZEN + ':' + path], cwd=ROOT)
        current = (ROOT / path).read_bytes()
        if path == 'vm/src/lib.rs':
            current = current.replace(b'#[cfg(feature = "experimental-stream-validation")]\npub mod experimental;\n', b'')
        if current != old:
            raise RuntimeError('frozen production/ABI source differs: ' + path)
        frozen_hashes[path] = digest(old)
    (out / 'unchanged-production.json').write_text(json.dumps(frozen_hashes, indent=2) + '\n')
    versions = {k: run('version-' + k, cmd).strip() for k, cmd in {
        'cargo': ['cargo', '--version'], 'rustc': ['rustc', '--version', '--verbose'],
        'node': ['node', '--version'], 'clang': ['clang', '--version'],
        'python': ['python3', '--version'], 'macos': ['sw_vers'], 'architecture': ['uname', '-m']}.items()}
    run('format', ['cargo', 'fmt', '--manifest-path', 'vm/Cargo.toml', '--', '--check'])
    cargo = ['cargo', 'test', '--manifest-path', 'vm/Cargo.toml']
    default_tests = run('default-debug-tests', cargo + ['--', '--nocapture'])
    feature = ['--features', 'experimental-stream-validation']
    feature_debug = run('feature-debug-tests', cargo + feature + ['--', '--nocapture'])
    feature_release = run('feature-release-tests', cargo + ['--release'] + feature + ['--', '--nocapture'])
    oracles = {}
    for build, flags in [('debug', []), ('release', ['--release'])]:
        oracles[build] = run('feature-' + build + '-explicit-oracles', cargo + flags + feature + ['--', '--ignored', '--nocapture'])
    run('clippy-default', ['cargo', 'clippy', '--manifest-path', 'vm/Cargo.toml', '--all-targets', '--', '-D', 'warnings'])
    run('clippy-feature', ['cargo', 'clippy', '--manifest-path', 'vm/Cargo.toml', *feature, '--all-targets', '--', '-D', 'warnings'])
    abi = {}
    exports = {}
    artifacts = {}
    for label, flags in [('default', []), ('feature', feature)]:
        run(label + '-release-build', ['cargo', 'build', '--manifest-path', 'vm/Cargo.toml', '--release', *flags])
        archive = target / 'release/libmixer_vm.a'
        dynamic = target / 'release/libmixer_vm.dylib'
        artifacts[label] = {'archive_sha256': digest(archive.read_bytes()),
                            'dynamic_sha256': digest(dynamic.read_bytes())}
        # Darwin tool on the qualified host; matching public symbol set is recorded.
        symbols = run(label + '-symbols', ['nm', '-gU', str(dynamic)])
        exports[label] = sorted(set(re.findall(r'\b_mixer_vm_\w+', symbols)))
        if not exports[label]:
            raise RuntimeError('no public C symbols observed')
        for name in ['ffi_smoke', 'ffi_numeric_smoke', 'ffi_table_memory_smoke', 'ffi_session_smoke']:
            executable = target / (label + '-' + name)
            run(label + '-' + name + '-build', ['clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
                '-I', 'vm/include', 'vm/tests/' + name + '.c', str(archive), '-o', str(executable)])
            abi[label + '-' + name] = run(label + '-' + name + '-run', [str(executable)]).strip()
    if exports['default'] != exports['feature']:
        raise RuntimeError('experimental feature changed public C symbol set')
    finish = manifest()
    if start != finish:
        raise RuntimeError('scoped source changed during verification')
    source_manifest = ''.join(f'{sha}  {path}\n' for path, sha in finish.items())
    (out / 'source-manifest.sha256').write_text(source_manifest)
    allocation_pattern = (r'observation ([^:]+): source=(\d+) requested_peak=(\d+) retained=(\d+) allocations=(\d+) '
                          r'total_peak_reserved=(\d+) metadata_peak_reserved=(\d+) scratch_peak_reserved=(\d+) work=(\d+)')
    fields = ['source_bytes', 'measured_requested_peak', 'measured_retained', 'allocation_calls',
              'total_peak_reserved', 'metadata_peak_reserved', 'scratch_peak_reserved', 'work_credits']
    observations = {}
    for build, output in [('debug', feature_debug), ('release', feature_release)]:
        values = {m[0]: dict(zip(fields, map(int, m[1:]))) for m in re.findall(allocation_pattern, output)}
        if len(values) != 8 or not re.search(r'all 12 allocation ordinals failed closed', output):
            raise RuntimeError('missing direct allocation/failure observations')
        observations[build] = values
    # Native test-harness baseline may vary but incremental validator values should not.
    if observations['debug'] != observations['release']:
        raise RuntimeError('debug/release requested allocations differ')
    def counts(output):
        return {'passed': sum(map(int, re.findall(r'test result: ok\. (\d+) passed;', output))),
                'ignored': sum(map(int, re.findall(r'test result: ok\..*? (\d+) ignored;', output)))}
    receipt = {
        'schema_version': 1,
        'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'implementation_agent_selection': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh'},
        'independent_review': False, 'host_revision_at_start': head,
        'source_tree_digest': digest(source_manifest.encode()),
        'source_manifest': (out / 'source-manifest.sha256').relative_to(ROOT).as_posix(),
        'frozen_production_reference': FROZEN,
        'frozen_production_identity': (out / 'unchanged-production.json').relative_to(ROOT).as_posix(),
        'scope': 'macOS arm64 host only; nondefault complete selected-profile validation experiment; no executable route',
        'environment': {'PATH_prefix': '/opt/homebrew/opt/rustup/bin', 'CARGO_TARGET_DIR': env['CARGO_TARGET_DIR']},
        'versions': versions, 'commands': commands,
        'test_counts': {'default_debug': counts(default_tests), 'feature_debug': counts(feature_debug),
                        'feature_release': counts(feature_release),
                        'explicit_oracles': {k: counts(v) for k, v in oracles.items()}},
        'bounded_mutation_truncation_parity_cases': 2040,
        'new_independent_node_validation_cases_per_build': 178,
        'parity_reference_is_independent_standards_oracle': False,
        'intentional_additional_work_budget_rejection': {'frozen_decoder_accepts': True,
            'experimental_result': 'ResourceExhausted/Work; no proof', 'limit': 64000000,
            'used': 64000000, 'attempted': 64000001, 'function': 0, 'absolute_offset': 35306,
            'fixture': 'original two-function module;16384 unreachable calls to4096-parameter signature'},
        'allocation_observations': observations,
        'allocation_method': 'separate single-test integration process; System GlobalAlloc requested Layout bytes and live incremental peak; caller source/cancellation/harness baseline excluded; all observed proof drops and 12 injected allocation failures restore baseline',
        'allocation_failure_checks': {'each_of_12_allocation_ordinals': 'AllocationFailure with no leak',
            'oversized_source_and_invalid_limits': 'zero allocation even with first allocation forced to fail',
            'source_vec_to_box': 'one exact-source-length allocation; zero realloc across conversion and fallible vector growth',
            'cancellation': 'four deterministic allocation gates across source/metadata/body traversal; no proof'},
        'accounting_is_measured_rss_or_native_allocator_usable_size': False,
        'public_c_symbols': exports, 'c_abi_outputs': abi, 'built_artifacts': artifacts,
        'full_fieldlog_passed_to_experimental_validator': False,
        'unchanged_full_fieldlog_candidate': {'bytes': 52008982,
            'sha256': '19ac88f26f0daf34b64acb3c5b895fc79b52701368fc4c532ac8ede5844fee75',
            'validation_or_execution_claim': False},
        'open_gates': ['independent experimental review', 'complete standards suite and coverage-guided fuzzing',
            'physical iOS/Android experimental validator qualification (phones disconnected)',
            'allocator-internal/RSS/stack-frame observations on deployment targets',
            'all cache/execution/ABI/public routing design and implementation',
            'full Swift source/function/global/control/instruction/memory admission contract',
            'all34WASI imports and full Swift/FieldLog owned-VM execution', 'OTA/D3/GA']}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'receipt': (out / 'receipt.json').relative_to(ROOT).as_posix(),
                      'source_tree_digest': receipt['source_tree_digest'], 'test_counts': receipt['test_counts'],
                      'full_swift_qualified': False}, indent=2))


if __name__ == '__main__':
    main()
