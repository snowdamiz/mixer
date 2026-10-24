"""Finite separate collector correction for the sealed serializer's sequence field.

The complete original oracle and collect() are retained. The three changes below
add sequence to both exact row schemas and enforce the actual bounded serializer
contract. No raw field is removed, and no native operation can be dispatched here.
"""
import difflib
import sys
from types import ModuleType
import review_support as support

ORIGINAL_SHA256 = '95dfbc590531c3874fc456fc845259c0a0f2d2a7d8ac84b11ecf7f15cc50067a'
CHANGES = (
    ('key-row-exact-schema',
     "TRACE_FIELDS={'stage','case','uptime','returned','action','keyCode','source','repeat','canceled','downTime','eventTime','deviceId'}",
     "TRACE_FIELDS={'stage','case','uptime','returned','action','keyCode','source','repeat','canceled','downTime','eventTime','deviceId','sequence'}"),
    ('mode-row-exact-schema',
     "set(mode)=={'stage','case','uptime','inTouchMode','rootInTouchMode','mainThread'}",
     "set(mode)=={'stage','case','uptime','inTouchMode','rootInTouchMode','mainThread','sequence'}"),
    ('both-serializer-sequences',
     '    for index,request in enumerate(requests):',
     "    for label,entries in (('key',trace),('mode',modes)):\n"
     '        for sequence,entry in enumerate(entries):\n'
     "            need(type(entry) is dict and type(entry.get('sequence')) is int and entry['sequence']==sequence,'native '+label+' trace contiguous integer sequence')\n"
     '    for index,request in enumerate(requests):'),
)


def derive(source=None):
    if source is None:
        source = (support.PRODUCER / 'keyboard_oracle.py').read_text()
    support.need(support.data_bind(source.encode())['sha256'] == ORIGINAL_SHA256, 'original keyboard oracle drift')
    for name, before, after in CHANGES:
        support.need(source.count(before) == 1, 'one finite correction site ' + name)
        source = source.replace(before, after, 1)
    return source


def load(corrected=True):
    source = derive() if corrected else (support.PRODUCER / 'keyboard_oracle.py').read_text()
    support.need(corrected or support.data_bind(source.encode())['sha256'] == ORIGINAL_SHA256, 'original collector drift')
    previous = sys.modules.get('support')
    try:
        # Supply only the three byte/JSON helpers actually called by collect().
        # This inert module has no runner, process, adb, emulator or shell API.
        inert = ModuleType('support')
        for name in ('data_bind', 'read_bytes', 'save'):
            setattr(inert, name, getattr(support, name))
        sys.modules['support'] = inert
        module = ModuleType('independent_offline_keyboard_oracle')
        module.__file__ = str(support.HERE / ('corrected_keyboard_oracle.py' if corrected else 'original_keyboard_oracle.py'))
        exec(compile(source, module.__file__, 'exec'), module.__dict__)
        return module
    finally:
        if previous is None:
            sys.modules.pop('support', None)
        else:
            sys.modules['support'] = previous


def adaptation():
    original = (support.PRODUCER / 'keyboard_oracle.py').read_text()
    corrected = derive()
    return {
        'schema': 1, 'originalSHA256': ORIGINAL_SHA256,
        'correctedSHA256': support.data_bind(corrected.encode())['sha256'],
        'finiteChanges': [{'name': name, 'occurrences': 1,
                           'before': before, 'after': after} for name, before, after in CHANGES],
        'original45CaseAndKeyboardPredicatesChanged': False,
        'rawExportModifiedOrFieldsStripped': False,
        'serializerSource': str((support.PRODUCER / 'fixture/ScrollTraceBuffer.java').relative_to(support.ROOT)),
        'serializerSourceBinding': support.bind(support.PRODUCER / 'fixture/ScrollTraceBuffer.java'),
        'diff': ''.join(difflib.unified_diff(original.splitlines(keepends=True), corrected.splitlines(keepends=True),
                                            fromfile='sealed-keyboard-oracle', tofile='separate-corrected-keyboard-oracle')),
    }


def replay(oracle, out, *, overrides=None, instrument=None, code=None):
    """Replay only the exact five completed export reads; never execute argv."""
    runtime = support.RUNTIME
    receipt = support.read(runtime / 'receipt.json')
    commands = {row['name']: row for row in receipt['commands']}
    expected = ['native-results-export'] + ['export-' + name for name in oracle.SCREENSHOTS]
    requests = []
    overrides = {} if overrides is None else overrides
    prefix = ['offline-evidence', 'exec-out', 'run-as', 'dev.mixer.android.authoredtogglekeyboardfixture', 'cat']

    def read_only(name, argv, allow_failure=False):
        index = len(requests)
        support.need(index < len(expected) and name == expected[index], 'finite offline replay read order')
        literal = 'toggle-supplement-results.json' if index == 0 else oracle.SCREENSHOTS[index - 1]
        support.need(argv == prefix + ['files/' + literal] and allow_failure is True, 'finite offline replay route')
        row = commands[name]
        payload = (runtime / row['output']).read_bytes()
        support.need(support.data_bind(payload)['sha256'] == row['sha256'], 'retained export command output drift')
        result, payload = overrides.get(name, (row['exitCode'], payload))
        requests.append({'name': name, 'literal': literal, 'exitCode': result, **support.data_bind(payload)})
        return result, payload

    if instrument is None:
        instrument = (runtime / 'actual-native-component.log').read_bytes()
    if code is None:
        code = commands['actual-native-component']['exitCode']
    metadata = support.read(runtime / 'source-identity-predispatch.json')
    result = oracle.collect(read_only, ['offline-evidence'], 'dev.mixer.android.authoredtogglekeyboardfixture',
                            out, metadata, code, instrument)
    support.need(len(requests) == len(expected), 'all finite retained exports replayed')
    return {'oracle': result, 'replayedReads': requests, 'newNativeCommandsExecuted': 0}
