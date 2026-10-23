#!/usr/bin/env python3
"""Recompile edited fixtures, reusing existing native/package products."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    commands = []
    record = {'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'commands': commands, 'scope': 'host fixture regression tests; existing package and activation dependency products reused'}

    def run(name, command, environment=None):
        command = [str(value) for value in command]
        result = subprocess.run(command, cwd=ROOT, env={**os.environ, **(environment or {})},
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = HERE / (name + '.log')
        log.write_text(result.stdout)
        commands.append({'name': name, 'command': command, 'environment': environment or {},
                         'exit_code': result.returncode, 'log': str(log.relative_to(ROOT)), 'log_sha256': sha(log)})
        print(name, result.returncode, flush=True)
        if result.returncode:
            raise RuntimeError(result.stdout)

    try:
        native = ROOT / 'experimental-capability-runtime/build-verification/local/guest-ui-1adb25c-v2/host'
        run('runtime-guest-ui-tests', ['swift', 'test', '--package-path', ROOT / 'experimental-capability-runtime',
            '--scratch-path', ROOT / 'experimental-capability-runtime/.build/guest-ui-debug', '--jobs', '4', '--filter', 'guestUI',
            '-Xcc', '-I' + str(native / 'include'), '-Xlinker', '-L' + str(native / 'lib'), '-Xswiftc', '-warnings-as-errors'])

        receipt_path = ROOT / 'verification/guest-ui-activation/candidate-4/receipt.json'
        receipt = json.loads(receipt_path.read_text())
        record['reused_activation_receipt'] = {'path': str(receipt_path.relative_to(ROOT)), 'sha256': sha(receipt_path)}
        library = receipt['artifacts']['debug']['dylib']
        assert sha(Path(library['path'])) == library['sha256']
        record['reused_activation_library'] = library
        previous_source = receipt['source'] + '/'
        command = next(c['command'] for c in receipt['commands'] if c['name'] == 'debug-test-link').copy()
        command = [str(ROOT) + '/' + part[len(previous_source):] if part.startswith(previous_source) else part for part in command]
        binary_index = command.index('-o') + 1
        original_binary = Path(command[binary_index])
        bundle = HERE / '.build/activation-debug/GuestUIActivationTests.xctest'
        binary = bundle / 'Contents/MacOS/GuestUIActivationTests'
        binary.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original_binary.parent.parent / 'Info.plist', bundle / 'Contents/Info.plist')
        command[binary_index] = str(binary)
        record['activation_test_sources'] = [{'path': str(Path(p).relative_to(ROOT)), 'sha256': sha(Path(p))}
                                              for p in command if p.endswith('.swift')]
        run('activation-debug-test-link', command, {'DEVELOPER_DIR': '/Applications/Xcode.app/Contents/Developer'})
        test = next(c for c in receipt['commands'] if c['name'] == 'debug-tests')
        run('activation-debug-tests', [test['command'][0], bundle], test['environment'])
        record['activation_test_binary'] = {'path': str(binary.relative_to(ROOT)), 'sha256': sha(binary)}
        record['status'] = 'passed'
    except Exception as error:
        record['status'] = 'failed'
        record['error'] = str(error)
        raise
    finally:
        (HERE / 'tests.json').write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
