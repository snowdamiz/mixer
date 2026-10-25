#!/usr/bin/env python3
"""Independent finite host review; never compiles or queries native state."""
import copy
import dataclasses
import hashlib
import importlib.util
import json
import pathlib
import platform
import stat
import subprocess
import sys
import tarfile
import traceback
from datetime import datetime, timezone
from decimal import Decimal as D, localcontext

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = ROOT / 'verification/apple-focus-system-join-correction'
EXPECTED_SEALS = {
    'apple-focus-system-join-correction': ('2121ef09603e12a5c69a8918a1494c1d3e2f34dc5e6354080cfe38b50649b16d', 85),
    'apple-focus-system-observation': ('5d88cd0069f7e83e73b95903ecf0e9e6b721a73328193653e8e1da8903c81427', 177),
    'apple-focus-system-observation-review': ('e66d1f5710d5614fc668bec3fc6759fb6080a91002516f13d43994dca2ab35a4', 51),
}
PINNED_RAW = {
    'before': (16451, '82581f55bd299fb623d85a39fa726ee072bb54fb065164da6618fec63c2c9c3d'),
    'after': (21153, '160f124cb50b74006b7f6791c0aab6a683dab65a9ad9c193604569efcf2a7a9b'),
    'witness': (1816, '388655651136e672499be043e1188733ca6dd549af67f755185332a77b90d70e'),
}
SOURCE_SHA = 'd1262c1e16a4decdca0ecbfdc278b7eaa1282f47d68776bfdede235157019cda'
SOURCE_REVISION = '9102ad3ee1247187c01ea5f55c42caaac882961b'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
controls = []

def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def load_json(raw):
    return json.loads(raw, parse_float=D)

