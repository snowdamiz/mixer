#!/usr/bin/env python3
"""Seal the bounded read-only source audit; never executes product/native code."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
SOURCES = (
    'native/android/bridge/jni.c',
    'native/android/bridge/mixer_android_v2.h',
    'native/android/app/src/dev/mixer/android/NativeBridge.java',
    'native/android/engine/Sources/MixerAndroidEngine/Bridge.swift',
    'cli/Sources/MixerBuild/AndroidProject.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    output = BASE / 'jni-cli-source-review-1'
    output.mkdir()
    inputs = {}
    for name in SOURCES:
        source = ROOT / name
        assert source.is_file() and not source.is_symlink(), name
        data = source.read_bytes()
        captured = output / 'inputs' / name
        captured.parent.mkdir(parents=True, exist_ok=True)
        captured.write_bytes(data)
        inputs[name] = {'bytes': len(data), 'sha256': sha(data)}
    evidence = {}
    candidate_path = ROOT / 'verification/android-v2-jni-candidate-bridge/candidate-1/receipt.json'
    replay_path = ROOT / 'verification/android-v2-jni-candidate-bridge/root-replay-1/receipt.json'
    candidate = json.loads(candidate_path.read_bytes())
    replay = json.loads(replay_path.read_bytes())
    assert candidate['status'] == replay['status'] == 'passed'
    assert replay['candidateReceiptSHA256'] == sha(candidate_path.read_bytes())
    assert replay['bindingsChecked'] == 153
    expected = {f'{kind}-{mode}-{execution}': count
                for kind, count in [('production', 585), ('derived', 199)]
                for mode in ['debug', 'release'] for execution in ['normal', 'interpreted']}
    assert replay['assertions'] == expected
    for command in replay['commands']:
        assert command['exitCode'] == 0, command['label']
        path = ROOT / command['log']
        assert sha(path.read_bytes()) == command['sha256'], str(path)
        evidence[str(path.relative_to(ROOT))] = command['sha256']
    for name, expected_hash in replay['artifacts'].items():
        path = ROOT / name
        assert sha(path.read_bytes()) == expected_hash, name
        evidence[name] = expected_hash
    manifest_path = candidate_path.parent / 'source-manifest.json'
    assert sha(manifest_path.read_bytes()) == candidate['sourceManifestSHA256']
    manifest = json.loads(manifest_path.read_bytes())
    # These four audited JNI/ABI sources are bound to the retained host replay.
    for name in SOURCES[:4]:
        assert manifest[name] == inputs[name]['sha256'], name
    for path in [candidate_path, replay_path, manifest_path, ROOT / 'AGENTS.md']:
        evidence[str(path.relative_to(ROOT))] = sha(path.read_bytes())
    for name, metadata in inputs.items():
        assert sha((ROOT / name).read_bytes()) == metadata['sha256'], name
    receipt = {
        'status': 'passed-bounded-source-review-no-new-blocking-findings',
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': [sys.executable, str(Path(__file__).resolve())],
        'pythonVersion': platform.python_version(),
        'reviewerScriptSHA256': sha(Path(__file__).read_bytes()),
        'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'sourceTree': subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip(),
        'sourceManifest': inputs,
        'sourceClosureSHA256': sha(json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode()),
        'sourceUnchanged': True,
        'findings': [],
        'reviewedBehavior': [
            'Prepare delivery failure frees buffers and local references, preserves pending Java exception, aborts candidate or retires session.',
            'Scalar commit and abort do not allocate Java results after the native decision.',
            'Private JNI Candidate constructor and packet copies match its native descriptor; opaque UInt64 token bits survive Java sign.',
            'Generated six C entry points match the private/legacy headers and runtime forwarding signatures.',
            'Exported source closure includes private header and twelve required Java sources without opting the legacy Activity into V2.',
            'JNI shared library links with no undefined symbols against actual generated AppAndroid; dependencies and unsigned APK are inspected.',
            'Build cleanup is confined to guarded owned output; source/toolchain guards reject changed input and do not claim isolated attestation.',
        ],
        'retainedHostReplay': {
            'receipt': str(replay_path.relative_to(ROOT)), 'bindingsChecked': 153,
            'assertions': replay['assertions'],
            'scope': 'Existing real Swift/JNI JVM evidence only; no product tests rerun by this review.',
        },
        'evidenceSHA256': evidence,
        'scope': 'Read-only JNI cleanup/link/export/generated-ABI source audit and offline integrity checks only. No GUI, screen capture, simulator/emulator, device discovery, product compilation, runtime execution, or publication.',
        'pending': ['Current final Android Java export/build binding after baseline source freeze.',
                    'Native rendering and engine/native owner coordination qualification.',
                    'Physical phones, signed V2/bootstrap, published FieldLog packages, stores and GA.'],
    }
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': receipt['status'], 'sources': len(inputs),
                      'evidenceBindings': len(evidence), 'receipt': str(output / 'receipt.json')}))


if __name__ == '__main__':
    main()
