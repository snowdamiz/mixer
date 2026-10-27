"""Bound exact private source/host/tool preimages; metadata and pure descriptor controls only."""
from pathlib import Path
import datetime
import json
import os
import platform
import shutil
import signal
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from prepare import (HERE, ROOT, LOADER_PATH, PHASE_PATH, HELPER_PATH, KEYS,
                     sha, canonical, write, identity, roster, checked_candidate, materialize)

RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
SDK = Path('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
FEATURES = ['experimental-swift-reactor', 'experimental-swift-wasi',
            'experimental-stream-validation', 'experimental-function-cache']
SCRATCH = HERE / 'owned-work'
RECEIPTS = []

def packed(values):
    values = [os.fsencode(value) for value in values]
    return struct.pack('<Q', len(values)) + b''.join(struct.pack('<Q', len(value)) + value for value in values)

def packed_environment(values):
    return packed([os.fsencode(k) + b'=' + os.fsencode(v)
                   for k, v in sorted(values.items(), key=lambda item: os.fsencode(item[0]))])

def group_exists(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False

def run(label, argv, environment, expected_code=0, expected_text=None, timeout=45):
    dest = HERE / 'commands' / label
    dest.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    actions = []
    with (dest / 'stdout').open('wb') as out, (dest / 'stderr').open('wb') as err:
        child = subprocess.Popen([str(value) for value in argv], cwd=ROOT, env=environment,
                                 stdout=out, stderr=err, start_new_session=True)
        timed_out = False
        while child.poll() is None:
            if time.monotonic() - start > timeout or (dest / 'stdout').stat().st_size + (dest / 'stderr').stat().st_size > 262144:
                timed_out = True
                os.killpg(child.pid, signal.SIGTERM)
                actions.append('TERM owned process group')
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    actions.append('KILL owned process group')
                break
            time.sleep(.02)
        code = child.wait(timeout=3)
    if group_exists(child.pid):
        os.killpg(child.pid, signal.SIGTERM)
        actions.append('TERM surviving owned descendants')
        deadline = time.monotonic() + 2
        while group_exists(child.pid) and time.monotonic() < deadline:
            time.sleep(.02)
        if group_exists(child.pid):
            os.killpg(child.pid, signal.SIGKILL)
            actions.append('KILL surviving owned descendants')
    absent = not group_exists(child.pid)
    stdout = (dest / 'stdout').read_bytes()
    stderr = (dest / 'stderr').read_bytes()
    passed = not timed_out and code == expected_code and absent
    if expected_text is not None:
        passed = passed and expected_text.encode() in stdout + stderr
    receipt = {'schema': 1, 'argv': [str(value) for value in argv],
        'cwd': str(ROOT), 'environment': environment, 'exit_code': code,
        'expected_exit_code': expected_code, 'expected_text': expected_text,
        'elapsed_seconds': time.monotonic() - start, 'timeout_seconds': timeout,
        'output_byte_limit': 262144, 'timed_out_or_output_limited': timed_out,
        'child_reaped': True, 'new_session': True, 'owned_process_group': child.pid,
        'owned_group_absent': absent, 'cleanup_actions': actions,
        'stdout': identity(dest / 'stdout'), 'stderr': identity(dest / 'stderr'),
        'expectation_met': passed}
    write(dest / 'receipt.json', receipt)
    RECEIPTS.append({'label': label, 'receipt': identity(dest / 'receipt.json'), 'expectation_met': passed})
    write(HERE / 'command-index.json', RECEIPTS)
    print(label + ': ' + ('pass' if passed else 'FAIL'), flush=True)
    assert passed, (label, stdout[-2000:], stderr[-4000:])
    return stdout

def build_record(parts, compiler_digest, output):
    assert len(parts) == 4 and all(parts)
    assert len(parts[0]) <= 65536 and all(len(part) <= 16384 for part in parts[1:])
    header = bytearray(512)
    header[:8] = b'MIXLBD01'
    for offset, value in [(8, 1), (16, 512), (24, 512 + sum(map(len, parts))),
                          (32, 145), (40, 11), (80, len(output))]:
        struct.pack_into('<Q', header, offset, value)
    target = b'aarch64-apple-darwin'
    header[88:88 + len(target)] = target
    for index, part in enumerate(parts):
        struct.pack_into('<Q', header, 48 + 8 * index, len(part))
        header[152 + 32 * index:184 + 32 * index] = bytes.fromhex(sha(part))
    header[280:312] = bytes.fromhex(compiler_digest)
    header[312:344] = bytes.fromhex(sha(output))
    return bytes(header) + b''.join(parts)

def extract_harness(source):
    loader = source[LOADER_PATH].decode()
    def between(start, end):
        a = loader.index(start)
        b = loader.index(end, a)
        return loader[a:b]
    fragments = {
        'constants': between('const HEADER:', '#[derive(Clone, Copy, Debug, PartialEq, Eq)]'),
        'error_usage_scaffold': between('#[derive(Clone, Copy, Debug, PartialEq, Eq)]\n#[repr(u8)]', '/// All actual File owners'),
        'descriptor_views': between('#[derive(Clone, Copy)]\nstruct Section', 'struct SessionView'),
        'parser_functions': between('fn word(b:', 'fn parse_session('),
        'actual_hash_function': between('    pub(super) fn hash(', '    pub(super) unsafe fn c_string'),
        'actual_identity_digest_block': between('    let embedded = COMPILED.map(', '    let build_digest ='),
    }
    scaffold = '''#![allow(dead_code)]
use std::io;
// Only the unrelated validator error's name is stubbed for this pure parser
// harness. No validator, proof, loader ingress, VM or writer is linked/run.
#[derive(Debug)] struct SwiftValidationFailure;
'''
    platform_hash = '''mod platform {
    use super::*;
    use std::ffi::c_void;
    #[link(name="System")] unsafe extern "C" {
        fn CC_SHA256(data:*const c_void,len:u32,md:*mut u8)->*mut u8;
    }
''' + fragments['actual_hash_function'] + '\n}\n'
    checks = (HERE / 'host/controls.rs').read_text()
    body = scaffold + ''.join(fragments[k] for k in ['constants', 'error_usage_scaffold', 'descriptor_views', 'parser_functions']) + platform_hash
    body += '\nfn checked_descriptor(build:&[u8],usage:&mut LoaderUsageV1)->Result<(),LoaderFailureV1>{\n    let b=parse_build(build)?;\n'
    body += fragments['actual_identity_digest_block'] + '\n    Ok(())\n}\n' + checks
    extraction = [{'name': name, 'source_path': LOADER_PATH,
        'source_sha256': sha(source[LOADER_PATH]), 'bytes': len(value.encode()),
        'extracted_sha256': sha(value.encode()), 'verbatim_from_candidate': True}
        for name, value in fragments.items()]
    return body.encode(), extraction

def main():
    assert not (HERE / 'seal.json').exists(), 'Never rerun a frozen producer'
    assert not SCRATCH.exists(), 'Preserve unexpected/failed owned scratch for explicit review'
    assert not (HERE / 'commands').exists(), 'Never overwrite command evidence'
    source, hosts, custody = checked_candidate()
    SCRATCH.mkdir()
    completed = False
    artifacts = []
    try:
        vm = SCRATCH / 'vm'
        materialize(vm)
        assert roster({str(p.relative_to(vm)): p.read_bytes() for p in vm.rglob('*') if p.is_file()}) == roster(source)
        environment = {'PATH': '/usr/bin:/bin', 'TMPDIR': str(SCRATCH), 'CARGO_MANIFEST_DIR': str(vm)}
        version = run('rustc-version', [RUSTC, '-vV'], environment, expected_text='rustc 1.99.0', timeout=10)
        (HERE / 'rustc-version.txt').write_bytes(version)
        revision = run('git-revision', ['git', 'rev-parse', 'HEAD'], environment, timeout=10).decode().strip()
        compiler = identity(RUSTC)
        headers = [identity(SDK / name) for name in ['usr/include/CommonCrypto/CommonDigest.h',
                    'usr/include/crt_externs.h', 'usr/include/mach-o/dyld.h', 'usr/include/unistd.h']]
        tools = {'rustc': compiler, 'rustc_version_sha256': sha(version),
                 'python': identity(Path(sys.executable).resolve()), 'python_version': sys.version,
                 'platform': platform.platform(), 'SDK_headers': headers}
        harness, extraction = extract_harness(source)
        (HERE / 'host/descriptor.rs').write_bytes(harness)
        write(HERE / 'extraction.json', {'schema': 1, 'fragments': extraction,
              'validator_error_type_is_stubbed': True, 'type_layout_claim': False,
              'production_metadata_has_no_stub': True, 'harness_sha256': sha(harness)})
        orchestration = [identity(HERE / name) for name in ['prepare.py', 'run.py', 'proposal.json', 'host/controls.rs']]
        closure = {'schema': 1, 'distribution': roster(source), 'host_support': roster(hosts),
            'orchestration': orchestration, 'tools': tools,
            'qualification_scope': 'Exact private metadata compilation; pure descriptor controls; no genuine retained-file loader admission'}
        write(HERE / 'build-input-manifest.json', closure)
        flags = [str(RUSTC), '--crate-name', 'mixer_vm', '--edition=2021', '--target', 'aarch64-apple-darwin',
                 '-C', 'overflow-checks=yes', '-C', 'panic=unwind']
        for feature in FEATURES:
            flags += ['--cfg', 'feature="' + feature + '"']
        def compile_bound(label, argv, output, manifest, variant=None):
            parts = [canonical(manifest), packed(argv), packed_environment(environment), version]
            values = [sha(parts[0]), sha(parts[1]), sha(parts[2]), compiler['sha256'], sha(parts[3])]
            compile_environment = environment | dict(zip(KEYS, values))
            if variant == 'missing':
                del compile_environment[KEYS[0]]
            elif variant == 'malformed':
                compile_environment[KEYS[0]] = 'G' * 64
            elif variant == 'stale':
                compile_environment[KEYS[0]] = '0' * 64
            dest = HERE / 'preimages' / label
            dest.mkdir(parents=True)
            for filename, data in zip(['manifest.json', 'argv.bin', 'environment.bin', 'compiler-version.txt'], parts):
                (dest / filename).write_bytes(data)
            write(dest / 'binding.json', {'schema': 1, 'source_tree_sha256': roster(source)['tree_sha256'],
                'source_members': 145, 'host_support_tree_sha256': roster(hosts)['tree_sha256'], 'host_support_members': 11,
                'compile_keys': dict(zip(KEYS, values)), 'actual_compile_identity_keys': {k: compile_environment[k] for k in KEYS if k in compile_environment},
                'negative_identity_variant': variant, 'compiler': compiler, 'compiler_version_sha256': sha(version),
                'manifest_sha256': sha(parts[0]), 'argv_sha256': sha(parts[1]), 'environment_sha256': sha(parts[2]),
                'orchestration_separate_from_host11': True})
            run(label, argv, compile_environment)
            assert identity(RUSTC) == compiler
            assert [identity(Path(h['path'])) for h in headers] == headers
            assert [identity(Path(item['path'])) for item in orchestration] == orchestration
            checked_candidate()
            actual = output.read_bytes()
            artifacts.append(identity(output) | {'label': label, 'executed': label.startswith('pure-')})
            descriptor = build_record(parts, compiler['sha256'], actual)
            (dest / 'build-preimage.bin').write_bytes(descriptor)
            return dest / 'build-preimage.bin'
        for mode, level in [('debug', '0'), ('optimized', '3')]:
            for production in [True, False]:
                label = 'metadata-' + mode + ('-production' if production else '-unit')
                output = SCRATCH / (label + '.rmeta')
                argv = flags + ['-C', 'opt-level=' + level]
                argv += ['--crate-type', 'rlib'] if production else ['--test']
                argv += [str(vm / 'src/lib.rs'), '--emit=metadata=' + str(output)]
                compile_bound(label, argv, output, closure)
                output.unlink()
            host_manifest = closure | {'compiled_input_kind': 'Extracted pure descriptor harness; no Mixer executable',
                                       'pure_harness': identity(HERE / 'host/descriptor.rs')}
            for variant in [None, 'missing', 'malformed', 'stale']:
                label = 'pure-' + mode + ('-bound' if variant is None else '-' + variant)
                output = SCRATCH / (label + '.bin')
                argv = [str(RUSTC), '--edition=2021', '--target', 'aarch64-apple-darwin', '-C', 'opt-level=' + level,
                        '-C', 'overflow-checks=yes', '-C', 'panic=unwind', str(HERE / 'host/descriptor.rs'), '-o', str(output)]
                descriptor = compile_bound(label, argv, output, host_manifest, variant)
                expected = 'descriptor_controls=41' if variant is None else 'identity_negative=' + variant
                run(label + '-controls', [output, descriptor, variant or 'bound'], environment,
                    expected_text=expected, timeout=10)
                output.unlink()
        # Fresh custody checks after all compilers and bounded pure executions.
        checked_candidate()
        assert roster(source)['member_count'] == 145 and roster(hosts)['member_count'] == 11
        write(HERE / 'results.json', {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'git_revision_context': revision, 'source_tree_sha256': roster(source)['tree_sha256'],
            'source_members': 145, 'support_tree_sha256': roster(hosts)['tree_sha256'], 'support_members': 11,
            'metadata_builds': 4, 'pure_harness_builds': 8, 'pure_bound_controls_each_mode': 41,
            'private_identity_negative_variants_each_mode': ['missing', 'malformed', 'stale'],
            'commands': len(RECEIPTS), 'all_command_expectations_met': all(r['expectation_met'] for r in RECEIPTS),
            'artifacts_measured_then_removed': artifacts, 'compiler': compiler, 'tools': tools,
            'actual_loader_ingress_executed': False, 'engine_VM_writer_executed': False,
            'type_layout_claim': False, 'WorkAuditPending_preserved': True,
            'budget_source_storage_work_host_pre_ingress_admission': 'pending',
            'phase_retention_integration': 'pending; source manifest must be rebound after any composition',
            'native_device_simulator_emulator_UI_capture': 'paused and unrun',
            'canonical_integration_production_publication_FieldLog_OTA_GA': 'pending'})
        completed = True
    finally:
        children_absent = all(json.loads((HERE / 'commands' / item['label'] / 'receipt.json').read_bytes())['owned_group_absent'] for item in RECEIPTS)
        scratch_removed = False
        if completed and children_absent:
            shutil.rmtree(SCRATCH)
            scratch_removed = not SCRATCH.exists()
        write(HERE / 'cleanup.json', {'schema': 1, 'completed': completed,
            'recorded_owned_child_groups_absent': children_absent,
            'owned_scratch_removed': scratch_removed, 'failed_scratch_preserved': not completed and SCRATCH.exists(),
            'scope': 'Only recorded owned groups and owned-work directory; no global inventory or unrelated processes',
            'native_or_capture_processes_started': False})

if __name__ == '__main__':
    main()
