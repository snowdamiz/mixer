#!/usr/bin/env python3
"""Audit and replay one completed native export wholly offline."""
import argparse
import json
import tempfile
import traceback
from pathlib import Path
import collector
import evidence
import review_support as support


def review(out):
    before = support.check_upstream()
    audit = evidence.audit()
    support.save(out / 'runtime-audit.json', audit)
    adaptation = collector.adaptation()
    (out / 'collector.diff').write_text(adaptation.pop('diff'))
    support.save(out / 'collector-adaptation.json', adaptation)
    (out / 'corrected_keyboard_oracle.py').write_text(collector.derive())
    original_failure = None
    scratch_paths = []
    for corrected in (False, True):
        with tempfile.TemporaryDirectory(prefix='.replay-', dir=out) as folder:
            scratch = Path(folder)
            scratch_paths.append(scratch)
            try:
                result = collector.replay(collector.load(corrected), scratch)
                support.need(corrected, 'original collector unexpectedly accepted completed export')
                copies = support.directory_bind(scratch)
                support.need(copies['toggle-supplement-results.json'] == before['nativeRawExport'], 'replayed native raw bytes preserved exactly')
                for name in collector.load().SCREENSHOTS:
                    support.need(copies[name] == support.bind(support.RUNTIME / name), 'replayed native screenshot preserved ' + name)
                result['replayedOutputBindings'] = copies
            except ValueError as failure:
                if corrected:
                    raise
                support.need(repr(failure) == "ValueError('native mode trace exact schema')", 'exact original collector failure identity')
                original_failure = {'failure': repr(failure), 'rawNativeBytes': support.bind(scratch / 'toggle-supplement-results.json'),
                                    'unchangedRuntimeReceipt': support.bind(support.RUNTIME / 'receipt.json')}
                (out / 'original-collector-failure.log').write_text(traceback.format_exc())
    support.need(original_failure is not None, 'original collection failure retained')
    after = support.check_upstream()
    support.need(before == after, 'upstream mutated during offline review')
    support.need(all(not path.exists() for path in scratch_paths), 'owned replay scratch cleanup')
    return {'schema': 1, 'status': 'passed-corrected-offline-collection-of-complete-immutable-native-export',
            'scope': 'independent component export acceptance only; root acceptance and product integration pending',
            'nativeAssertions': audit['nativeCompleted'], 'correctedOfflineCollection': result,
            'originalOuterCollectionFailurePreserved': original_failure,
            'upstreamBefore': before, 'upstreamAfter': after,
            'cleanup': {'ownedReplayScratchAbsent': True, 'pathsRemoved': [str(path) for path in scratch_paths],
                        'newNativeInstances': 0, 'retainedNativeCleanupRechecked': audit['cleanup']},
            'nativeCommandsExecuted': 0, 'GitCommandsExecuted': 0, 'CUACommandsExecuted': 0,
            'productionCodeChanged': False, 'dependenciesAdded': [],
            'physicalPhones': 'deferred disconnected', 'TalkBackServiceWorkflow': 'NOT RUN',
            'AppleParity': 'pending', 'engineCoordinatorAuthority': 'not established',
            'screenshotPixels': 'pending root visual review', 'FieldLogPublishedPackageQualification': 'pending',
            'GA': 'not accepted', 'rootIndependentAcceptance': 'pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    support.need(args.out.resolve().is_relative_to(support.HERE) and args.out.is_dir(), 'owned review output required')
    print(json.dumps(review(args.out), indent=2, sort_keys=True, allow_nan=False))
