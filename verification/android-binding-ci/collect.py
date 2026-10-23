#!/usr/bin/env python3
"""Preserve and bind the three fresh-source host qualifications."""
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'verification/android-binding-ci'
OUT = BASE / 'qualified-1'
RUNNER = ROOT / 'scripts/ci/check-android-binding.py'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    OUT.mkdir(exist_ok=False)
    specification = importlib.util.spec_from_file_location('host_runner', RUNNER)
    runner = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(runner)
    files = {}
    bindings = 0
    receipts = {}
    baseline = None
    inputs = None

    def preserve(source, relative):
        destination = OUT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        require(digest(source) == digest(destination), 'Copy changed: ' + relative)
        files[str(destination.relative_to(ROOT))] = digest(destination)

    for mode in ['debug', 'release', 'tsan']:
        build = BASE / '.build' / (mode + '-3')
        receipt = json.loads((build / 'receipt.json').read_text())
        require(receipt['status'] == 'passed' and receipt['mode'] == mode, 'Incomplete mode: ' + mode)
        require(receipt['cases_executed'] == runner.SCENARIOS, 'Scenario set changed: ' + mode)
        require(receipt['runner_sha256'] == digest(RUNNER), 'Runner source changed')
        for relative, expected in receipt['input_files'].items():
            require(digest(ROOT / relative) == expected, 'Current input changed: ' + relative)
            bindings += 1
        for relative, expected in receipt['source_files'].items():
            require(digest(build / 'source' / relative) == expected, 'Frozen source changed: ' + relative)
            bindings += 1
        for path, expected in receipt['native_inputs'].items():
            require(digest(Path(path)) == expected, 'Native input changed: ' + path)
            bindings += 1
        require(digest(Path(receipt['native_receipt'])) == receipt['native_receipt_sha256'], 'Native receipt changed')
        require(digest(Path(receipt['executable']['path'])) == receipt['executable']['sha256'], 'Executable changed')
        names = set()
        for command in receipt['commands']:
            require(command['exit'] == 0, 'Command failed: ' + command['name'])
            require(command['name'] not in names, 'Duplicate command/log name')
            names.add(command['name'])
            require(digest(Path(command['log'])) == command['sha256'], 'Command log changed')
            preserve(Path(command['log']), mode + '/logs/' + command['name'] + '.log')
            bindings += 1
        if baseline is None:
            baseline, inputs = receipt, receipt['input_files']
        else:
            for field in ['input_files', 'source_files', 'native_inputs', 'dependency_checkouts', 'native_receipt_sha256']:
                require(receipt[field] == baseline[field], 'Modes used different ' + field)
        preserve(build / 'receipt.json', mode + '/receipt.json')
        receipts[mode] = str((OUT / mode / 'receipt.json').relative_to(ROOT))

    preserve(Path(baseline['native_receipt']), 'native-receipt.json')
    archive = OUT / 'source.tar.gz'
    source = BASE / '.build/debug-3/source'
    with archive.open('wb') as file:
        with gzip.GzipFile(filename='', mode='wb', fileobj=file, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as tar:
                for relative in sorted(baseline['source_files']):
                    info = tar.gettarinfo(str(source / relative), arcname=relative)
                    info.uid = info.gid = 0
                    info.uname = info.gname = ''
                    info.mtime = 0
                    with (source / relative).open('rb') as content:
                        tar.addfile(info, content)
    files[str(archive.relative_to(ROOT))] = digest(archive)
    commands = []
    for name, argv in [
        ('python-version', [sys.executable, '--version']),
        ('ci-tests', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'scripts/ci/tests', '-v']),
        ('optimized-ci-tests', [sys.executable, '-B', '-O', '-m', 'unittest', 'discover', '-s', 'scripts/ci/tests', '-v']),
        ('workflow-parse', ['ruby', '-rpsych', '-e', 'p Psych.load_file(".github/workflows/verify.yml")["jobs"]["swift"]["steps"].map { |s| s["name"] }.compact.last(4)']),
        ('policy', [sys.executable, '-B', 'scripts/check-policy.py']),
    ]:
        result = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        log = OUT / (name + '.log')
        log.write_bytes(result.stdout)
        files[str(log.relative_to(ROOT))] = digest(log)
        commands.append({'name': name, 'argv': argv, 'cwd': str(ROOT), 'exit': result.returncode,
                         'log': str(log.relative_to(ROOT)), 'sha256': digest(log)})
        require(result.returncode == 0, 'Qualification command failed: ' + name)
    inputs = dict(inputs)
    for relative in ['scripts/ci/check-android-binding.py', 'scripts/ci/tests/test_android_binding_runner.py',
                     '.github/workflows/verify.yml', 'verification/android-binding-ci/collect.py', 'THIRD_PARTY.yml']:
        inputs[relative] = digest(ROOT / relative)
    receipt = {
        'observed_utc': datetime.now(timezone.utc).isoformat(), 'status': 'passed',
        'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'platform': platform.platform(), 'inputs': inputs, 'source_tree_sha256': baseline['source_tree_sha256'],
        'verified_bindings': bindings, 'receipts': receipts, 'artifacts': files, 'commands': commands,
        'scenario_count_per_mode': len(runner.SCENARIOS), 'modes': ['debug', 'release', 'tsan'],
        'dependency_checkouts': baseline['dependency_checkouts'],
        'native_source_revision': baseline['native_source_revision'],
        'scope': 'Fresh actual Swift/C host builds and ordinary ownership scenarios; exact native archive and clean pinned dependency checkouts are bound. CI runner fail-closed checks also pass under optimized Python.',
        'limits': 'No literal 32-case debugger matrix qualification, JNI/Looper/widget/draw/physical-device execution, native evidence authority, signed core integration, immutable release or GA pass. The supplied Rust archive was built separately and is not TSan instrumented. Hosted pinned Swift 6.2.4 execution of this new step remains pending.',
    }
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'receipt': str((OUT / 'receipt.json').relative_to(ROOT)),
                      'bindings': bindings, 'scenarios_per_mode': len(runner.SCENARIOS),
                      'artifact_count': len(files)}))


if __name__ == '__main__':
    main()
