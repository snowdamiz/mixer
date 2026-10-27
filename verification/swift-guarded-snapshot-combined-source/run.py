"""Fresh exact metadata and narrow, separately bound combined host interactions."""
from pathlib import Path
import argparse
import datetime
import gzip
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
from prepare import (HERE, ROOT, REVIEW, CONTROL, PROFILE, COMPILE_KEYS, sha, canonical,
                     roster, checked_candidate, materialize, write, acceptance)

RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
SDK = Path('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
FEATURES = ['experimental-swift-reactor', 'experimental-swift-wasi',
            'experimental-stream-validation', 'experimental-function-cache']
SCRATCH = HERE / 'owned-work'
RELEASE_SHA = 'c08376ad082af1b12fed92571d23f2544d52dad389096b62790a4073b7b3a8b3'


def identity(path):
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=sha(data))


def packed(values):
    values = [os.fsencode(value) for value in values]
    return struct.pack('<Q', len(values)) + b''.join(struct.pack('<Q', len(value)) + value for value in values)


def packed_environment(values):
    return packed([os.fsencode(key) + b'=' + os.fsencode(value)
                   for key, value in sorted(values.items(), key=lambda item: os.fsencode(item[0]))])


def absent(group):
    try:
        os.killpg(group, 0)
        return False
    except ProcessLookupError:
        return True


def run(label, argv, environment, timeout=55, expected_text=None):
    folder = HERE / 'commands' / label
    folder.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    actions = []
    out_path, err_path = folder / 'stdout', folder / 'stderr'
    limited = False
    with out_path.open('wb') as out, err_path.open('wb') as err:
        child = subprocess.Popen([str(value) for value in argv], cwd=ROOT, env=environment,
                                 stdout=out, stderr=err, start_new_session=True)
        try:
            while child.poll() is None:
                if time.monotonic() - start > timeout or out_path.stat().st_size + err_path.stat().st_size > 4*1024*1024:
                    limited = True
                    os.killpg(child.pid, signal.SIGTERM)
                    actions.append('TERM owned group after timeout/output cap')
                    try:
                        child.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        actions.append('KILL owned group after TERM deadline')
                    break
                time.sleep(.02)
        finally:
            code = child.wait(timeout=3)
            if not absent(child.pid):
                os.killpg(child.pid, signal.SIGTERM)
                actions.append('TERM surviving owned descendants')
                until = time.monotonic() + 2
                while not absent(child.pid) and time.monotonic() < until:
                    time.sleep(.02)
                if not absent(child.pid):
                    os.killpg(child.pid, signal.SIGKILL)
                    actions.append('KILL surviving owned descendants')
    stdout, stderr = out_path.read_bytes(), err_path.read_bytes()
    passed = code == 0 and not limited and absent(child.pid)
    if expected_text is not None:
        passed = passed and expected_text.encode() in stdout
    receipt = dict(schema=1, argv=[str(value) for value in argv], environment=environment, cwd=str(ROOT),
        exit_code=code, elapsed_seconds=time.monotonic()-start, timeout_seconds=timeout,
        output_cap_bytes=4*1024*1024, timed_out_or_output_limited=limited,
        new_session=True, owned_process_group=child.pid, child_reaped=True,
        owned_group_absent=absent(child.pid), cleanup_actions=actions,
        stdout_sha256=sha(stdout), stderr_sha256=sha(stderr), expected_text=expected_text,
        expectation_met=passed, runner_sha256=sha(Path(__file__).read_bytes()))
    write('commands/' + label + '/receipt.json', receipt)
    if len(stdout) > 65536:
        (folder / 'stdout.gz').write_bytes(gzip.compress(stdout, mtime=0))
        out_path.unlink()
        receipt['stdout_storage'] = 'stdout.gz, hash is exact uncompressed bytes'
        write('commands/' + label + '/receipt.json', receipt)
    print(json.dumps(dict(label=label, exit_code=code, expectation_met=passed,
                         elapsed_seconds=receipt['elapsed_seconds'])), flush=True)
    assert passed, (label, stdout[-2000:], stderr[-4000:])
    return stdout, receipt


