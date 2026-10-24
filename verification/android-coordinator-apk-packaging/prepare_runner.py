#!/usr/bin/env python3
"""Freeze one APK packaging runner contract; no native dispatch."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    path = HERE / 'runner-contract.json'
    if path.exists():
        raise ValueError('frozen runner contract already exists')
    spec = importlib.util.spec_from_file_location('packaging_prepare_local_adapter', HERE / 'run.py')
    adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
    parent = adapter.load_module('packaging_prepare_parent', adapter.PARENT)
    _, original, _ = parent.load_runner()
    built = HERE / 'candidate-1'; receipt = json.loads((built / 'receipt.json').read_text())
    old_contract = json.loads(parent.CONTRACT.read_text())
    contract = {'schema': 1, 'bindings': adapter.BINDINGS,
        'acceptedConcreteRunnerSHA256': hashlib.sha256(original.encode()).hexdigest(),
        'acceptedBuildBindings': old_contract['buildBindings'],
        'frozenAPK_SHA256': receipt['apkSHA256'], 'sourceClosureSHA256': receipt['sourceClosureSHA256'],
        'buildBindings': {name: sha(built / name) for name in ('receipt.json', 'source-lock.json', 'built-artifacts.json',
            'built-artifacts.tar.gz', 'artifact-seal.json', 'artifact-delta.json', 'apk-entry-delta.json', 'apk-entries.json',
            'pre-sign-packaging.json', 'post-sign-packaging.json', 'pre-sign-official-zipalign.log',
            'post-sign-official-zipalign.log', 'private-debug-signature-cert.log')},
        'packagingValidatorSHA256': sha(HERE / 'apk_packaging.py'), 'builderSourceSHA256': sha(HERE / 'build.py'),
        'toolBindings': {name: value['sha256'] for name, value in receipt['tools'].items()},
        'originalInstallFailureEvidence': {name: value for name, value in adapter.BINDINGS.items() if '/runtime-1/' in name},
        'scope': 'APK-only packaging correction; all source inputs/class/DEX/native/artifact bytes except APK unchanged',
        'nativeRuntime': 'NOT RUN by packaging lane; root dispatch only', 'physicalPhoneMatrix': 'deferred; phones disconnected'}
    path.write_text(json.dumps(contract, indent=2, sort_keys=True) + '\n')
    concrete, deltas = adapter.transform(original)
    contract.update({'transformedRunnerSHA256': hashlib.sha256(concrete.encode()).hexdigest(), 'sourceDeltas': deltas})
    path.write_text(json.dumps(contract, indent=2, sort_keys=True) + '\n')
    wrapper = HERE / 'run.py'; text = wrapper.read_text(); old = "CONTRACT_SHA256 = 'PENDING'"
    if text.count(old) != 1:
        raise ValueError('exact one-time contract site required')
    wrapper.write_text(text.replace(old, "CONTRACT_SHA256 = '" + sha(path) + "'", 1))
    loaded = adapter.load_module('packaging_prepared_runner', wrapper)
    runner, source, diff = loaded.load_runner(); runner.bind_candidate(built)
    out = HERE / 'runner-source'; out.mkdir()
    (out / 'accepted_click_concrete_runner.py').write_text(original)
    (out / 'transformed_runner.py').write_text(source)
    (out / 'runner.diff').write_text(diff)
    (out / 'source-deltas.json').write_text(json.dumps(deltas, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': 'frozen-packaging-runner-source-only', 'sourceDeltas': len(deltas),
        'wrapperSHA256': sha(wrapper), 'contractSHA256': sha(path),
        'transformedRunnerSHA256': contract['transformedRunnerSHA256'], 'nativeInstancesStarted': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
