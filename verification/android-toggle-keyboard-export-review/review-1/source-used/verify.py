#!/usr/bin/env python3
"""Record a fresh host-only validation attempt; never dispatch native tools."""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import traceback
from pathlib import Path
import review_support as support


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', required=True)
    args = parser.parse_args()
    support.need(re.fullmatch(r'review-[1-9][0-9]*', args.attempt) is not None, 'fresh review-N required')
    out = support.HERE / args.attempt
    out.mkdir()
    source = out / 'source-used'
    source.mkdir()
    for path in sorted(support.HERE.glob('*.py')):
        (source / path.name).write_bytes(path.read_bytes())
    doc = support.ROOT / 'docs/android-toggle-keyboard-export-review.md'
    if doc.exists():
        (source / doc.name).write_bytes(doc.read_bytes())
    receipt = {'schema': 1, 'status': 'offline-review-running', 'startedUTC': now(),
               'invocation': [sys.executable, '-B', str(Path(__file__).resolve()), '--attempt', args.attempt],
               'python': {'executable': str(Path(sys.executable).resolve()), 'binding': support.bind(Path(sys.executable).resolve()),
                          'version': sys.version}, 'host': list(os.uname()),
               'commands': [], 'nativeCommandsExecuted': 0, 'GitCommandsExecuted': 0, 'CUACommandsExecuted': 0,
               'sourceSnapshots': support.directory_bind(source), 'rootIndependentAcceptance': 'pending'}

    def command(name, script_args):
        argv = [sys.executable, '-B', *map(str, script_args)]
        started = now()
        result = subprocess.run(argv, cwd=support.ROOT, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60, check=False)
        log = out / (name + '.log')
        log.write_bytes(result.stdout)
        receipt['commands'].append({'name': name, 'argv': argv, 'cwd': str(support.ROOT), 'startedUTC': started,
                                    'finishedUTC': now(), 'exitCode': result.returncode, 'output': log.name, **support.bind(log)})
        support.save(out / 'receipt.json', receipt)
        support.need(result.returncode == 0, name + ' failed; full output retained')
        return result.stdout

    try:
        receipt['upstreamBefore'] = support.check_upstream()
        original = support.read_bytes(command('original-sealed-host-controls', [support.PRODUCER / 'test_host.py']))
        support.need(original['checks'] == 101 and original['originalCaseBodiesAndScrollProtocolUnchanged'] is True,
                     'original source and export controls')
        controls = support.read_bytes(command('strict-sequence-and-native-export-controls', [support.HERE / 'test_controls.py', '--work-root', out]))
        support.save(out / 'controls.json', controls)
        result = support.read_bytes(command('immutable-runtime-audit-and-offline-collector-replay', [support.HERE / 'replay.py', '--out', out]))
        support.save(out / 'offline-acceptance.json', result)
        receipt['upstreamAfter'] = support.check_upstream()
        support.need(receipt['upstreamAfter'] == receipt['upstreamBefore'], 'unchanged sealed upstream')
        receipt.update(status='passed-independent-offline-keyboard-export-review-root-acceptance-pending',
                       originalHostChecks=original['checks'], checks=controls['checks'], rejectedControls=controls['rejectedControls'],
                       sourceRevision=support.read(support.RUNTIME / 'receipt.json')['sourceRevision'],
                       fixtureSourceClosureSHA256=support.read(out / 'runtime-audit.json')['fixtureSourceClosureSHA256'],
                       nativeAssertions=result['nativeAssertions'], correctedOfflineCollection=result['correctedOfflineCollection']['oracle'],
                       originalOuterCollectionFailurePreserved=True, actualFailed39CaseExportRemainsFailed=True)
    except BaseException as failure:
        receipt.update(status='failed-offline-review-retained', failure=repr(failure))
        (out / 'failure.log').write_text(traceback.format_exc())
        raise
    finally:
        scratch = [str(path) for path in out.rglob('*') if path.is_dir() and path.name.startswith(('.replay-', '.controls-', '__pycache__'))]
        receipt['cleanup'] = {'ownedScratchAbsent': not scratch, 'remainingOwnedScratch': scratch, 'newNativeInstances': 0,
                              'nativeProcessQueries': 0, 'scope': 'own temporary offline replay and control directories only'}
        receipt['finishedUTC'] = now()
        support.save(out / 'receipt.json', receipt)
        support.save(out / 'artifact-seal.json', support.directory_bind(out, (out / 'artifact-seal.json',)))
    print(json.dumps({key: receipt[key] for key in ('status', 'checks', 'rejectedControls', 'nativeAssertions', 'cleanup')}, sort_keys=True))


if __name__ == '__main__':
    main()
