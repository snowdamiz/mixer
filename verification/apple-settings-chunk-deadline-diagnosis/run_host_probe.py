"""Finite host Foundation serialization probe; owned scratch always removed."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import time

BASE = pathlib.Path(__file__).resolve().parent
COMPILER = pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc')
SDK = '/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
SCRATCH = BASE / 'owned-host-scratch'


def main():
    SCRATCH.mkdir(exist_ok=False)
    commands = []
    passed = False

    def run(argv, name, timeout):
        start = time.monotonic()
        result = subprocess.run(argv, capture_output=True, timeout=timeout, cwd=BASE)
        (BASE / (name + '.stdout')).write_bytes(result.stdout)
        (BASE / (name + '.stderr')).write_bytes(result.stderr)
        commands.append({'argv': argv, 'exitCode': result.returncode,
            'elapsedSeconds': time.monotonic() - start,
            'stdoutSHA256': hashlib.sha256(result.stdout).hexdigest(),
            'stderrSHA256': hashlib.sha256(result.stderr).hexdigest()})
        if result.returncode:
            raise RuntimeError(name + ' failed; retained command/output')
        return result

    try:
        run([str(COMPILER), '--version'], 'swift-version', 15)
        run([str(COMPILER), '-sdk', SDK, '-target', 'arm64-apple-macosx26.0',
            '-module-cache-path', str(SCRATCH / 'module-cache'),
            str(BASE / 'serialization_probe.swift'), '-o', str(SCRATCH / 'serialization-probe')], 'host-compile', 45)
        output = run([str(SCRATCH / 'serialization-probe')], 'serialization-probe', 15)
        document = json.loads(output.stdout)
        assert len(document['rows']) == 41
        (BASE / 'serialization-probe.json').write_bytes(output.stdout)
        passed = True
    finally:
        shutil.rmtree(SCRATCH)
        receipt = {'schema': 1, 'python': sys.version, 'passed': passed,
            'sourceSHA256': hashlib.sha256((BASE / 'serialization_probe.swift').read_bytes()).hexdigest(),
            'runnerSHA256': hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
            'compilerSHA256': hashlib.sha256(COMPILER.read_bytes()).hexdigest(),
            'commands': commands, 'ownedScratchAbsent': not SCRATCH.exists(),
            'scope': 'One finite Foundation host serializer executable; no native product/client/runtime code, listener/device/UI/process inventory'}
        (BASE / 'host-command-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'passed': passed, 'rows': 41, 'ownedScratchAbsent': not SCRATCH.exists()}))


if __name__ == '__main__':
    main()
