#!/usr/bin/env python3
"""Collect uncalled compiler composition evidence in one owned temporary tree.

Never runs a VM/test binary, reads a retained reactor, changes live VM sources,
uses Git/network/native tools, or selects/accepts a lifecycle implementation.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'verification/swift-calls-dispatch-root-review/live-v7-integration-retry'
EXPECTED = '3dee84f70c852c2a26572c1d6e3463e45e56760a6bba403fabfb9c355ccb1cd3'
TOOL = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
PINS = {
    'rustc': 'dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0',
    'cargo': 'fc7aa5077deca8abc0651f329e8ec1d968f520e996a93b428f9935014362b382',
}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else encoded(value))

def manifest(tree):
    return {str(p.relative_to(tree)): digest(p.read_bytes())
            for p in sorted(tree.rglob('*')) if p.is_file()}

def group_members(group):
    result = subprocess.run(['/bin/ps', '-axo', 'pid=,pgid=,command='],
                            check=True, capture_output=True, text=True)
    return [line.strip() for line in result.stdout.splitlines()
            if len(line.split(None, 2)) >= 2 and line.split(None, 2)[1] == str(group)]

def archive(tree, output):
    with tarfile.open(output, 'w:gz') as packed:
        for name in manifest(tree):
            packed.add(tree / name, arcname=name, recursive=False)

def main():
    attempt = HERE / 'attempts' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    attempt.mkdir(parents=True)
    baseline = json.loads((BASE / 'final-live-manifest.json').read_text())
    assert len(baseline) == 130
    assert digest(encoded(baseline)) == EXPECTED
    for key, pin in PINS.items():
        assert digest((TOOL / key).read_bytes()) == pin, key
    assert not any(os.environ.get(key) for key in
                   ['DYLD_INSERT_LIBRARIES', 'LD_PRELOAD', 'RUSTC_WRAPPER',
                    'RUSTC_WORKSPACE_WRAPPER', 'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS'])
    scratch = Path(tempfile.mkdtemp(prefix='mixer-lifecycle-contract-')).resolve()
    source = scratch / 'source'
    source.mkdir()
    commands = []
    receipt = {'schema': 'mixer.swift-lifecycle.contract-composition.1',
               'selected': False, 'runtime': False, 'vmExecutions': 0,
               'nativeInstancesCreated': 0, 'targetArtifactRead': False,
               'baselineClosure': EXPECTED, 'baselineFileCount': 130,
               'toolSHA256': PINS, 'scratch': str(scratch), 'commands': commands,
               'scope': 'Uncalled Rust type/borrow composition only; no product/accounting/runtime acceptance.'}
    def run(label, argv, expected_success=True, target=None):
        before = manifest(source)
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('CARGO_', 'RUST'))}
        env.update(PATH=str(TOOL) + ':/usr/bin:/bin:/usr/sbin:/sbin',
                   RUSTC=str(TOOL / 'rustc'), CARGO_INCREMENTAL='0', CARGO_NET_OFFLINE='true')
        if target is not None:
            env['CARGO_TARGET_DIR'] = str(target)
        started = datetime.now(timezone.utc).isoformat()
        process = subprocess.Popen(argv, cwd=source, env=env, start_new_session=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        timed_out = False
        try:
            output, _ = process.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate()
        remaining = group_members(process.pid)
        if remaining:
            os.killpg(process.pid, signal.SIGKILL)
            remaining = group_members(process.pid)
        log = label + '.log.gz'
        write(attempt / log, gzip.compress(output, mtime=0))
        row = {'label': label, 'argv': argv, 'cwd': str(source),
               'target': str(target) if target is not None else None,
               'startedUTC': started, 'finishedUTC': datetime.now(timezone.utc).isoformat(),
               'exitCode': process.returncode, 'expectedSuccess': expected_success,
               'timedOut': timed_out, 'processGroup': process.pid,
               'remainingGroup': remaining, 'sourceBefore': digest(encoded(before)),
               'sourceAfter': digest(encoded(manifest(source))),
               'sourceUnchanged': before == manifest(source),
               'outputSHA256': digest(output), 'log': log}
        commands.append(row)
        write(attempt / 'commands.json', commands)
        assert not timed_out and not remaining and row['sourceUnchanged'], row
        assert (process.returncode == 0) == expected_success, output.decode(errors='replace')[-12000:]
        return output
    try:
        for name, expected in baseline.items():
            path = Path(name)
            assert not path.is_absolute() and '..' not in path.parts
            data = (ROOT / 'vm' / path).read_bytes()
            assert digest(data) == expected, name
            write(source / path, data)
        write(attempt / 'baseline-manifest.json', baseline)
        archive(source, attempt / 'baseline-source.tar.gz')
        probe = (HERE / 'composition_probe.rs').read_bytes()
        path = source / 'src/experimental_swift_reactor/lifecycle_contract_probe.rs'
        path.write_bytes(probe)
        frame = source / 'src/experimental_swift_reactor/frame_operations.rs'
        frame.write_bytes(frame.read_bytes() +
                          b'\n#[path="lifecycle_contract_probe.rs"]\nmod lifecycle_contract_probe;\n')
        witness = manifest(source)
        write(attempt / 'witness-manifest.json', witness)
        archive(source, attempt / 'witness-source.tar.gz')
        receipt['witnessClosure'] = digest(encoded(witness))
        run('rustc-version', [str(TOOL / 'rustc'), '--version', '--verbose'])
        run('cargo-version', [str(TOOL / 'cargo'), '--version'])
        run('python-version', [sys.executable, '--version'])
        for features in ['swift', 'all']:
            for release in [False, True]:
                label = features + ('-release' if release else '-debug')
                argv = [str(TOOL / 'cargo'), 'check', '--lib', '--locked', '--offline', '--no-default-features']
                argv += ['--all-features'] if features == 'all' else ['--features', 'experimental-swift-reactor']
                if release:
                    argv += ['--release']
                run(label, argv, target=scratch / ('target-' + label))
        negatives = {
            'owner-during-growth': '''fn bad(owner:&mut SwiftReactorInstance,cursor:Cursor)->Result<(),SwiftRunFailure>{let(mut phase,context)=owner.prepare_growth(cursor)?;owner.lifecycle=Lifecycle::Ready;phase.enter(35)?;drop(context);Ok(())}''',
            'ready-before-retained-completion': '''fn bad<'a>(owner:&'a mut SwiftReactorInstance,cursor:Cursor)->Result<GrowthCompletion<'a>,SwiftRunFailure>{let(phase,context)=owner.prepare_growth(cursor)?;let pending=SwiftGrowthStorage::empty();let storage=FrameOperationStorage{preparation:None,entry:None,returned:None,drained:None,controlled:None};let completed=call_dispatch::complete(phase,context,pending,storage,None);if matches!(completed,GrowthCompletion::Completed(FrameCompletion::Completed)){owner.lifecycle=Lifecycle::Ready;}Ok(completed)}''',
        }
        for label, body in negatives.items():
            data = probe + b'\n' + body.encode() + b'\n'
            path.write_bytes(data)
            write(attempt / ('negative-' + label + '.rs'), data)
            write(attempt / ('negative-' + label + '-manifest.json'), manifest(source))
            output = run('negative-' + label,
                         [str(TOOL / 'cargo'), 'check', '--lib', '--locked', '--offline',
                          '--no-default-features', '--features', 'experimental-swift-reactor'],
                         expected_success=False, target=scratch / ('target-negative-' + label))
            assert any(code in output for code in [b'error[E0499]', b'error[E0502]', b'error[E0506]']), output
            path.write_bytes(probe)
        assert manifest(source) == witness
        assert all(digest((ROOT / 'vm' / name).read_bytes()) == pin for name, pin in baseline.items())
        receipt['liveBaselineRecheckedAfter'] = True
        receipt['compositionPassed'] = True
    except BaseException as error:
        receipt['compositionPassed'] = False
        receipt['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        holders = subprocess.run(['/usr/sbin/lsof', '-nP', '+D', str(scratch)], capture_output=True)
        write(attempt / 'holders.log', holders.stdout + holders.stderr)
        remaining = {str(row['processGroup']): group_members(row['processGroup']) for row in commands}
        clean_groups = not any(remaining.values())
        cleanup = {'scratch': str(scratch), 'holderCheckExitCode': holders.returncode,
                   'holderCheckEmpty': holders.returncode == 1 and not holders.stdout,
                   'remainingCommandGroups': remaining, 'groupsEmpty': clean_groups}
        if cleanup['holderCheckEmpty'] and clean_groups:
            files = [p for p in scratch.rglob('*') if p.is_file()]
            cleanup.update(filesRemoved=len(files), logicalBytesRemoved=sum(p.stat().st_size for p in files))
            shutil.rmtree(scratch)
        cleanup['ownedScratchRemoved'] = not scratch.exists()
        write(attempt / 'cleanup.json', cleanup)
        receipt['cleanupPassed'] = cleanup['ownedScratchRemoved'] and cleanup['holderCheckEmpty'] and clean_groups
        receipt['finishedUTC'] = datetime.now(timezone.utc).isoformat()
        write(attempt / 'receipt.json', receipt)
        print(attempt, flush=True)

if __name__ == '__main__':
    main()