def release():
    value = acceptance('guarded-snapshot-work-admission-host-acceptance.json', RELEASE_SHA)
    write('root-dependent-release.json', dict(schema=1, root_acceptance=value,
        parent_compiler_release='Root explicitly released exact production/unit metadata and narrow synthetic privatecore -> A commit -> real complete tests after common acceptance; one whole-source compiler at a time.',
        bootstrap_H_or_helper_delegation_included=False, loader_or_writer_authorized=False,
        native_checks='paused and pending'))
    return value


def test_source(source):
    source = dict(source)
    appended = [
        ('src/experimental_swift_reactor/control_tests.rs', 'interaction-tests.inc.rs'),
        ('src/experimental_swift_reactor/cache.rs', 'cache-tests.inc.rs'),
        (PROFILE, 'profile-tests.inc.rs'),
    ]
    overlays = []
    for path, fixture in appended:
        data = (HERE / fixture).read_bytes()
        before = source[path]
        source[path] += data
        overlays.append(dict(path=path, base_bytes=len(before), base_sha256=sha(before),
                             append=identity(HERE / fixture), resulting=row_for(source, path)))
    write('test-overlay-manifest.json', dict(schema=1, source=roster(source),
        exact_product_source=roster(checked_candidate()[0]), append_operations=overlays,
        product_source145_unchanged=True, test_overlay_is_not_host11=True,
        expected_unit_floor_before=1898105, expected_unit_floor_combined=1899541, delta=1436))
    return source


def row_for(source, name):
    data = source[name]
    return dict(path=name, bytes=len(data), sha256=sha(data))


