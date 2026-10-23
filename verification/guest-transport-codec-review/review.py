#!/usr/bin/env python3
"""Independent public-API review of an immutable guest transport codec commit."""
import datetime
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
COMMIT = 'c8bb3bcb37076e6c05a4de6cafe342b57018b59e'
FROZEN = '3ba601332dab7c2aba98d7a50d7f0e893b1ea776'
CONTRACT_SHA = '052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439'
SOURCE_SHA = 'd144534e28ac463b5cb500fc5a64b9bda6109cfa422a200d99191e917ed993b3'
PATHS = ['sdk', 'capabilities', 'contracts/guest-capability-transport-v1.json', 'verification/guest-capability-contract']


def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)


def execute(name, args, cwd, scope):
    started = stamp()
    result = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    path = OUT / (name + '.log')
    path.write_bytes(result.stdout)
    record = {'name': name, 'command': args, 'cwd': str(cwd), 'started_at': started, 'ended_at': stamp(),
              'exit_code': result.returncode, 'output': str(path.relative_to(ROOT)), 'output_sha256': sha(result.stdout), 'scope': scope}
    print(name + ': ' + str(result.returncode), flush=True)
    return record


def source_manifest(source, entries):
    records = []
    for entry in entries:
        path = source / entry['path']
        data = path.read_bytes()
        assert len(data) == entry['bytes'] and sha(data) == entry['sha256'], entry['path']
        assert data == git('show', COMMIT + ':' + entry['path']), entry['path']
        records.append({'path': entry['path'], 'bytes': len(data), 'sha256': sha(data)})
    assert sha(canonical(records)) == SOURCE_SHA
    return {'digest': SOURCE_SHA, 'files': records}


def audit_receipts(source, implementation):
    records = []
    for command in implementation['commands'] + implementation['tools']:
        content = (source / command['output']).read_bytes()
        assert sha(content) == command['output_sha256'], command['name']
        assert command['exit_code'] == command['expected_exit_code'] == 0 and command['matched'], command['name']
        records.append({'name': command['name'], 'command': command['command'], 'scope': command['scope'],
                        'log_sha256': sha(content), 'exit_code': command['exit_code']})
    assert implementation['source_unchanged_during_run'] and implementation['scoped_checks_passed']
    cases = json.loads((source / 'verification/guest-capability-contract/cases.json').read_text())
    case_map = {case['id']: case for case in cases['cases']}
    assert len(case_map) == 90
    bindings = {item['swiftCase']: item for item in cases['operations']}
    audited_runs = []
    for run in implementation['fixture_runs']:
        raw = (source / run['raw_outputs']).read_bytes()
        assert sha(raw) == run['raw_outputs_sha256']
        observations = [json.loads(line) for line in raw.splitlines()]
        assert len(observations) == 90 and {x['id'] for x in observations} == set(case_map)
        accepted = rejected = 0
        for observed in observations:
            case = case_map[observed['id']]
            fixture = (source / 'verification/guest-capability-contract' / case['file']).read_bytes()
            assert sha(fixture) == case['sha256'] == observed['fixture_sha256'] and len(fixture) == case['bytes']
            data = fixture
            if case['phase'] == 'outcomes':
                binding = bindings[case['operation']]
                header = {'abi': 1, 'capability': binding['capability'], 'schemaHash': binding['schemaHash'], 'operation': binding['operation']}
                data = json.dumps(header, separators=(',', ':')).encode()[:-1] + b',"outcome":' + fixture + b'}'
            assert sha(data) == observed['stdin_sha256'] and len(data) == observed['stdin_bytes']
            stdout, stderr = observed['stdout_utf8'].encode(), observed['stderr_utf8'].encode()
            assert sha(stdout) == observed['stdout_sha256'] and sha(stderr) == observed['stderr_sha256']
            assert len(stdout) <= 524288 and len(stderr) <= 8192
            expected = 0 if case['expected'] == 'accept' else 1
            assert observed['exit_code'] == expected
            if expected == 0:
                assert json.loads(stdout) == json.loads(data)
                accepted += 1
            else:
                assert not stdout and stderr == b'guest transport probe rejected input\n'
                rejected += 1
            assert observed['matched'] and observed['output_bounded']
        audited_runs.append({'configuration': run['configuration'], 'total': 90, 'accepted': accepted, 'rejected': rejected,
                             'matched': 90, 'raw_outputs_sha256': sha(raw), 'audit': 'exact fixture/stdin/stdout/stderr bytes and independent expected exits checked; actual execution reused'})
    return records, audited_runs


