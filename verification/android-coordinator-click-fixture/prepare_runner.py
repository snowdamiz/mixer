#!/usr/bin/env python3
"""Freeze exact build metadata and eight counted runner deltas once, headlessly."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    contract_path = HERE / 'runner-contract.json'
    if contract_path.exists():
        raise ValueError('contract already exists; frozen derivations are immutable')
    spec = importlib.util.spec_from_file_location('click_prepare_runner', HERE / 'run.py')
    adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
    wifi = adapter.load_module('click_prepare_wifi', adapter.WIFI)
    inherited, original, _ = wifi.load_runner()
    built = HERE / 'candidate-1'
    receipt = json.loads((built / 'receipt.json').read_text())
    contract = {'schema': 1, 'bindings': adapter.BINDINGS,
        'acceptedConcreteRunnerSHA256': hashlib.sha256(original.encode()).hexdigest(),
        'frozenCandidatePath': str(built.relative_to(ROOT)),
        'frozenAPK_SHA256': receipt['apkSHA256'], 'sourceClosureSHA256': receipt['sourceClosureSHA256'],
        'buildBindings': {name: sha(built / name) for name in ('receipt.json', 'source-lock.json',
            'built-artifacts.json', 'built-artifacts.tar.gz', 'artifact-seal.json', 'artifact-delta.json',
            'apk-entry-delta.json', 'apk-entries.json', 'instrumentation.diff')},
        'builderSourceSHA256': sha(HERE / 'build.py'),
        'originalFailureEvidence': {name: digest for name, digest in adapter.BINDINGS.items() if '/runtime-1/' in name},
        'scope': 'test-only corrected instrumentation; production .class/native/resources unchanged',
        'nativeRuntime': 'NOT RUN by derivation lane; root dispatch only',
        'physicalPhoneMatrix': 'deferred; phones disconnected'}
    # BUILD_BINDINGS consumed by the inherited binder may bind extra metadata safely.
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True) + '\n')
    source, deltas = adapter.transform(original)
    contract.update({'transformedRunnerSHA256': hashlib.sha256(source.encode()).hexdigest(), 'sourceDeltas': deltas})
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True) + '\n')
    wrapper = HERE / 'run.py'
    text = wrapper.read_text()
    old = "CONTRACT_SHA256 = 'PENDING'"
    if text.count(old) != 1:
        raise ValueError('exact one-time unsealed contract site required')
    wrapper.write_text(text.replace(old, "CONTRACT_SHA256 = '" + sha(contract_path) + "'", 1))
    loaded = adapter.load_module('click_prepared_runner', wrapper)
    runner, concrete, diff = loaded.load_runner()
    runner.bind_candidate(built)
    review = HERE / 'runner-source'; review.mkdir()
    (review / 'accepted_wifi_concrete_runner.py').write_text(original)
    (review / 'transformed_runner.py').write_text(concrete)
    (review / 'runner.diff').write_text(diff)
    (review / 'source-deltas.json').write_text(json.dumps(deltas, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': 'frozen-runner-source-only', 'wrapperSHA256': sha(wrapper),
        'contractSHA256': sha(contract_path), 'transformedRunnerSHA256': contract['transformedRunnerSHA256'],
        'sourceDeltas': len(deltas), 'nativeInstancesStarted': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
