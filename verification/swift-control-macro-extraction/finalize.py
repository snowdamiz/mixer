#!/usr/bin/env python3
"""Reconstruct preserved layout logs and finish missing privacy probes only."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = HERE / 'results/20261024T030635088702Z'
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = HERE / 'results' / STAMP
BUILD = HERE / 'build' / STAMP
OUT.mkdir(parents=True, exist_ok=False)
BUILD.mkdir(parents=True, exist_ok=False)
ENV = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'])
ENV.pop('RUSTC_BOOTSTRAP', None)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


saved = json.loads((BASE / 'receipt.json').read_text())
assert saved['status'] == 'failed-preflight'
assert saved['productVMUnchanged'] and saved['priorRejectionUnchanged']
assert len(saved['expansions']) == 8 and len(saved['binaries']) == 16
for command in saved['commands']:
    assert command['exitCode'] == 0
    assert sha(BASE / command['stdout']) == command['stdoutSHA256']
    assert sha(BASE / command['stderr']) == command['stderrSHA256']
for name in ['frozen_control_methods.rs', 'layout_probe.rs']:
    assert (HERE / name).read_bytes() == (BASE / 'inputs' / name).read_bytes()
assert sha(BASE / 'source.tar.gz') == saved['archiveSHA256']
source = json.loads((BASE / 'source-manifest.json').read_text())
for name, digest in source.items():
    assert sha(ROOT / 'vm' / name) == digest
layouts = []
for binary in saved['binaries']:
    assert sha(Path(binary['path'])) == binary['sha256']
    rows = []
    for line in (BASE / (binary['runCommand'] + '.stdout')).read_text().splitlines():
        for marker in ['control_macro_type ', 'control_macro_offset ', 'control_macro_reservation ']:
            at = line.find(marker)
            if at >= 0:
                rows.append(line[at:])
                break
    assert len(rows) == 66, binary['label']
    layouts.append(dict(label=binary['label'], records=rows))
assert all(item['records'] == layouts[0]['records'] for item in layouts)
(OUT / 'reconstructed-layouts.json').write_bytes(encoded(layouts))
(OUT / 'finalize.py').write_bytes(Path(__file__).read_bytes())
commands = []
negatives = []
variants = []
status = 'failed-finalization'
try:
    # Inherited expansion/type/layout commands are not rerun: their exact source,
    # output and binary hashes remain bound and independently reconstructible.
    for name, body, expected in [
        ('private-macro', 'mixer_vm::frozen_control_methods!();\nfn main(){}\n', 'E0433'),
        ('private-method', 'use mixer_vm::experimental::execution::SpanInstance;\nfn main(){let _ = SpanInstance::branch;}\n', 'E0624'),
    ]:
        with tarfile.open(BASE / 'source.tar.gz') as archive:
            archive.extractall(BUILD / name, filter='data')
        vm = BUILD / name / 'vm'
        owner = vm / 'src/experimental/execution/mod.rs'
        text = owner.read_text()
        for method_name in ['pop32', 'close_control', 'branch']:
            start = text.index('fn ' + method_name + '(')
            end = text.index('{', start) + 1
            depth = 1
            while depth:
                depth += (text[end] == '{') - (text[end] == '}')
                end += 1
            text = text[:start] + ('borrowed::frozen_control_methods!();' if method_name == 'pop32' else '') + text[end:]
        owner.write_text(text)
        borrowed = vm / 'src/experimental/execution/borrowed.rs'
        borrowed.write_text(borrowed.read_text() + '\n' + (BASE / 'inputs/frozen_control_methods.rs').read_text())
        (vm / 'src/bin').mkdir(exist_ok=True)
        (vm / 'src/bin/macro-privacy-probe.rs').write_text(body)
        closure = manifest(vm)
        manifest_name = name + '-manifest.json'
        (OUT / manifest_name).write_bytes(encoded(closure))
        variants.append(dict(name=name, manifest=manifest_name,
                             treeSHA256=hashlib.sha256(encoded(closure)).hexdigest()))
        argv = ['cargo', 'check', '--locked', '--offline', '--features', 'experimental-span-execution',
                '--bin', 'macro-privacy-probe', '--message-format=json']
        target = BUILD / (name + '-target')
        env = dict(ENV, CARGO_TARGET_DIR=str(target))
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        run = subprocess.run(argv, cwd=vm, env=env, capture_output=True, timeout=600)
        assert manifest(vm) == closure
        stdout = OUT / (name + '.stdout')
        stderr = OUT / (name + '.stderr')
        stdout.write_bytes(run.stdout)
        stderr.write_bytes(run.stderr)
        codes = []
        for line in run.stdout.decode().splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            code = item.get('message', {}).get('code') or {}
            if code.get('code'):
                codes.append(code['code'])
        commands.append(dict(name=name, argv=argv, cwd=str(vm), target=str(target),
                             exitCode=run.returncode, expectedError=expected, diagnosticBootstrap=False,
                             stdout=stdout.name, stdoutSHA256=sha(stdout),
                             stderr=stderr.name, stderrSHA256=sha(stderr),
                             startedUTC=started, completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                             sourceBeforeAfterVerified=True))
        assert run.returncode != 0 and expected in codes, (name, run.returncode, codes)
        negatives.append(dict(name=name, expectedError=expected, actualCodes=codes))
        print(name, run.returncode, codes, flush=True)
    status = 'macro-proposal-expansion-layout-privacy-preflight-only'
finally:
    unchanged = all(sha(ROOT / 'vm' / name) == digest for name, digest in source.items())
    prior = json.loads((ROOT / 'verification/swift-control-extraction/seal.json').read_text())
    prior_unchanged = all(sha(ROOT / name) == digest for name, digest in prior['bindings'].items())
    receipt = dict(schema=1, status=status, inheritedResults=str(BASE.relative_to(ROOT)),
                   inheritedReceiptSHA256=sha(BASE / 'receipt.json'),
                   sourceTreeSHA256=saved['sourceTreeSHA256'], sourceRevision=saved['sourceRevision'],
                   reconstructedLayouts='reconstructed-layouts.json',
                   reconstructedLayoutsSHA256=sha(OUT / 'reconstructed-layouts.json'),
                   sourceFiles=len(source), expandedMethodsCompared=12,
                   stableFeatureProfileChecks=8, layoutBinaries=16, layoutRecordsPerBinary=66,
                   metadataOnly=True, guestExecution=False, nativeRuntime=False,
                   implementationApplied=False, semanticAcceptance=False,
                   productVMUnchanged=unchanged, priorRejectionUnchanged=prior_unchanged,
                   commands=commands, negatives=negatives, variants=variants,
                   accounting='zero additional runtime objects/boundaries; delta map needs independent root review',
                   collectorHistory='Initial expected-row-count failure and subsequent test-name-prefix parsing failure remain unchanged. Finalization binds existing outputs and reconstructs rows by complete marker names; no source/build/binary output is replaced.')
    (OUT / 'receipt.json').write_bytes(encoded(receipt))
    print(str(OUT), flush=True)
    assert unchanged and prior_unchanged
