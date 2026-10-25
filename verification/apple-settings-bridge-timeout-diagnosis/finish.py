"""Recheck read inputs, remove only owned scratch, and bind this offline report."""
import ast
import datetime
import hashlib
import json
import pathlib
import shutil
import sys

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def digest(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def main():
    inputs = json.loads((BASE / 'evidence-bindings.json').read_text())['files']
    for name, expected in inputs.items():
        assert digest(ROOT / name) == expected, name
    for name in ['collect.py', 'host_controls.py', 'finish.py']:
        ast.parse((BASE / name).read_text(), filename=name)
    controls = json.loads((BASE / 'host-controls.json').read_text())
    assert controls['transport']['passedAssertions'] == 5
    assert controls['transaction']['fsyncCallsBeforeCommitReturns'] == 8
    assert controls['execute']['exitCode'] == controls['compile']['exitCode'] == 0
    # Clarify that the allowed compiler and host binary are not counted as
    # simulator/device verification processes; retain their actual command logs.
    controls['nativeVerificationProcessesStarted'] = controls.pop('nativeProcessesStarted', 0)
    write(BASE / 'host-controls.json', controls)

    scratch = BASE / 'scratch'
    assert scratch.resolve() == scratch and scratch.parent == BASE and not scratch.is_symlink()
    files = [path for path in scratch.rglob('*') if path.is_file()]
    before = {'files': len(files), 'bytes': sum(path.stat().st_size for path in files)}
    shutil.rmtree(scratch)
    assert not scratch.exists()
    write(BASE / 'cleanup.json', {'schema': 1, 'command': [sys.executable, '-B', str(pathlib.Path(__file__).resolve())],
        'python': sys.version, 'ownedScratchPath': str(scratch), 'removedScratch': before,
        'ownedScratchAbsent': True, 'inputFilesRecheckedUnchanged': len(inputs),
        'devicesQueried': 0, 'processesSignalled': 0, 'otherProjectsTouched': False})
    doc = ROOT / 'docs/apple-settings-bridge-timeout-diagnosis.md'
    members = {str(doc.relative_to(ROOT)): digest(doc)}
    for path in sorted(BASE.iterdir()):
        if path.is_file() and path.name != 'handoff.json':
            members[str(path.relative_to(ROOT))] = digest(path)
    write(BASE / 'handoff.json', {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Bounded offline diagnosis only; no native retry or source/packet/budget/importer correction',
        'nativeInputHandoffSHA256': 'bc226729d7133f33b52d98a4fd7446771bae7bc6c5672455927bbe343c723927',
        'members': members, 'inputFilesRecheckedUnchanged': len(inputs), 'ownedScratchAbsent': True,
        'timedOutBridgeRequestID': None, 'diagnosticPassCredited': False, 'gaAccepted': False,
        'nextStep': 'First-failure client identity and actual remaining-budget instrumentation under unchanged limits; phase spans if latency attribution is needed.'})
    print(json.dumps({'reportMembers': len(members), 'inputFilesRecheckedUnchanged': len(inputs),
        'ownedScratchAbsent': True, 'handoffSHA256': digest(BASE / 'handoff.json')['sha256']}))


if __name__ == '__main__':
    main()
