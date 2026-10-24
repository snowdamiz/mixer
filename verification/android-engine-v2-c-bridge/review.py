#!/usr/bin/env python3
"""Replay retained C bridge source, executable and command bindings offline."""
import datetime
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OLD = HERE / 'candidate-1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    prior = json.loads((OLD / 'receipt.json').read_text())
    completed = json.loads((HERE / 'inspection-completion/receipt.json').read_text())
    assert prior['status'] == 'failed'
    assert completed['status'] == 'passed-c-abi-and-android-export-inspection'
    assert completed['originalReceiptSHA256'] == sha(OLD / 'receipt.json')
    assert completed['correctedCollectorSHA256'] == sha(HERE / 'verify.py')
    assert completed['completionScriptSHA256'] == sha(HERE / 'finish-inspection.py')
    manifest = json.loads((OLD / 'source-manifest.json').read_text())
    assert prior['sourceManifestSHA256'] == sha(OLD / 'source-manifest.json')
    assert prior['sourceArchiveSHA256'] == sha(OLD / 'source.tar.gz')
    exceptions = {
        'verification/android-engine-v2-c-bridge/verify.py': 'Only symbol-tool selection repaired; failed original captured script retained in archive.',
        'docs/android-engine-v2-c-bridge.md': 'Verification outcome documented after capture; no product/test edits.'
    }
    with tarfile.open(OLD / 'source.tar.gz') as archive:
        for name, expected in manifest.items():
            assert hashlib.sha256(archive.extractfile(name).read()).hexdigest() == expected, name
            if name not in exceptions: assert sha(ROOT / name) == expected, name
    commands = prior['commands'] + completed['commands']
    for command in commands:
        assert command['exitCode'] == 0
        assert sha(ROOT / command['log']) == command['sha256']
    for name, expected in prior['artifacts'].items():
        assert sha(ROOT / name) == expected, name
    for mode in ['debug', 'release']:
        assert (OLD / (mode + '-c-run.log')).read_text() == 'PASS 77 C ABI assertions\n'
    acceptance = {
        'status': 'accepted-private-ordinary-staged-c-exports',
        'reviewer': 'root source and retained evidence review; no separate independent reviewer claimed for these thin forwards',
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'sourceRevision': prior['sourceRevision'], 'capturedFiles': len(manifest),
        'commandLogs': len(commands), 'nativeArtifacts': len(prior['artifacts']),
        'hostCAssertionsPerMode': 77, 'hostModes': ['debug', 'release'],
        'postCaptureNonProductChanges': exceptions,
        'bindings': {str(p.relative_to(ROOT)): sha(p) for p in [
            ROOT / 'native/android/engine/Sources/MixerAndroidEngine/Bridge.swift',
            ROOT / 'native/android/bridge/mixer_android_v2.h',
            ROOT / 'docs/android-engine-v2-c-bridge.md', OLD / 'receipt.json',
            HERE / 'inspection-completion/receipt.json', HERE / 'review.py', HERE / 'verify.py']},
        'scope': completed['scope'], 'pending': completed['pending'], 'gaPass': False,
    }
    (HERE / 'acceptance.json').write_text(json.dumps(acceptance, indent=2) + '\n')
    print(json.dumps({k: acceptance[k] for k in ['status', 'capturedFiles', 'commandLogs', 'nativeArtifacts', 'hostCAssertionsPerMode']}))


if __name__ == '__main__': main()
