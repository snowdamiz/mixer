#!/usr/bin/env python3
"""Independent read-only path/hash audit of the bounded host checkpoint."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BINDINGS = {}
ERRORS = []
RECEIPTS = {}
COMMANDS = []
sha = lambda data: hashlib.sha256(data).hexdigest()

def require(value, message):
    if not value:
        ERRORS.append(message)

def bind(path, expected=None):
    path = ROOT / path
    label = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    try:
        actual = sha(path.read_bytes())
    except OSError as error:
        ERRORS.append(f'{label}: {error}')
        return None
    require(expected is None or actual == expected, f'Digest mismatch: {label}: {expected} != {actual}')
    BINDINGS[label] = actual
    return path

def read(path, expected=None):
    bound = bind(path, expected)
    return json.loads(bound.read_text()) if bound else {}

def receipt(path, expected=None):
    path = ROOT / path
    if str(path) in RECEIPTS:
        bind(path, expected)
        return RECEIPTS[str(path)]
    d = read(path, expected)
    RECEIPTS[str(path)] = d
    for field in ['artifacts', 'inputs', 'native_inputs', 'input_files']:
        for p, checksum in d.get(field, {}).items():
            if isinstance(checksum, str) and len(checksum) == 64 and '/' in p:
                bind(p, checksum)
    inputs = d.get('inputs', {})
    if 'driver' in inputs:
        bind(path.parent / 'debugger_driver.py', inputs['driver'])
    if 'launcher' in inputs:
        bind('verification/android-binding-stage4/debuggers.py', inputs['launcher'])
    if 'script' in inputs and 'symbols-' in str(path):
        bind('verification/android-binding-stage4/symbols.py', inputs['script'])
    if 'edge' in inputs:
        bind('verification/android-binding-stage4/SymbolEntry.swift', inputs['edge'])
    for command in d.get('commands', []):
        log = command.get('log', command.get('output'))
        checksum = command.get('sha256', command.get('log_sha256', command.get('output_sha256')))
        if log and checksum:
            bind(log, checksum)
        COMMANDS.append({'receipt': str(path.relative_to(ROOT)), 'name': command.get('name'),
                         'exit': command.get('exit'), 'expected_exit': command.get('expected_exit')})
    if d.get('reference'):
        receipt(d['reference'], d.get('reference_sha256'))
    if d.get('dependency_receipt'):
        dep = read(d['dependency_receipt'], d.get('dependency_receipt_sha256'))
        base = Path(dep['dylib']).parents[1]
        for p, checksum in d.get('dependency_artifacts', {}).items():
            bind(base / p, checksum)
    if d.get('source_files'):
        manifest = d['source_files']
        if 'source_tree_sha256' in d:
            require(sha(json.dumps(manifest, sort_keys=True).encode()) == d['source_tree_sha256'],
                    f'Manifest digest mismatch: {path}')
        # This is a receipt's retained source export, never a new build input.
        export = Path(d['commands'][-1].get('cwd', str(path.parent / 'source')))
        if export.name != 'source' and (path.parent / 'source').is_dir():
            export = path.parent / 'source'
        if (export / next(iter(manifest))).is_file():
            for p, checksum in manifest.items():
                bind(export / p, checksum)
    if d.get('executable'):
        bind(d['executable']['path'], d['executable']['sha256'])
    if d.get('native_receipt'):
        read(d['native_receipt'], d.get('native_receipt_sha256'))
    return d

def main():
    seals = {
        'verification/android-binding-stage4/evidence.json': 'b3e912c176710d23c4982efd400a78872e409e5c5a3f64da31716ca9898e16d3',
        'verification/android-binding-stage4/acceptance-results.json': '5b30ba43a716ae897ce906b073ec9ca28da5ac9e4fb944a9dc33dd1da5d641d9',
        'verification/android-binding-stage4/runs/release-repaired-2/receipt.json': '71c98da65fdb5c48122c3506314557bd9d60ad0e8f49109d92c21a4c0680b53c',
        'verification/android-binding-stage4-review/candidate-3/review.json': 'a0a1c31e5b7e19f377c02dbfc97cc082a3e450b59afac41296636cd6c03e8c4a',
        'verification/android-binding-ci/qualified-1/receipt.json': 'f1afd01d5e14084076ac20bcf23ff68abb3213d5d48e102f3c71c9f657d51efd',
    }
    for p, checksum in seals.items():
        bind(p, checksum)
    producer = read('verification/android-binding-stage4/evidence.json')
    acceptance = read('verification/android-binding-stage4/acceptance-results.json')
    canonical = receipt(producer['canonical_source_receipt'], producer['canonical_source_receipt_sha256'])
    require(canonical['source_tree_sha256'] == 'e8a6d021c7eb99db60391ba516870b6722c8307f5f331ad3f8a76999cb862645', 'Wrong canonical manifest')
    for field in ['product_and_fixed_fixture_files', 'contracts_and_separate_amendments', 'tooling_files']:
        for p, checksum in producer[field].items():
            bind(p, checksum)
    for p, value in producer['receipts'].items():
        receipt(p, value['sha256'])
    proofs = {}
    for name, value in producer['debugger_proofs'].items():
        d = read(value['path'], value['sha256'])
        require(d['result'] == 'passed' and d['exit'] == 0, 'Failed selected debugger proof: ' + name)
        launcher = receipt(value['launcher_receipt'])
        build = receipt(value['build_receipt'])
        for p, checksum in producer['product_and_fixed_fixture_files'].items():
            if p in build.get('source_files', {}):
                require(build['source_files'][p] == checksum, 'Wrong debugger product source: ' + name + ': ' + p)
        binary = d['binary']
        bind(binary, build.get('artifacts', {}).get(binary.removeprefix(str(ROOT) + '/')))
        proofs[name] = {'path': value['path'], 'event_points': [x['point'] for x in d['events']],
                        'binary': binary, 'stdout': d['stdout'], 'event_count': len(d['events'])}
    limited = producer['mode_limitations']['release/lifetime-exhaustion']
    failed = read(limited['failed_attempt'], limited['failed_attempt_sha256'])
    require(failed.get('result') != 'passed', 'Release failure must not be counted as pass')
    join = read('verification/android-binding-stage4-join-admission/acceptance.json')
    for p, checksum in join['bindings'].items():
        bind(p, checksum)
    ci = receipt(producer['root_fresh_source_CI']['path'], producer['root_fresh_source_CI']['sha256'])
    test_inputs = read('verification/android-binding-ci/qualified-1/test-inputs.json')
    require(test_inputs['receipt_sha256'] == seals['verification/android-binding-ci/qualified-1/receipt.json'], 'Wrong CI test-input parent')
    for p, checksum in test_inputs['files'].items():
        bind(p, checksum)
    archive = ROOT / 'verification/android-binding-ci/qualified-1/source.tar.gz'
    with tarfile.open(archive, 'r:gz') as tar:
        members = {m.name: sha(tar.extractfile(m).read()) for m in tar.getmembers() if m.isfile()}
    modes = {}
    for mode, p in ci['receipts'].items():
        d = receipt(p)
        require(members == d['source_files'], 'CI archive differs: ' + mode)
        require(d['status'] == 'passed' and len(d['cases_executed']) == 39, 'Incomplete CI mode: ' + mode)
        for cmd in d['commands']:
            require(cmd['exit'] == 0, 'CI command failed: ' + cmd['name'])
            if cmd['name'] in d['cases_executed']:
                require('HOST_PASS ' + cmd['name'] in (ROOT / cmd['log']).read_text().splitlines(), 'Wrong success marker: ' + cmd['name'])
        modes[mode] = {'manifest': d['source_tree_sha256'], 'case_count': len(d['cases_executed']),
                       'dependency_checkouts': d['dependency_checkouts']}
    require(not producer['full_original_dynamic_matrix_pass'] and not acceptance['full_original_dynamic_matrix_pass'], 'False full-matrix authority')
    result = {'observed_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
              'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'auditor_sha256': sha(Path(__file__).read_bytes()), 'status': 'passed' if not ERRORS else 'failed',
              'errors': ERRORS, 'binding_count': len(BINDINGS), 'bindings': BINDINGS,
              'receipt_count': len(RECEIPTS), 'commands': COMMANDS, 'debugger_proofs': proofs,
              'ci_modes': modes, 'producer_manifest': canonical['source_tree_sha256'],
              'scope': 'Read-only independent verification of sealed producer, join-delta and fresh CI retained artifacts. No scenario is described as newly executed by this path audit.'}
    (HERE / 'artifact-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['status', 'binding_count', 'receipt_count', 'errors']}))
    raise SystemExit(bool(ERRORS))

if __name__ == '__main__':
    main()
