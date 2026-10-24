#!/usr/bin/env python3
"""Isolated macro expansion/type/layout proposal. Never edits product source."""
from pathlib import Path
import datetime
import hashlib
import json
import os
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
METHODS = ['pop32', 'close_control', 'branch']


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def method(text, name):
    start = text.index('fn ' + name + '(')
    body = text.index('{', start)
    depth = 1
    end = body + 1
    # These three exact bodies have no brace-bearing strings/comments. Expanded
    # methods are separately emitted by rustc, not inferred from this scanner.
    while depth:
        char = text[end]
        depth += (char == '{') - (char == '}')
        end += 1
    return text[start:end]


def apply_macro(vm):
    owner = vm / 'src/experimental/execution/mod.rs'
    text = owner.read_text()
    original = {name: method(text, name) for name in METHODS}
    macro = (OUT / 'inputs/frozen_control_methods.rs').read_text()
    for name in METHODS:
        # Whitespace-only difference from indentation is checked here as an
        # input guard. Actual compiler expansion equality is checked later.
        assert ''.join(method(macro, name).split()) == ''.join(original[name].split())
        replacement = 'borrowed::frozen_control_methods!();' if name == 'pop32' else ''
        text = text.replace(original[name], replacement, 1)
    owner.write_text(text)
    borrowed = vm / 'src/experimental/execution/borrowed.rs'
    borrowed.write_text(borrowed.read_text() + '\n' + macro)


files = [ROOT / 'vm/Cargo.toml', ROOT / 'vm/Cargo.lock']
for directory in ['src', 'tests', 'include']:
    files += sorted(p for p in (ROOT / 'vm' / directory).rglob('*') if p.is_file())
source = {str(p.relative_to(ROOT / 'vm')): sha(p) for p in files}
(OUT / 'source-manifest.json').write_bytes(encoded(source))
with tarfile.open(OUT / 'source.tar.gz', 'w:gz') as archive:
    for path in files:
        archive.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
(OUT / 'inputs').mkdir()
for name in ['collect.py', 'frozen_control_methods.rs', 'layout_probe.rs']:
    (OUT / 'inputs' / name).write_bytes((HERE / name).read_bytes())
prior_seal = ROOT / 'verification/swift-control-extraction/seal.json'
(OUT / 'inputs/prior-rejection-seal.json').write_bytes(prior_seal.read_bytes())
prior = json.loads(prior_seal.read_text())
for name, digest in prior['bindings'].items():
    assert sha(ROOT / name) == digest, 'prior rejection changed: ' + name
commands = []
variants = []
expansions = []
layouts = []
binaries = []
negatives = []
status = 'failed-preflight'


def command(name, argv, cwd, target=None, closure=None, bootstrap=False, expected_error=None):
    if closure is not None:
        assert manifest(cwd) == closure, 'source changed before ' + name
    env = dict(ENV)
    if target is not None:
        env['CARGO_TARGET_DIR'] = str(target)
    if bootstrap:
        # Only compiler pretty-print expansion diagnostics use this process-local
        # flag. Ordinary compile/layout/negative checks do not enable it.
        env['RUSTC_BOOTSTRAP'] = '1'
    else:
        env.pop('RUSTC_BOOTSTRAP', None)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    run = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=600)
    stdout = OUT / (name + '.stdout')
    stderr = OUT / (name + '.stderr')
    stdout.write_bytes(run.stdout)
    stderr.write_bytes(run.stderr)
    if closure is not None:
        assert manifest(cwd) == closure, 'source changed after ' + name
    entry = dict(name=name, argv=argv, cwd=str(cwd), target=str(target) if target else None,
                 exitCode=run.returncode, diagnosticBootstrap=bootstrap,
                 stdout=stdout.name, stdoutSHA256=sha(stdout),
                 stderr=stderr.name, stderrSHA256=sha(stderr),
                 startedUTC=started, completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 sourceBeforeAfterVerified=closure is not None, expectedError=expected_error)
    commands.append(entry)
    print(name, run.returncode, flush=True)
    if expected_error:
        assert run.returncode != 0, name
        codes = []
        for line in run.stdout.decode().splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            code = item.get('message', {}).get('code') or {}
            if code.get('code'):
                codes.append(code['code'])
        assert expected_error in codes, (expected_error, codes)
        negatives.append(dict(name=name, expectedError=expected_error, actualCodes=codes))
    else:
        assert run.returncode == 0, (run.stdout + run.stderr).decode(errors='replace')[-6000:]
    return run.stdout.decode()


