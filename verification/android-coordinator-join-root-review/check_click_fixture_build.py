#!/usr/bin/env python3
"""Independently inspect both retained archives in memory; no native dispatch."""
import datetime
import hashlib
import io
import json
from pathlib import Path
import platform
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'verification/android-coordinator-join/candidate-2'
NEW = ROOT / 'verification/android-coordinator-click-fixture/candidate-1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def inspect(folder):
    receipt = read(folder / 'receipt.json')
    expected = read(folder / 'built-artifacts.json')
    archive = folder / 'built-artifacts.tar.gz'
    assert digest(archive.read_bytes()) == receipt['builtArchiveSHA256']
    observed = {}
    apk = None
    with tarfile.open(archive, 'r:gz') as tar:
        for member in tar:
            assert member.isfile() and member.name in expected and member.name not in observed
            raw = tar.extractfile(member).read()
            observed[member.name] = {'bytes': len(raw), 'sha256': digest(raw)}
            if member.name == 'coordinator-join.apk':
                apk = raw
    assert observed == expected and len(observed) == 177
    assert digest(apk) == receipt['apkSHA256']
    entries = {}
    with zipfile.ZipFile(io.BytesIO(apk)) as package:
        for entry in package.infolist():
            assert not entry.is_dir() and entry.filename not in entries
            raw = package.read(entry)
            entries[entry.filename] = {'bytes': len(raw), 'sha256': digest(raw)}
    return receipt, observed, entries


def main():
    before, old_artifacts, old_entries = inspect(BASE)
    after, new_artifacts, new_entries = inspect(NEW)
    assert old_artifacts.keys() == new_artifacts.keys()
    changed = [name for name in old_artifacts if old_artifacts[name] != new_artifacts[name]]
    assert set(changed) == {'coordinator-join.apk', 'dex/classes.dex',
                           'test-classes/dev/mixer/android/CoordinatorJoinInstrumentation.class'}
    assert old_entries.keys() == new_entries.keys()
    changed_entries = [name for name in old_entries if old_entries[name] != new_entries[name]]
    assert set(changed_entries) == {'classes.dex', 'META-INF/DEBUG.RSA', 'META-INF/DEBUG.SF', 'META-INF/MANIFEST.MF'}
    old_inputs = read(BASE / 'source-lock.json')['files']
    new_inputs = read(NEW / 'source-lock.json')['files']
    assert old_inputs.keys() == new_inputs.keys() and len(old_inputs) == 105
    source_delta = [name for name in old_inputs if old_inputs[name] != new_inputs[name]]
    assert source_delta == ['verification/android-coordinator-join/CoordinatorJoinInstrumentation.java']
    for folder, inputs in [(BASE, old_inputs), (NEW, new_inputs)]:
        for name, expected in inputs.items():
            assert digest((folder / 'inputs' / name).read_bytes()) == expected
    for command in after['commands']:
        assert command['exitCode'] == 0
        assert digest((NEW / command['output']).read_bytes()) == command['sha256']
    assert after['productionArtifactsRecompiled'] == 0 and after['privateKeyRetained'] is False
    assert after['buildScratchCleanup']['status'] == 'removed' and not (NEW / '.build').exists()
    files = [BASE / 'receipt.json', BASE / 'built-artifacts.json', BASE / 'source-lock.json',
             NEW / 'receipt.json', NEW / 'built-artifacts.json', NEW / 'source-lock.json',
             NEW / 'artifact-delta.json', NEW / 'apk-entry-delta.json', NEW / 'instrumentation.diff', Path(__file__)]
    result = {
        'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'accepted-instrumentation-only-build-derivation',
        'command': ['python3', '-B', str(Path(__file__).relative_to(ROOT))],
        'pythonVersion': platform.python_version(), 'sourceRevision': after['sourceRevision'],
        'baselineSourceClosure': before['sourceClosureSHA256'], 'derivedSourceClosure': after['sourceClosureSHA256'],
        'actualArchivesInspected': 2, 'actualArtifactsInspected': 354, 'actualSourceInputsInspected': 210,
        'changedArtifacts': sorted(changed), 'unchangedArtifacts': 174,
        'changedAPKEntries': sorted(changed_entries), 'unchangedAPKEntries': len(old_entries) - len(changed_entries),
        'changedSourceInputs': source_delta, 'apkSHA256': after['apkSHA256'],
        'review': 'Inspected exact one-site fixture diff. It invokes the same native performClick once and records its OnClickListener contract while preserving reducer revision+1, checked state, native identity and failure assertions.',
        'scope': 'Read-only archive inspection without extraction or native execution. Production classes, native libraries, assets and manifest are byte-identical. New DEX and private debug signatures are expected. Fresh app runtime remains required.',
        'bindings': {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in files},
    }
    (HERE / 'click-fixture-build-acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('status', 'actualArtifactsInspected', 'unchangedArtifacts', 'unchangedAPKEntries')}))


if __name__ == '__main__':
    main()
