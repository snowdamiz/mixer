#!/usr/bin/env python3
"""Compile frozen contract types in isolated metadata overlays before product edits."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = HERE / 'results' / STAMP
BUILD = HERE / 'build' / STAMP
OUT.mkdir(parents=True, exist_ok=False)
BUILD.mkdir(parents=True, exist_ok=False)
ENV = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'])


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


files = [ROOT / 'vm/Cargo.toml', ROOT / 'vm/Cargo.lock']
for directory in ['src', 'tests', 'include']:
    files += sorted(p for p in (ROOT / 'vm' / directory).rglob('*') if p.is_file())
source = {str(p.relative_to(ROOT / 'vm')): sha(p) for p in files}
(OUT / 'source-manifest.json').write_bytes(encoded(source))
with tarfile.open(OUT / 'source.tar.gz', 'w:gz') as archive:
    for path in files:
        archive.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
(OUT / 'inputs').mkdir()
for name in ['preflight.py', 'control_candidate.rs']:
    (OUT / 'inputs' / name).write_bytes((HERE / name).read_bytes())
freeze = ROOT / 'verification/swift-executor-control-next-slice/root-freeze.json'
(OUT / 'inputs/root-freeze.json').write_bytes(freeze.read_bytes())
commands = []
binaries = []
measurements = []
variants = []
status = 'failed-preflight'


def command(name, argv, cwd, target=None, closure=None):
    if closure is not None:
        assert manifest(cwd) == closure, 'changed before ' + name
    env = dict(ENV)
    if target is not None:
        env['CARGO_TARGET_DIR'] = str(target)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    run = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, timeout=600)
    log = OUT / (name + '.log')
    log.write_bytes(run.stdout)
    if closure is not None:
        assert manifest(cwd) == closure, 'changed after ' + name
    commands.append(dict(name=name, argv=argv, cwd=str(cwd),
                         target=str(target) if target else None, exitCode=run.returncode,
                         startedUTC=started, completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         output=log.name, outputSHA256=sha(log),
                         sourceBeforeAfterVerified=closure is not None))
    print(name, run.returncode, flush=True)
    assert run.returncode == 0, run.stdout.decode(errors='replace')[-5000:]
    return run.stdout.decode()


try:
    revision = command('revision', ['git', 'rev-parse', 'HEAD'], ROOT).strip()
    command('rustc-version', ['rustc', '-vV'], ROOT)
    command('cargo-version', ['cargo', '-V'], ROOT)
    command('python-version', ['python3', '--version'], ROOT)
    accepted = json.loads((ROOT / 'verification/swift-value-operations-root-review/acceptance.json').read_text())
    assert hashlib.sha256(encoded(source)).hexdigest() == accepted['sourceTreeSHA256']
    for config, flags in [('span', ['--features', 'experimental-span-execution']), ('all', ['--all-features'])]:
        for profile in ['debug', 'release']:
            label = config + '-' + profile
            with tarfile.open(OUT / 'source.tar.gz') as archive:
                archive.extractall(BUILD / label, filter='data')
            vm = BUILD / label / 'vm'
            borrowed = vm / 'src/experimental/execution/borrowed.rs'
            borrowed.write_text(borrowed.read_text() + '\n#[cfg(test)]\nmod control_preflight {\nuse super::*;\n'
                                + (OUT / 'inputs/control_candidate.rs').read_text() + '\n}\n')
            closure = manifest(vm)
            (OUT / (label + '-manifest.json')).write_bytes(encoded(closure))
            variants.append(dict(label=label, manifest=label + '-manifest.json',
                                 treeSHA256=hashlib.sha256(encoded(closure)).hexdigest()))
            target = BUILD / (label + '-target')
            args = ['cargo', 'test', '--locked', '--offline', '--no-run', '--message-format=json', '--lib', *flags]
            if profile == 'release':
                args += ['--release']
            built = command(label + '-build', args, vm, target, closure)
            artifacts = []
            for line in built.splitlines():
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if item.get('reason') == 'compiler-artifact' and item.get('executable') and item.get('profile', {}).get('test'):
                    artifacts.append(Path(item['executable']))
            assert len(artifacts) == 1
            binary = artifacts[0]
            listed = command(label + '-list', [str(binary), '--list'], vm, target, closure)
            identity = 'experimental::execution::borrowed::control_preflight::control_adapter_transfer_accounting_probe'
            assert identity + ': test' in listed.splitlines()
            output = command(label + '-probe', [str(binary), identity, '--exact', '--nocapture', '--test-threads=1'], vm, target, closure)
            assert re.search(r'test result: ok\. 1 passed; 0 failed; 0 ignored;', output)
            lines = [line[line.index('control_'):] for line in output.splitlines()
                     if 'control_accounting ' in line or 'control_transfer_position ' in line]
            assert len(lines) == 4, lines
            measurements.append(dict(configuration=label, records=lines,
                                     metadataOnly=True, guestExecution=False))
            binaries.append(dict(configuration=label, path=str(binary), sha256=sha(binary),
                                 executedTest=identity, testListCommand=label + '-list',
                                 runCommand=label + '-probe'))
    assert all(item['records'] == measurements[0]['records'] for item in measurements)
    status = 'rejected-chosen-fallible-control-transfer-inventory'
finally:
    unchanged = all(sha(ROOT / 'vm' / name) == digest for name, digest in source.items())
    receipt = dict(schema=1, status=status, sourceRevision=locals().get('revision'),
                   sourceTreeSHA256=hashlib.sha256(encoded(source)).hexdigest(),
                   sourceFiles=len(source), sourceArchiveSHA256=sha(OUT / 'source.tar.gz'),
                   productVMUnchanged=unchanged, rootFreezeSHA256=sha(freeze),
                   commands=commands, variants=variants, binaries=binaries, measurements=measurements,
                   implementationApplied=False, productTestsExecuted=False,
                   metadataProbeExecutions=len(measurements), nativeRuntimeExecuted=False,
                   computerUsePerformed=False,
                   limitation='Necessary transfer subset only; no complete inventory or semantic acceptance.')
    (OUT / 'receipt.json').write_bytes(encoded(receipt))
    print(str(OUT), flush=True)
    assert unchanged
