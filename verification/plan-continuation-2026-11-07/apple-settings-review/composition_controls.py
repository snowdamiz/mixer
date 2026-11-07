#!/usr/bin/env python3
"""Load the exact sealed runtime archive and exercise only the Python receiver."""
import copy
import importlib
import json
from pathlib import Path
import secrets
import shutil
import sys
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
FIX = HERE.parent / 'apple-settings-fix'
ACTUAL = HERE.parent / 'apple-runtime'
mode = sys.argv[1]
assert mode in ['baseline', 'candidate']
scratch = Path(tempfile.mkdtemp(prefix='composition-' + mode + '-', dir=HERE)).resolve()
report = {'mode': mode, 'scope': 'exact archive, host receiver replay; no native/HTTP/process calls'}
try:
    selected = scratch / 'selected'
    selected.mkdir()
    archive_path = FIX / 'candidate-runtime-sources.tar.gz' if mode == 'candidate' else REPO / 'verification/apple-passive-lifecycle-runtime-preparation/runtime-sources.tar.gz'
    with tarfile.open(archive_path) as archive:
        for member in archive:
            if member.isdir():
                continue
            assert member.isfile() and member.name.startswith('selected/')
            name = member.name.removeprefix('selected/')
            assert '..' not in Path(name).parts and not Path(name).is_absolute()
            target = selected / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
            target.chmod(member.mode)
    template = FIX / 'candidate-selection-template.json' if mode == 'candidate' else REPO / 'verification/apple-passive-lifecycle-runtime-preparation/selection-template.json'
    selection = json.loads(template.read_bytes())
    root = json.loads((ACTUAL / 'root-selection.json').read_bytes())
    selection.update(repositoryRoot=str(REPO), outputBase=str(scratch / 'output'),
                     productsRoot=str(scratch / 'unused-products'), trustedRootSelection=root)
    (selected / 'runtime-selection.json').write_text(json.dumps(selection))
    sys.path.insert(0, str(selected))
    m = importlib.import_module('composition')
    receiver = m.h.Bridge({'diagnostic': scratch / 'unused-documents'}, scratch / 'captures',
                          secrets.token_hex(32), root['ownedSimulatorIdentity'],
                          allowed_cases={'keyboard-enabled-off'})
    captures = ACTUAL / json.loads((ACTUAL / 'result.json').read_bytes())['artifacts']['rawCaptures']
    rows = [json.loads(p.read_bytes()) for p in sorted(captures.glob('0000-settings-*.json'))]
    clock = [rows[0]['receivedUptime']]
    receiver.settings.now = lambda: clock[0]
    receiver.settings.token = rows[0]['generation']
    receiver.settings.deadline = rows[0]['sessionDeadlineUptime']
    sent = 0
    for row in rows:
        if mode == 'candidate' and row['record'].get('slot') == 'settings-0131-png':
            continue
        clock[0] = row['receivedUptime']
        receiver.request('evaluate', {'settingsDiagnostic': copy.deepcopy(row['record'])})
        sent += 1
    summary = receiver.settings.summary()
    report.update(requestsReplayed=sent, settingsSummary=summary, setupReady=m.setup_ready(receiver.settings))
    assert not m.setup_ready(receiver.settings)
    if mode == 'candidate':
        assert summary['settingsEvidenceComplete'] and summary['setupObservationSatisfied']
        assert summary['terminationMarkers'] == [] and summary['completionMarkers'] == []
        replay = importlib.import_module('replay')
        assert replay.replay(scratch / 'captures') == summary
        assert (scratch / 'captures/settings-0131-png.png').read_bytes() == (captures / 'settings-0083-png.png').read_bytes()
        report['durableReplayAndTerminalBytesExact'] = True
    else:
        assert summary['pendingSlots'] == ['settings-0131-png']
        assert len(receiver.settings.uploads['settings-0131-png']['parts']) == 23
        assert not summary['setupObservationSatisfied']
    try:
        receiver.request('begin', {'candidate': 'diagnostic', 'case': 'keyboard-enabled-off'})
    except ValueError as error:
        assert 'Durable measured setup' in str(error)
        report['missingCompletionBlocksTab'] = True
    else:
        raise AssertionError('Incomplete Settings allowed Tab begin')
    # Exact module origin checks reject substitution without executing outside code.
    original_origin = m.telemetry.__spec__.origin
    m.telemetry.__spec__.origin = str(scratch / 'unselected.py')
    try:
        m.bindings.module(m.telemetry)
    except ValueError as error:
        assert 'outside selected origin' in str(error)
        report['moduleOriginSubstitutionRejected'] = True
    else:
        raise AssertionError('Unselected module origin accepted')
    finally:
        m.telemetry.__spec__.origin = original_origin
    # The first source-binding failure must latch even after restoring the bytes.
    source = selected / 'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py'
    original_bytes = source.read_bytes()
    source.write_bytes(original_bytes + b'\n')
    failure = None
    try:
        receiver.request('evaluate', {'settingsDiagnostic': rows[-1]['record']})
    except ValueError as error:
        assert 'source/data changed' in str(error)
        failure = error
    finally:
        source.write_bytes(original_bytes)
    assert failure is not None
    try:
        receiver.request('evaluate', {'settingsDiagnostic': rows[-1]['record']})
    except ValueError as error:
        assert error is failure
        report['sourceMutationRejectedAndFirstFailureLatched'] = True
    else:
        raise AssertionError('Source failure did not latch')
    assert receiver.settings.summary() == summary
    report['passed'] = True
finally:
    shutil.rmtree(scratch)
    report['scratchRemoved'] = not scratch.exists()
    (HERE / ('composition-' + mode + '.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'settingsSummary'}, indent=2))
