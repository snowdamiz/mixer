"""Independent metadata mutation controls, deriving expectations from binding."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT/'overlay'
HERE = ROOT/'verification/plan-continuation-2026-11-07/source113-inspection-caller-r3'
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('r560_offline', ROOT/'verification/envelope-rust-1991-default-ci-adoption/offline_guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
__import__('metadata_guard').install(guard, HERE)
import adopt_envelope as a

def need(condition, text):
    if not condition:
        raise RuntimeError(text)

base = a.bind()
binding = json.loads((HERE/'binding.json').read_text())
actual = json.loads((HERE/'source-inputs.json').read_text())
owner = base.module_at('r560_controls_owner', ROOT/'scripts/ci/check-android-generated-java.py')
transition = binding['guest_ui_v2_transition']
predecessor = a.guest_ui_v2_predecessor(base, binding, actual, owner)
need((len(predecessor), owner.source_digest(predecessor)) == (transition['sourceCountBefore'], transition['sourceBefore']), 'Predecessor reconstruction differs')
need(predecessor == json.loads((OUT/'preimages/verification/plan-continuation-2026-11-07/source113-inspection-caller-r3/source-inputs.json').read_text()), 'Original immutable source116 not recovered')
negative = 0
for key in transition:
    mutation = copy.deepcopy(binding)
    mutation['guest_ui_v2_transition'][key] = None if transition[key] is not None else 'changed'
    try:
        a.guest_ui_v2_predecessor(base, mutation, actual, owner)
    except RuntimeError:
        negative += 1
    else:
        raise RuntimeError('Transition mutation admitted: '+key)
for row in transition['owningChanges']:
    for operation in ('omit','corrupt'):
        mutation = copy.deepcopy(actual)
        if operation == 'omit':
            del mutation[row['path']]
        else:
            mutation[row['path']]['sha256'] = '0'*64
        try:
            a.guest_ui_v2_predecessor(base, binding, mutation, owner)
        except RuntimeError:
            negative += 1
        else:
            raise RuntimeError('Owning mutation admitted')
for row in transition['rawPredecessors']:
    recovered = a.guest_ui_v2_predecessor_raw(base, ROOT/row['path'])
    original = OUT/'preimages'/row['path']
    need(recovered == original.read_bytes(), 'Exact historical raw preimage differs')
# Current tests continue deriving their expected identity from independent binding.
for name in ('test_rebind.py','test_source113.py'):
    original = OUT.parents[2]/'verification/plan-continuation-2026-11-07/source113-inspection-caller-r3'/name
    candidate = (HERE/name).read_text()
    baseline = original.read_text()
    if name == 'test_rebind.py':
        start = '    def test_successor_binds_current_source_and_actual_cli(self):'
        end = '    def test_each_changed_frozen_source_is_refused(self):'
        candidate = candidate[candidate.index(start):candidate.index(end)]
        baseline = baseline[baseline.index(start):baseline.index(end)]
    need(candidate == baseline, 'Structural current identity expectation changed')
original_binding = json.loads((OUT/'preimages/verification/plan-continuation-2026-11-07/source113-inspection-caller-r3/binding.json').read_text())
need({k:v for k,v in binding.items() if k not in ('source','guest_ui_v2_transition')} == {k:v for k,v in original_binding.items() if k != 'source'}, 'Historical binding changed')
need(guard.DENIED == [], 'Forbidden runtime attempt')
print(json.dumps({'passed':True,'negativeTransitionControls':negative,'exactSource116Recovered':True,'historicalBindingUnchanged':True,'runtimeDeniedAttempts':guard.DENIED,'optimization':sys.flags.optimize}))