def compile_one(label, unit=False, interactions=False, optimized=False):
    assert not (HERE / 'seal.json').exists(), 'Never mutate a frozen packet'
    root_release = release()
    source, hosts = checked_candidate()
    assert not (SCRATCH / label).exists()
    work = SCRATCH / label
    work.mkdir(parents=True)
    completed = False
    artifact = work / ('interactions.bin' if interactions else 'candidate.rmeta')
    try:
        actual_source = test_source(source) if interactions else source
        vm = work / 'vm'
        if interactions:
            for name, data in actual_source.items():
                path = vm / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        else:
            materialize(vm)
        assert roster({str(path.relative_to(vm)): path.read_bytes() for path in vm.rglob('*') if path.is_file()}) == roster(actual_source)
        environment = {'PATH':'/usr/bin:/bin', 'TMPDIR':str(work), 'RUSTC_BOOTSTRAP':'1',
                       'CARGO_MANIFEST_DIR':str(vm), 'SDKROOT':str(SDK)}
        version, version_receipt = run(label + '-rustc-version', [RUSTC, '-vV'], environment, timeout=10,
                                       expected_text='rustc 1.99.0')
        compiler = identity(RUSTC)
        headers = [identity(SDK / name) for name in ['usr/include/CommonCrypto/CommonDigest.h',
            'usr/include/crt_externs.h', 'usr/include/mach-o/dyld.h', 'usr/include/unistd.h']]
        orchestration = [identity(HERE / name) for name in ['prepare.py', 'run.py', 'host-test-plan.json',
            'root-dependent-release.json', 'interaction-tests.inc.rs', 'cache-tests.inc.rs', 'profile-tests.inc.rs']]
        tools = dict(rustc=compiler, rustc_version_sha256=sha(version),
            python=identity(Path(sys.executable).resolve()), python_version=sys.version,
            host_platform=platform.platform(), SDK_headers=headers,
            cc=identity(Path('/usr/bin/cc')), separate_from_host11=True)
        closure = dict(schema=1, distribution=roster(source), host_support=roster(hosts),
            compiled_source=roster(actual_source), test_overlay=interactions,
            orchestration=orchestration, tools=tools, root_acceptance=root_release,
            qualification_scope='Synthetic selected-core/A-commit/real-complete interaction only' if interactions else 'Exact source145 metadata only, no executable')
        argv = [str(RUSTC), '--crate-name', 'mixer_vm', '--edition=2021', '--target', 'aarch64-apple-darwin',
            '-C', 'opt-level=' + ('3' if optimized else '0'), '-C', 'overflow-checks=yes',
            '-C', 'panic=unwind', '-Zmir-opt-level=0']
        for feature in FEATURES:
            argv += ['--cfg', 'feature="' + feature + '"']
        argv += ['--test'] if unit or interactions else ['--crate-type', 'rlib']
        argv += [str(vm / 'src/lib.rs')]
        argv += ['--emit=link', '-o', str(artifact)] if interactions else ['--emit=metadata=' + str(artifact)]
        parts = [canonical(closure), packed(argv), packed_environment(environment), version]
        values = [sha(parts[0]), sha(parts[1]), sha(parts[2]), compiler['sha256'], sha(parts[3])]
        actual_environment = environment | dict(zip(COMPILE_KEYS, values))
        preimage = HERE / 'preimages' / label
        preimage.mkdir(parents=True, exist_ok=False)
        for filename, data in zip(['manifest.json', 'argv.bin', 'environment.bin', 'compiler-version.txt'], parts):
            (preimage / filename).write_bytes(data)
        write('preimages/' + label + '/binding.json', dict(schema=1,
            distribution_source_tree_sha256=roster(source)['tree_sha256'],
            compiled_source_tree_sha256=roster(actual_source)['tree_sha256'],
            source_members=145, host_support_members=11,
            host_support_tree_sha256=roster(hosts)['tree_sha256'],
            compile_identity_keys=dict(zip(COMPILE_KEYS, values)),
            environment_preimage_excludes_only_five_injected_keys=True,
            orchestration_tools_SDK_separate_from_host11=True,
            no_previous_component_build_identity_reused=True))
        _, receipt = run(label, argv, actual_environment, timeout=55)
        assert identity(RUSTC) == compiler
        assert [identity(Path(item['path'])) for item in orchestration] == orchestration
        assert [identity(Path(item['path'])) for item in headers] == headers
        assert roster({str(path.relative_to(vm)): path.read_bytes() for path in vm.rglob('*') if path.is_file()}) == roster(actual_source)
        checked_candidate()
        output = identity(artifact)
        write('commands/' + label + '/artifact.json', output | dict(executed=interactions))
        if interactions:
            run(label + '-tests', [artifact, 'combined_source_interaction_', '--nocapture', '--test-threads=1'],
                {'PATH':'/usr/bin:/bin'}, timeout=30, expected_text='4 passed; 0 failed')
        write('commands/' + label + '/scope.json', dict(schema=1,
            exact_source145=roster(source)['tree_sha256'], compiled_source=roster(actual_source)['tree_sha256'],
            metadata_only=not interactions, cfg_test=unit or interactions,
            new_interaction_tests=4 if interactions else 0,
            actual_loader_guest_cache_scope_construct_writer_executed=False,
            synthetic_private_selected_core=interactions,
            actual_A_commit_and_real_complete=interactions,
            immutable_source145_not_executed=True,
            bootstrap_H_full_funding_healthy_cleanup_real_writer_or_GA_qualified=False))
        completed = True
    finally:
        # Only this runner's owned scratch and recorded groups are inspected.
        receipts = [json.loads(path.read_bytes()) for path in (HERE / 'commands').glob(label + '*/receipt.json')]
        groups_absent = all(item['owned_group_absent'] for item in receipts)
        removed_artifact = identity(artifact) if artifact.exists() else None
        if groups_absent:
            shutil.rmtree(work)
        write('commands/' + label + '/cleanup.json', dict(schema=1, completed=completed,
            recorded_owned_groups_absent=groups_absent, owned_scratch_removed=not work.exists(),
            removed_artifact=removed_artifact, no_global_inventory=True,
            no_native_UI_capture_started=True, scope='Only owned commands and scratch'))
        if SCRATCH.exists() and not any(SCRATCH.iterdir()):
            SCRATCH.rmdir()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('label')
    parser.add_argument('--unit', action='store_true')
    parser.add_argument('--interactions', action='store_true')
    parser.add_argument('--optimized', action='store_true')
    args = parser.parse_args()
    compile_one(args.label, unit=args.unit, interactions=args.interactions, optimized=args.optimized)