def native_hash(base, omit_new=False):
    files = {}
    for folder in [base / 'sdk/Sources/MixerCapabilities', base / 'capabilities/java/mixer/capabilities']:
        for path in folder.rglob('*'):
            if path.is_file() and path.name not in ['GeneratedIdentity.swift', 'CapabilityNativeIdentity.java', 'CapabilityProbe.java']:
                if omit_new and path.name == 'GeneratedGuestTransport.swift': continue
                files[str(path.relative_to(base))] = path.read_bytes()
    files['capabilities/schema/v1.json'] = canonical(json.loads((base / 'capabilities/schema/v1.json').read_text()))
    return sha(canonical([{'path': path, 'sha256': sha(data)} for path, data in sorted(files.items())]))


def generate_review(source, base):
    destination = base / 'generation'
    for relative in ['sdk/Sources/MixerCapabilities', 'capabilities/java/mixer/capabilities']:
        shutil.copytree(source / relative, destination / relative)
    for relative in ['capabilities/tools/generate.py', 'capabilities/schema/v1.json']:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
    for relative in ['sdk/Sources/MixerCapabilities/GeneratedGuestTransport.swift', 'sdk/Sources/MixerCapabilities/GeneratedIdentity.swift',
                     'capabilities/java/mixer/capabilities/CapabilityNativeIdentity.java']:
        (destination / relative).unlink()
    commands = [execute('generator-first-independent', ['python3', 'capabilities/tools/generate.py'], destination,
                        'First generation with new output and both native identity outputs absent in separate small source copy')]
    assert commands[-1]['exit_code'] == 0
    expected = json.loads((source / 'capabilities/schema/hashes.json').read_text())['nativeImplementationSHA256']
    generated = json.loads((destination / 'capabilities/schema/hashes.json').read_text())['nativeImplementationSHA256']
    assert generated == expected == native_hash(destination)
    assert generated != native_hash(destination, True)
    def manifest(): return {str(p.relative_to(destination)): sha(p.read_bytes()) for p in destination.rglob('*') if p.is_file()}
    first = manifest()
    commands.append(execute('generator-repeat-independent', ['python3', 'capabilities/tools/generate.py'], destination, 'Repeat generation must preserve all copied/generated source bytes'))
    assert commands[-1]['exit_code'] == 0 and first == manifest()
    commands.append(execute('generator-check-independent', ['python3', 'capabilities/tools/generate.py', '--check'], destination, 'Independent copied-tree generated drift check'))
    assert commands[-1]['exit_code'] == 0
    for relative in first:
        assert (destination / relative).read_bytes() == (source / relative).read_bytes(), relative
    return commands, {'native_hash': generated, 'omitting_new_output_hash': native_hash(destination, True), 'first_repeat_and_export_exact': True}