def binding(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': sha(raw), 'mode': stat.S_IMODE(path.stat().st_mode)}

def verify_parents(stage):
    result = {}
    for lane, (expected_digest, expected_count) in EXPECTED_SEALS.items():
        folder = ROOT / 'verification' / lane
        handoff = folder / 'handoff.json'
        raw = handoff.read_bytes()
        assert sha(raw) == expected_digest, lane
        members = json.loads(raw)['members']
        assert len(members) == expected_count, lane
        checksum = folder / 'handoff.sha256'
        actual = {str(p.relative_to(ROOT)) for p in folder.rglob('*') if p.is_file() and p not in (handoff, checksum)}
        actual.update(relative for relative in members if not relative.startswith('verification/' + lane + '/'))
        assert actual == set(members), (lane, sorted(actual ^ set(members)))
        if checksum.exists():
            assert checksum.read_text().strip() == expected_digest
            assert stat.S_IMODE(checksum.stat().st_mode) == 0o444
        observed = {}
        for relative, expected in members.items():
            observed[relative] = binding(ROOT / relative)
            assert observed[relative] == {k: expected[k] for k in ('bytes', 'sha256', 'mode')}, relative
        assert stat.S_IMODE(handoff.stat().st_mode) == 0o444, lane
        result[lane] = {'handoffSHA256': sha(raw), 'members': expected_count, 'observed': observed}
    write('parent-seals-' + stage + '.json', result)
    return result

def imported(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def diagnostic(rows):
    return {'schema': 'mixer.apple-toggle.focus-system.1', 'authoritative': False,
            'atomic': False, 'entries': rows, 'dropped': 0,
            'revision': len(rows), 'captureStatus': 'complete'}

def sample(sequence, start, context=None, item=1, system=True, scene='absent', window=True):
    identities = ['review-control-A', 'review-control-B', 'review-control-C']
    item_identity = identities[item] if type(item) is int else 'review-other' if item == 'other' else None
    matches = [system and item_identity == identity for identity in identities]
    item_state = 'unavailable' if not system else 'fixed' if any(matches) else 'null' if item is None else 'other'
    return {
        'sequence': sequence, 'startedUptime': start, 'finishedUptime': start + D('.000001'),
        'site': 'controller-callback' if context is not None else 'snapshot',
        'contextSequence': context, 'stage': 'review',
        'environment': {'selection': 'window' if window else 'controller',
                        'identity': 'review-window' if window else 'review-controller',
                        'windowIdentity': 'review-window' if window else None},
        'system': {'state': 'present' if system else 'unavailable',
                   'identity': 'review-system' if system else None,
                   'item': {'state': item_state, 'identity': item_identity if system else None, 'fixedMatches': matches}},
        'controls': [{'slot': slot, 'identity': identity, 'isFocused': False,
                      'attachedToWindow': window, 'windowIdentity': 'review-window' if window else None,
                      'canBecomeFocused': True, 'focusGroupIdentifier': None, 'focusGroupPriority': 0}
                     for slot, identity in zip(('authored-toggle', 'plain-uibutton-reference', 'next-focus'), identities)],
        'scene': {'state': scene, 'identity': None if scene == 'absent' else 'review-scene',
                  'systemIdentity': 'review-scene-system' if scene == 'present' else None, 'itemIdentity': None},
    }

def fixture(o):
    raws = [(CANDIDATE / 'inputs/v7' / name).read_bytes() for name in
            ('0001-before-1.json', '0001-after-1.json', '0001-keyboard-witness-1.json')]
    b, a, packet = [load_json(raw) for raw in raws]
    before, after, witness, action = b['observation'], a['observation'], packet['witness'], packet['binding']
    before['focusSystemDiagnostic'] = diagnostic([
        sample(1, before['focusContexts'][0]['uptime'] + D('.00001'), 1),
        sample(2, action['baselineUptime'] - D('.01'))])
    rows = copy.deepcopy(before['focusSystemDiagnostic']['entries'])
    for context, item in zip(after['focusContexts'][1:], (None, 1, None)):
        rows.append(sample(len(rows) + 1, context['uptime'] + D('.00001'), context['sequence'], item))
    rows.append(sample(len(rows) + 1, witness['after']['uptime'] + D('.001'), item=None))
    after['focusSystemDiagnostic'] = diagnostic(rows)
    anchor = o.select_original_action('v7-first-tab', *raws)
    return [before, after, witness, action, anchor, a['verdict']]

def fingerprint(o, value):
    if type(value) is o.OriginalActionAnchor:
        return {'selection': value.selection, 'packets': {role: sha(getattr(value, role + '_packet_raw')) for role in PINNED_RAW}}
    return sha(o.encoded(value))

def join_control(o, name, mutation=None, expected='complete'):
    values = fixture(o)
    if mutation:
        mutation(values)
    before = [fingerprint(o, v) for v in values]
    original_object = values[-1]
    original_bytes = o.encoded(original_object)
    result = o.join(*values)
    actual = result['supplemental']['captureStatus']
    assert actual == expected, (name, expected, actual)
    assert result['originalVerdict'] is original_object
    assert o.encoded(original_object) == original_bytes
    assert before == [fingerprint(o, v) for v in values], name
    assert result['supplemental']['nativePass'] is False
    controls.append({'name': name, 'kind': 'join', 'expected': expected, 'actual': actual,
                     'passed': True, 'nativePass': False, 'originalVerdictUnchanged': True,
                     'allInputsUnchanged': True, 'inputFingerprints': before, 'supplemental': result['supplemental']})
    return result

def validate_control(o, name, value, contexts, expected=None):
    before = o.encoded(value)
    try:
        result = o.validate(value, contexts)
        actual = 'complete'
        assert result is value
    except o.Incomplete as error:
        actual = str(error)
    assert actual == (expected or 'complete'), (name, expected, actual)
    assert before == o.encoded(value)
    controls.append({'name': name, 'kind': 'schema', 'expected': expected or 'complete', 'actual': actual,
                     'passed': True, 'inputSHA256': sha(before), 'nativeEvidence': False})

def execute(o):
    assert o.RAW_INPUTS == PINNED_RAW
    positive = join_control(o, 'Exact frozen join and ordered [1,2,3,4] callbacks')
    assert positive['originalVerdict']['passed'] is False
    assert [k for k, v in positive['originalVerdict']['predicates'].items() if v is False] == ['actualNativeFocusTraversal']
    join_control(o, 'F1 exact AX authored-toggle hasFocus substitution',
                 lambda v: v[2]['after']['elements']['authored-toggle'].update(hasFocus=True), 'incomplete-original-witness')
    join_control(o, 'F1 exact app before.state.focused substitution',
                 lambda v: v[0]['state'].update(focused=not v[0]['state']['focused']), 'incomplete-original-before-observation')

    def tighter_reorder(v):
        rows = v[1]['focusSystemDiagnostic']['entries']; old = copy.deepcopy(rows)
        rows[2]['contextSequence'], rows[3]['contextSequence'] = 3, 2
        rows[2]['startedUptime'] = v[1]['focusContexts'][2]['uptime'] + D('.00001')
        rows[2]['finishedUptime'] = rows[2]['startedUptime'] + D('.000001')
        rows[3]['startedUptime'] = rows[2]['finishedUptime'] + D('.000001')
        rows[3]['finishedUptime'] = rows[3]['startedUptime'] + D('.000001')
        assert rows[:2] == old[:2] and rows[4:] == old[4:]
        assert [r['contextSequence'] for r in rows if r['site'] != 'snapshot'] == [1, 3, 2, 4]
    join_control(o, 'F2 exact tighter two-middle-row reorder [1,3,2,4]', tighter_reorder, 'incomplete-complete-context-order')

    # Selection errors and constructor-forged anchors are both tested independently.
    anchor = fixture(o)[4]
    for role in PINNED_RAW:
        raws = [getattr(anchor, key + '_packet_raw') for key in PINNED_RAW]
        index = list(PINNED_RAW).index(role)
        bad = raws[index].replace(b'"generation":1', b'"generation":9', 1)
        assert len(bad) == len(raws[index]) and sha(bad) != sha(raws[index])
        raws[index] = bad
        try:
            o.select_original_action('v7-first-tab', *raws)
            raise AssertionError('wrong hash accepted')
        except o.Incomplete as error:
            assert str(error) == 'original-action-raw-' + role
        controls.append({'name': 'Wrong raw ' + role + ' hash rejected by selector', 'kind': 'selection', 'passed': True})
        forged = o.OriginalActionAnchor('v7-first-tab', *raws)
        join_control(o, 'Forged anchor revalidates ' + role + ' raw bytes',
                     lambda v, forged=forged: v.__setitem__(4, forged), 'incomplete-original-action-raw-' + role)
    for selection in ('future-runtime', '', True, 1, None):
        try:
            o.select_original_action(selection, anchor.before_packet_raw, anchor.after_packet_raw, anchor.witness_packet_raw)
            raise AssertionError('unselected action accepted')
        except o.Incomplete as error:
            assert str(error) == 'original-action-selection'
        controls.append({'name': 'Closed selection rejects ' + repr(selection), 'kind': 'selection', 'passed': True})
    join_control(o, 'Candidate expected fingerprints cannot replace anchor',
                 lambda v: v.__setitem__(4, {'beforeSHA256': PINNED_RAW['before'][1]}), 'incomplete-original-action-selection')

    for index, name, mutate in [
        (0, 'before extra original key', lambda value: value.update(reviewExtra=True)),
        (1, 'after missing original event list', lambda value: value.pop('events')),
        (1, 'after nested state label', lambda value: value['state'].update(label='review-substitution')),
        (0, 'before integer revision changed to Decimal', lambda value: value.update(focusContextRevision=D(value['focusContextRevision']))),
    ]:
        join_control(o, 'Full observation: ' + name, lambda v, i=index, m=mutate: m(v[i]),
                     'incomplete-original-' + ('before' if index == 0 else 'after') + '-observation')
    for endpoint in ('before', 'after'):
        join_control(o, 'Full witness ' + endpoint + ' endpoint label',
                     lambda v, e=endpoint: v[2][e]['elements']['next-focus'].update(label='changed'), 'incomplete-original-witness')
    def jointly_substitute(v):
        v[2]['after']['elements']['authored-toggle']['hasFocus'] = True
        v[-1]['keyboardWitness'] = copy.deepcopy(v[2])
    join_control(o, 'Witness and verdict joint substitution still fails pinned original', jointly_substitute, 'incomplete-original-witness')

    def decimal_change(v):
        with localcontext() as context:
            context.prec = 50
            old = v[3]['baselineUptime']; replacement = old + D('0.00000000000000001')
        assert float(old) == float(replacement) and old != replacement
        v[3]['baselineUptime'] = replacement
    join_control(o, 'Binding Decimal difference hidden by binary float', decimal_change, 'incomplete-original-binding')
    for name, field, replacement in [
        ('bool generation', 'generation', True), ('Decimal action index', 'actionIndex', D(1)),
        ('binary float baseline', 'baselineUptime', 948787.116983291),
        ('equal value unequal Decimal spelling', 'evaluatedUptime', D('948794.2310545410')),
        ('wrong case', 'case', 'future-runtime'), ('extra binding key', 'reviewExtra', True),
    ]:
        # Floats cannot be encoded by the adapter, so input immutability uses repr for this finite case.
        if type(replacement) is float:
            values = fixture(o); values[3][field] = replacement; before = repr(values)
            result = o.join(*values)
            assert result['supplemental']['captureStatus'] == 'incomplete-original-binding'
            assert repr(values) == before and result['originalVerdict'] is values[-1] and result['supplemental']['nativePass'] is False
            controls.append({'name': 'Binding ' + name, 'kind': 'join', 'passed': True, 'actual': 'incomplete-original-binding', 'nativePass': False})
        else:
            join_control(o, 'Binding ' + name, lambda v, f=field, r=replacement: v[3].update({f: r}), 'incomplete-original-binding')
    join_control(o, 'Original verdict witness consistency',
                 lambda v: v[-1]['keyboardWitness']['after']['elements']['authored-toggle'].update(hasFocus=True), 'incomplete-verdict-witness-consistency')
    join_control(o, 'Original verdict binding consistency',
                 lambda v: v[-1]['keyboardBinding'].update(evaluatedUptime=D('948794.231054542')), 'incomplete-verdict-binding-consistency')
    join_control(o, 'Original verdict pass claim rejected', lambda v: v[-1].update(passed=True), 'incomplete-original-verdict')
    join_control(o, 'Original verdict full shape change rejected', lambda v: v[-1].update(reviewExtra=True), 'incomplete-original-verdict')

    join_control(o, 'Diagnostic prefix metadata replacement',
                 lambda v: v[1]['focusSystemDiagnostic']['entries'][0]['controls'][0].update(isFocused=True), 'incomplete-entry-prefix')
    def prefix_decimal(v):
        entry = v[1]['focusSystemDiagnostic']['entries'][0]
        old = entry['startedUptime']; entry['startedUptime'] = D(str(old) + '0')
        assert old == entry['startedUptime'] and old.as_tuple() != entry['startedUptime'].as_tuple()
    join_control(o, 'Diagnostic prefix exact Decimal spelling', prefix_decimal, 'incomplete-entry-prefix')
    join_control(o, 'Callback source remains exact',
                 lambda v: v[1]['focusSystemDiagnostic']['entries'][2].update(site='carrier-callback'), 'incomplete-callback-source-time')

    for item in (0, 1, 2, 'other', None):
        validate_control(o, 'Pointer item state ' + repr(item), diagnostic([sample(1, D(1), item=item)]), [])
    validate_control(o, 'Unavailable primary focus system', diagnostic([sample(1, D(1), system=False)]), [])
    for scene in ('absent', 'unavailable', 'present'):
        validate_control(o, 'Windowless controller and optional scene ' + scene,
                         diagnostic([sample(1, D(1), item=None, system=False, window=False, scene=scene)]), [])
    validate_control(o, 'Entry count bound', diagnostic([sample(1, D(1))] * 129), [], 'entry-count')
    oversized = sample(1, D(1)); oversized['stage'] = 'x' * 4097
    validate_control(o, 'Encoded entry byte bound', diagnostic([oversized]), [], 'entry-size')
    validate_control(o, 'Whole-object byte bound', diagnostic([sample(i, D(i)) for i in range(1, 100)]), [], 'total-size')
    for name, mutate, expected in [
        ('saturating revision envelope', lambda value: value.update(revision=2147483648), 'bounded-envelope'),
        ('complete counter mismatch', lambda value: value.update(revision=2), 'complete-accounting'),
        ('declared truncation', lambda value: value.update(captureStatus='incomplete-total-size', dropped=1), 'incomplete-total-size'),
        ('oversized UTF8 group identifier', lambda value: value['entries'][0]['controls'][0].update(focusGroupIdentifier='é' * 65), 'group-identifier'),
        ('scene absent identity substitution', lambda value: value['entries'][0]['scene'].update(identity='review-illegal'), 'scene-absent'),
        ('nonmonotonic interval', lambda value: value['entries'][0].update(finishedUptime=D('.5')), 'entry-time'),
    ]:
        value = diagnostic([sample(1, D(1))]); mutate(value)
        validate_control(o, name, value, [], expected)
    # One finite retention failure and one already-saturated counter; no exhaustive producer loops.
    buffer = o.Buffer(); buffer.append(sample(1, D(1))); kept = copy.deepcopy(buffer.entries)
    buffer.append({'sequence': 2, 'oversized': 'x' * 4096}); buffer.append(sample(3, D(3)))
    assert buffer.entries == kept and buffer.status == 'incomplete-entry-size' and buffer.dropped == 2
    controls.append({'name': 'Failure retains prefix and never recovers', 'kind': 'buffer', 'passed': True,
                     'retainedEntries': len(buffer.entries), 'dropped': buffer.dropped, 'status': buffer.status})
    buffer = o.Buffer(); buffer.revision = 2147483647; buffer.dropped = 2147483647
    buffer.append(sample(1, D(1)))
    assert buffer.revision == 2147483647 and buffer.dropped == 2147483647 and buffer.status == 'incomplete-counter'
    controls.append({'name': 'Counters saturate and remain incomplete', 'kind': 'buffer', 'passed': True})

def main():
    before = verify_parents('before')
    source = CANDIDATE / 'inputs/source.tar.gz'
    assert sha(source.read_bytes()) == SOURCE_SHA
    with tarfile.open(source) as archive:
        members = archive.getmembers()
        assert len(members) == len({m.name for m in members}) == 40 and all(m.isfile() for m in members)
        manifest = {m.name: {'bytes': m.size, 'sha256': sha(archive.extractfile(m).read()), 'mode': m.mode} for m in members}
    write('source-members.json', {'archiveSHA256': SOURCE_SHA, 'members': manifest, 'changedSwiftMembers': []})
    o = imported('independent_review_focus_join', CANDIDATE / 'observation.py')
    execute(o)
    write('independent-controls.json', {'scope': 'Finite host-only frozen V7 replay controls with synthetic supplemental rows',
                                      'controlCount': len(controls), 'controls': controls, 'nativePass': False})
    argv = [sys.executable, '-B', '-m', 'unittest', '-v', 'test_observation', 'test_join_correction']
    completed = subprocess.run(argv, cwd=CANDIDATE, capture_output=True, text=True)
    (HERE / 'producer-tests.stdout').write_text(completed.stdout)
    (HERE / 'producer-tests.stderr').write_text(completed.stderr)
    write('producer-tests-command.json', {'argv': argv, 'cwd': str(CANDIDATE), 'exitCode': completed.returncode,
                                         'toolVersion': sys.version, 'scope': 'Bounded 38-method host regression rerun; no producer audit loops'})
    assert completed.returncode == 0
    assert '\nRan 38 tests ' in completed.stderr and completed.stderr.rstrip().endswith('OK')
    after = verify_parents('after')
    assert before == after
    assert not list(CANDIDATE.rglob('__pycache__')) and not list(HERE.rglob('__pycache__'))
    write('cleanup.json', {'ownedScratchCreated': False, 'ownedNativeInstancesCreated': 0,
                           'pythonCachesPresent': False, 'cleanupRequired': False,
                           'otherProjectsProcessesAndDataTouched': False,
                           'reason': 'Host Python -B only; no temporary directories or native instances created'})
    inputs = {}
    paths = ['AGENTS.md', 'PLAN.md', 'mixer-product-plan.md',
             'docs/apple-focus-system-observation-contract.md', 'docs/apple-focus-system-observation-review.md',
             'docs/apple-focus-system-join-correction.md',
             'verification/apple-focus-system-join-correction/observation.py',
             'verification/apple-focus-system-join-correction/test_observation.py',
             'verification/apple-focus-system-join-correction/test_join_correction.py',
             'verification/apple-focus-system-join-correction-review/review.py']
    for relative in paths:
        inputs[relative] = binding(ROOT / relative)
    for filename in ('0001-before-1.json', '0001-after-1.json', '0001-keyboard-witness-1.json'):
        relative = 'verification/apple-focus-system-join-correction/inputs/v7/' + filename
        inputs[relative] = binding(ROOT / relative)
    write('execution-inputs.json', {'sourceRevisionReportedByRoot': SOURCE_REVISION, 'files': inputs,
                                    'treeSHA256': sha(json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode())})
    result = {'schema': 1, 'status': 'accepted-frozen-replay-host-slice-only', 'passed': True,
              'observedUTC': datetime.now(timezone.utc).isoformat(),
              'scope': 'Independent narrow HOST-ONLY review of F1/F2 correction; frozen V7 replay only',
              'sourceRevisionReportedByRoot': SOURCE_REVISION, 'sourceArchiveSHA256': SOURCE_SHA,
              'sourceMembers': 40, 'changedSwiftMembers': [],
              'independentFiniteControlsPassed': len(controls), 'producerHostMethodsPassed': 38,
              'sealAudit': {k: {'members': v['members'], 'handoffSHA256': v['handoffSHA256']} for k, v in before.items()},
              'parentSealsExactBeforeAndAfter': True, 'findings': [],
              'originalVerdictUnchanged': True, 'originalOraclePassed': False,
              'originalFailingPredicates': ['actualNativeFocusTraversal'], 'nativePass': False,
              'frozenReplayHostAccepted': True, 'futureRuntimeIngestionAccepted': False,
              'nativeAccepted': False, 'gaAccepted': False, 'physicalPhones': 'disconnected-deferred',
              'compilerInvocations': 0, 'typecheckInvocations': 0, 'links': 0, 'appProducts': 0,
              'nativeQueries': 0, 'nativeAttempts': 0, 'uiOperations': 0, 'screenCaptures': 0,
              'networkOperations': 0, 'gitOperations': 0, 'rootTrackerEdits': 0,
              'prohibitedUnrelatedLanesRead': False,
              'tool': {'executable': sys.executable, 'version': sys.version, 'platform': platform.platform()},
              'command': {'argv': sys.argv, 'cwd': str(pathlib.Path.cwd()), 'scriptSHA256': sha(pathlib.Path(__file__).read_bytes())}}
    write('receipt.json', result)
    print(json.dumps({k: result[k] for k in ('status', 'passed', 'independentFiniteControlsPassed', 'producerHostMethodsPassed', 'nativePass')}, sort_keys=True))

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        write('failure.json', {'error': str(error), 'type': type(error).__name__, 'traceback': traceback.format_exc(),
                               'controlsCompleted': controls, 'toolVersion': sys.version, 'argv': sys.argv,
                               'scriptSHA256': sha(pathlib.Path(__file__).read_bytes())})
        raise
