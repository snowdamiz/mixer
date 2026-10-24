#!/usr/bin/env python3
"""Frozen F06/F07 callback adaptation; only root may dispatch after review."""
import argparse
import hashlib
import json
import support

CONTRACT_SHA256 = 'ccac2be8e717f2063eb2f8f8e09dc72a2bb81a43b29b18b883d4f3d649813cfe'

def load_runner():
    contract_path = support.HERE / 'runner-contract.json'
    if support.sha(contract_path) != CONTRACT_SHA256: raise ValueError('frozen correction contract drift')
    contract = json.loads(contract_path.read_text())
    for name, digest in contract['implementationBindings'].items():
        if support.sha(support.HERE / name) != digest: raise ValueError('correction implementation drift ' + name)
    for name, digest in contract['priorBindings'].items():
        if support.sha(support.ROOT / name) != digest: raise ValueError('reviewed runner binding drift ' + name)
    for name, digest in contract['toolBindings'].items():
        if support.sha(name) != digest: raise ValueError('frozen tool binding drift ' + name)
    _, prior, _ = support.prior_modules()
    runner, source, diff = prior.load_runner()
    if hashlib.sha256(source.encode()).hexdigest() != support.CONCRETE: raise ValueError('unchanged concrete runner drift')
    corrected = support.load('timing_corrected_oracle', support.HERE / 'oracle.py')
    runner._pointer_validate_native = corrected.validate
    runner._pointer_runtime_directory = support.runtime_directory
    runner._ADAPTATION = dict(runner._ADAPTATION, timingCorrection={
        'contractSHA256': support.sha(contract_path), 'wrapperSHA256': support.sha(__file__),
        'oracleSHA256': support.sha(support.HERE / 'oracle.py'),
        'outputPolicyImplementationSHA256': support.sha(support.HERE / 'support.py'),
        'unchangedConcreteRunnerSHA256': support.CONCRETE,
        'unchangedReviewedWrapperSHA256': support.sha(support.PRIOR / 'run.py'),
        'rootCorrectionSelection': support.bind(support.SELECTION),
        'runtimeOutputPolicy': support.RUNTIME_POLICY,
        'overrides': ['_pointer_validate_native', '_pointer_runtime_directory'],
        'nativeAuthority': 'explicit root dispatch only after independent correction acceptance',
        'scope': 'new oracle callback and output policy; unchanged concrete runner source does not contain the corrected oracle'})
    return runner, source, diff

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, choices=['candidate-5'])
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--execute-native', action='store_true')
    args = parser.parse_args()
    if not args.execute_native: parser.error('runtime NOT RUN; --execute-native requires explicit root dispatch after correction acceptance')
    support.runtime_directory(args.attempt)
    packet = support.load('timing_correction_packet', support.HERE / 'check_packet.py')
    packet.check()  # Both exact host packets/review/selection before runner entry.
    runner, _, _ = load_runner()  # Rechecks source and executable/SDK bindings.
    runner.main()  # Reviewed source repeats APK/source/signature checks preinstall.

if __name__ == '__main__': main()