def main():
    location = OUT / 'export-location.json'
    if location.exists():
        base = Path(json.loads(location.read_text())['temporary_directory'])
        source = base / 'source'
        assert source.exists()
    else:
        base = Path(tempfile.mkdtemp(prefix='mixer-guest-codec-review-'))
        source = base / 'source'; source.mkdir()
        archive = git('archive', COMMIT, *PATHS)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar: tar.extractall(source, filter='data')
    implementation = json.loads((source / 'capabilities/verification/guest-transport-codec/receipt.json').read_text())
    before = source_manifest(source, implementation['source']['files'])
    (OUT / 'implementation-source-manifest.json').write_text(json.dumps(before, indent=2) + '\n')
    preserved = []
    for entry in implementation['frozen_preservation']['files']:
        data = (source / entry['path']).read_bytes()
        assert data == git('show', FROZEN + ':' + entry['path'])
        preserved.append({'path': entry['path'], 'sha256': sha(data), 'matches_frozen': True})
    assert sha((source / 'contracts/guest-capability-transport-v1.json').read_bytes()) == CONTRACT_SHA
    audited_commands, audited_fixtures = audit_receipts(source, implementation)
    commands, generation = generate_review(source, base)
    review = base / 'review'
    (review / 'Tests').mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT / 'ReviewPackage.swift', review / 'Package.swift')
    shutil.copy2(OUT / 'PublicCodecReviewTests.swift', review / 'Tests/PublicCodecReviewTests.swift')
    for configuration in ['debug', 'release']:
        commands.append(execute('independent-public-' + configuration,
                                ['swift', 'test', '--package-path', str(review), '-c', configuration, '-Xswiftc', '-warnings-as-errors'],
                                base, 'Independently authored external-public-import tests against exact Git export; no @testable or mutable SDK'))
    unchanged = before == source_manifest(source, implementation['source']['files'])
    tools = [execute('version-swift', ['swift', '--version'], base, 'Observed host Swift compiler'),
             execute('version-python', ['python3', '--version'], base, 'Observed review runner Python'),
             execute('version-git', ['git', '--version'], ROOT, 'Observed immutable export Git tool')]
    passed = unchanged and all(c['exit_code'] == 0 for c in commands + tools)
    review_sources = {name: sha((OUT / name).read_bytes()) for name in ['ReviewPackage.swift', 'PublicCodecReviewTests.swift', 'review.py']}
    receipt = {'schema': 1, 'created_at': stamp(), 'reviewed_commit': COMMIT, 'reviewed_tree': git('rev-parse', COMMIT + '^{tree}').decode().strip(),
               'source': before, 'source_unchanged_during_review': unchanged, 'review_source_sha256': review_sources,
               'fixed_contract': {'commit': FROZEN, 'sha256': CONTRACT_SHA, 'preserved_files': preserved},
               'implementation_receipt_audit': {'receipt_sha256': sha((source / 'capabilities/verification/guest-transport-codec/receipt.json').read_bytes()),
                                                'commands': audited_commands, 'fixture_runs': audited_fixtures, 'cross_builds_reused_and_audited': True,
                                                'original_precommit_revision': implementation['source_revision'], 'linked_to_reviewed_commit_by_exact_source_digest': True},
               'independent_generator': generation, 'commands': commands, 'tools': tools, 'scoped_checks_passed': passed,
               'findings': [], 'scope': 'Independent value-codec public API/source/evidence review only. No VM/import/native bridge/C/activation/release/device/Swift async qualification.',
               'limitations': ['Existing 90-fixture debug/release execution and iOS/Android/WASI compilation receipts audited byte-for-byte and reused, not rerun',
                               'Independent tests run only on macOS and are not exhaustive fuzzing, constant-time, allocation-bound or physical-device proof',
                               'Frozen wrapper contract remains development-only; value acceptance including HTTP3xx/false commit/found=false payload is not native policy or effects approval',
                               'Legacy malformed-data error behavior remains unchanged; new public decoding boundaries expose sanitized CapabilityWireError',
                               'Independent lane authored public tests and review evidence only; no implementation edits, device commands or publication'],
               'temporary_export_destroyed': passed}
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'scoped_checks_passed': passed, 'source_unchanged': unchanged, 'reviewed_commit': COMMIT, 'source_digest': SOURCE_SHA}), flush=True)
    if passed:
        shutil.rmtree(base)
        location.unlink(missing_ok=True)
    return 0 if passed else 1


if __name__ == '__main__': raise SystemExit(main())
