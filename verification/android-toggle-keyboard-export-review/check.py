#!/usr/bin/env python3
"""Read-only sealed packet/root review check; executes no runner or native tools."""
import json
import collector
import evidence
import review_support as support


def check():
    packet_path = support.HERE / 'packet-seal.json'
    packet = support.read(packet_path)
    files = support.directory_bind(support.HERE, (packet_path,))
    doc = support.ROOT / 'docs/android-toggle-keyboard-export-review.md'
    files[str(doc)] = support.bind(doc)
    support.need(packet == {'schema': 1, 'files': files}, 'review packet file set/bytes drift')
    for path in support.HERE.glob('review-*'):
        if not path.is_dir():
            continue
        seal = path / 'artifact-seal.json'
        support.need(support.directory_bind(path, (seal,)) == support.read(seal), 'review attempt artifact seal drift')
    out = support.HERE / 'review-1'
    receipt = support.read(out / 'receipt.json')
    support.need(receipt['status'] == 'passed-independent-offline-keyboard-export-review-root-acceptance-pending', 'complete offline review required')
    support.need((out / 'corrected_keyboard_oracle.py').read_text() == collector.derive(), 'exact finite corrected collector source')
    support.need(support.read(out / 'collector-adaptation.json') == {key: value for key, value in collector.adaptation().items() if key != 'diff'}, 'finite correction receipt drift')
    support.need((out / 'collector.diff').read_text() == collector.adaptation()['diff'], 'finite correction diff drift')
    audit = evidence.audit()
    support.need(audit == support.read(out / 'runtime-audit.json'), 'independent runtime audit drift')
    oracle = collector.load()
    accepted = oracle.validate(support.read(support.RUNTIME / 'toggle-supplement-results.json'), support.HERE,
                               support.read(support.RUNTIME / 'source-identity-predispatch.json'))
    support.need(accepted == receipt['correctedOfflineCollection'], 'all original and strict native predicates reapply')
    support.need(receipt['cleanup']['ownedScratchAbsent'] is True, 'owned host scratch cleanup required')
    return {'schema': 1, 'status': 'passed-read-only-independent-keyboard-export-packet-check',
            'checks': receipt['checks'], 'rejectedControls': receipt['rejectedControls'],
            'originalHostChecks': receipt['originalHostChecks'], 'nativeCases': accepted['cases'],
            'nativeAssertions': audit['nativeCompleted'], 'producerSealSHA256': support.PRODUCER_SEAL,
            'runtimeSealSHA256': support.RUNTIME_SEAL, 'packetFiles': len(files),
            'nativeCommandsExecuted': 0, 'rootIndependentAcceptance': 'pending', 'GA': 'not accepted'}


if __name__ == '__main__':
    print(json.dumps(check(), indent=2, sort_keys=True))
