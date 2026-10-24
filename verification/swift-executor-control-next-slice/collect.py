#!/usr/bin/env python3
"""Collect planning evidence only; no compilation, guest or native execution."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'results'


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vm_manifest():
    files = [ROOT / 'vm/Cargo.toml', ROOT / 'vm/Cargo.lock']
    for directory in ['src', 'tests', 'include']:
        files += sorted(p for p in (ROOT / 'vm' / directory).rglob('*') if p.is_file())
    return {str(p.relative_to(ROOT / 'vm')): sha(p) for p in files}


def main():
    OUT.mkdir(exist_ok=False)
    manifest = vm_manifest()
    acceptance_path = ROOT / 'verification/swift-value-operations-root-review/acceptance.json'
    acceptance = json.loads(acceptance_path.read_text())
    for name, digest in manifest.items():
        assert acceptance['bindings']['vm/' + name] == digest, name
    tree = hashlib.sha256(encoded(manifest)).hexdigest()
    assert tree == acceptance['sourceTreeSHA256'], tree
    (OUT / 'vm-source-manifest.json').write_bytes(encoded(manifest))
    env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'])
    commands = []
    revision = None
    for name, argv in [
        ('revision', ['git', 'rev-parse', 'HEAD']),
        ('rustc-version', ['rustc', '-vV']),
        ('cargo-version', ['cargo', '-V']),
        ('python-version', ['python3', '--version']),
    ]:
        before = vm_manifest()
        run = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=30)
        log = OUT / (name + '.log')
        log.write_bytes(run.stdout + run.stderr)
        assert run.returncode == 0, name
        assert before == manifest == vm_manifest(), name
        commands.append(dict(argv=argv, cwd=str(ROOT), exitCode=run.returncode,
                             output=str(log.relative_to(HERE)), outputSHA256=sha(log),
                             vmSourceBeforeAfterVerified=True))
        if name == 'revision':
            revision = run.stdout.decode().strip()
    inputs = [
        'AGENTS.md', 'mixer-product-plan.md',
        'docs/swift-shared-executor-algorithm-contract.md',
        'docs/swift-executor-stage-contract.md',
        'docs/swift-executor-operations.md',
        'docs/swift-executor-construction-acceptance.md',
        'docs/swift-value-operations-independent-review.md',
        'verification/swift-shared-executor-algorithm-contract/root-acceptance.json',
        'verification/swift-value-operations-root-review/acceptance.json',
        'verification/computer-use-pause-2026-10-24/receipt.json',
        'docs/swift-executor-control-next-slice.md',
    ]
    bindings = {name: sha(ROOT / name) for name in inputs}
    for path in [HERE / 'collect.py', HERE / 'verify.py', HERE / 'matrix.json',
                 *sorted(OUT.iterdir())]:
        bindings[str(path.relative_to(ROOT))] = sha(path)
    receipt = dict(schema=1, status='planning-evidence-only',
                   observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   sourceRevision=revision, vmSourceTreeSHA256=tree,
                   vmSourceFiles=len(manifest), acceptedVMSourceBindingsMatch=True,
                   bindings=bindings, commands=commands,
                   proposedScope=['FrozenMode pop32', 'FrozenMode close_control', 'FrozenMode branch'],
                   rootFreeze='pending', productionChanged=False,
                   compilationPerformed=False, productTestsPerformed=False,
                   nativeRuntimePerformed=False, computerUsePerformed=False,
                   activeSwiftFrames='deferred; rejected-pin outcome requires later exact freeze',
                   limitations=['Planning packet integrity only; no semantic/accounting acceptance.',
                                'No target/native/device/published consumer/GA qualification.'])
    (OUT / 'receipt.json').write_bytes(encoded(receipt))
    print(json.dumps({k: receipt[k] for k in ['status', 'sourceRevision', 'vmSourceTreeSHA256',
                                             'vmSourceFiles', 'rootFreeze']}))


if __name__ == '__main__':
    main()