def extract(label, candidate=False):
    destination = BUILD / label
    with tarfile.open(OUT / 'source.tar.gz') as archive:
        archive.extractall(destination, filter='data')
    vm = destination / 'vm'
    if candidate:
        apply_macro(vm)
    return vm


def save_variant(label, vm):
    closure = manifest(vm)
    name = label + '-manifest.json'
    (OUT / name).write_bytes(encoded(closure))
    variants.append(dict(name=label, manifest=name,
                         treeSHA256=hashlib.sha256(encoded(closure)).hexdigest()))
    return closure


try:
    revision = command('revision', ['git', 'rev-parse', 'HEAD'], ROOT).strip()
    command('rustc-version', ['rustc', '-vV'], ROOT)
    command('cargo-version', ['cargo', '-V'], ROOT)
    command('python-version', ['python3', '--version'], ROOT)
    accepted = json.loads((ROOT / 'verification/swift-value-operations-root-review/acceptance.json').read_text())
    assert hashlib.sha256(encoded(source)).hexdigest() == accepted['sourceTreeSHA256']
    # Exact compiler-expanded inherent methods, separate from metadata probes.
    original_methods = {}
    for candidate in [False, True]:
        variant = 'candidate' if candidate else 'baseline'
        vm = extract(variant + '-expansion', candidate)
        closure = save_variant(variant + '-expansion', vm)
        for config, flags in [('span', ['--features', 'experimental-span-execution']), ('all', ['--all-features'])]:
            for profile in ['debug', 'release']:
                label = variant + '-' + config + '-' + profile + '-expansion'
                args = ['cargo', 'rustc', '--locked', '--offline', '--lib', *flags]
                if profile == 'release':
                    args += ['--release']
                args += ['--', '-Zunpretty=expanded']
                output = command(label, args, vm, BUILD / (label + '-target'), closure, bootstrap=True)
                owner = output[output.index('impl SpanInstance {'):]
                methods = {name: method(owner, name) for name in METHODS}
                (OUT / (label + '-methods.json')).write_bytes(encoded(methods))
                if not candidate:
                    original_methods[(config, profile)] = methods
                else:
                    assert methods == original_methods[(config, profile)], label
                expansions.append(dict(label=label, methods=label + '-methods.json',
                                       methodHashes={name: hashlib.sha256(text.encode()).hexdigest() for name, text in methods.items()},
                                       baselineEqual=True if candidate else None))
    # Real stable-mode type checks use no bootstrap and no probe modifications.
    vm = extract('candidate-check', True)
    closure = save_variant('candidate-check', vm)
    for config, flags in [('default', []), ('span', ['--features', 'experimental-span-execution']),
                          ('swift', ['--features', 'experimental-swift-reactor']), ('all', ['--all-features'])]:
        for profile in ['debug', 'release']:
            label = 'candidate-' + config + '-' + profile + '-check'
            args = ['cargo', 'check', '--locked', '--offline', '--lib', *flags]
            if profile == 'release':
                args += ['--release']
            command(label, args, vm, BUILD / (label + '-target'), closure)
    # Baseline/candidate production and unit metadata use identical probes.
    for candidate in [False, True]:
        variant = 'candidate' if candidate else 'baseline'
        vm = extract(variant + '-layout', candidate)
        owner = vm / 'src/experimental/execution/mod.rs'
        owner.write_text(owner.read_text() + '\n' + (OUT / 'inputs/layout_probe.rs').read_text())
        lib = vm / 'src/lib.rs'
        lib.write_text(lib.read_text() + '\n#[cfg(feature="experimental-span-execution")] pub fn control_macro_layout_probe(){experimental::execution::control_macro_layout_probe();}\n')
        (vm / 'examples').mkdir(exist_ok=True)
        (vm / 'examples/control-macro-layout.rs').write_text('fn main(){mixer_vm::control_macro_layout_probe();}\n')
        closure = save_variant(variant + '-layout', vm)
        for config, flags in [('span', ['--features', 'experimental-span-execution']), ('all', ['--all-features'])]:
            for profile in ['debug', 'release']:
                for mode in ['production', 'unit']:
                    label = variant + '-' + config + '-' + profile + '-' + mode + '-layout'
                    args = ['cargo', 'build', '--locked', '--offline', '--message-format=json', '--example', 'control-macro-layout', *flags] if mode == 'production' else ['cargo', 'test', '--locked', '--offline', '--no-run', '--message-format=json', '--lib', *flags]
                    if profile == 'release':
                        args += ['--release']
                    target = BUILD / (label + '-target')
                    output = command(label + '-build', args, vm, target, closure)
                    artifacts = []
                    for line in output.splitlines():
                        try:
                            item = json.loads(line)
                        except ValueError:
                            continue
                        if item.get('reason') == 'compiler-artifact' and item.get('executable'):
                            if mode == 'production' or item.get('profile', {}).get('test'):
                                artifacts.append(Path(item['executable']))
                    assert len(artifacts) == 1, (label, artifacts)
                    binary = artifacts[0]
                    if mode == 'unit':
                        identity = 'experimental::execution::control_macro_layout_only'
                        listed = command(label + '-list', [str(binary), '--list'], vm, target, closure)
                        assert identity + ': test' in listed.splitlines()
                        args = [str(binary), identity, '--exact', '--nocapture', '--test-threads=1']
                    else:
                        identity = None
                        args = [str(binary)]
                    output = command(label + '-run', args, vm, target, closure)
                    records = []
                    for line in output.splitlines():
                        for marker in ['control_macro_type ', 'control_macro_offset ', 'control_macro_reservation ']:
                            at = line.find(marker)
                            if at >= 0:
                                records.append(line[at:])
                                break
                    assert len(records) == 66, (label, len(records))
                    binaries.append(dict(label=label, path=str(binary), sha256=sha(binary),
                                         executedTest=identity, metadataOnly=True, runCommand=label + '-run',
                                         listCommand=label + '-list' if identity else None))
                    layouts.append(dict(label=label, records=records))
    assert all(item['records'] == layouts[0]['records'] for item in layouts)
    # Downstream code gets neither an exported macro nor newly accessible methods.
    for name, body, error in [
        ('private-macro', 'mixer_vm::frozen_control_methods!();\nfn main(){}\n', 'E0433'),
        ('private-method', 'use mixer_vm::experimental::execution::SpanInstance;\nfn main(){let _ = SpanInstance::branch;}\n', 'E0624'),
    ]:
        vm = extract(name, True)
        (vm / 'src/bin').mkdir(exist_ok=True)
        (vm / 'src/bin/macro-privacy-probe.rs').write_text(body)
        closure = save_variant(name, vm)
        command(name, ['cargo', 'check', '--locked', '--offline', '--features', 'experimental-span-execution',
                       '--bin', 'macro-privacy-probe', '--message-format=json'], vm,
                BUILD / (name + '-target'), closure, expected_error=error)
    status = 'macro-proposal-expansion-layout-preflight-only'
finally:
    unchanged = all(sha(ROOT / 'vm' / name) == digest for name, digest in source.items())
    prior_unchanged = all(sha(ROOT / name) == digest for name, digest in prior['bindings'].items())
    receipt = dict(schema=1, status=status, sourceRevision=locals().get('revision'),
                   sourceTreeSHA256=hashlib.sha256(encoded(source)).hexdigest(), sourceFiles=len(source),
                   archiveSHA256=sha(OUT / 'source.tar.gz'), commands=commands, variants=variants,
                   expansions=expansions, layouts=layouts, binaries=binaries, negatives=negatives,
                   productVMUnchanged=unchanged, priorRejectionUnchanged=prior_unchanged,
                   implementationApplied=False, guestExecution=False, nativeRuntime=False,
                   semanticAcceptance=False, accountingCompletenessAccepted=False,
                   limitation='Compiler expansion/type/layout/privacy preflight only; semantic cases and independent accounting review pending.')
    (OUT / 'receipt.json').write_bytes(encoded(receipt))
    print(str(OUT), flush=True)
    assert unchanged and prior_unchanged
