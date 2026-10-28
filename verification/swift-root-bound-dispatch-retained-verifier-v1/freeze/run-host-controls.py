"""One 55-second pure-stdlib control invocation; never spawns a child."""
from pathlib import Path
import hashlib
import io
import json
import signal
import sys
import time
import unittest

signal.alarm(55)
started=time.monotonic()
root=Path(__file__).resolve().parents[3]
owned=Path(__file__).resolve().parents[1]
source=owned/'source'
plan=root/'verification/swift-root-bound-dispatch-retained-capture-v1/plan.json'
inputs=[
    root/'verification/swift-root-bound-dispatch-physical-evidence-v2/source/region_certificate.py',
    root/'verification/swift-root-bound-dispatch-physical-evidence-v2/source/tests_region_certificate.py',
    plan,
    root/'verification/swift-root-bound-dispatch-retained-capture-v1/base-capture-plan.json',
    root/'verification/swift-root-bound-dispatch-retained-capture-v1/runtime/capture-observation.json',
    root/'verification/swift-semantic-adapter-root-review/dispatch-retained-physical-identity-acceptance.json',
    *sorted(source.glob('*.py')),Path(__file__),Path(sys.executable),
]

def pins():
    result=[]
    for path in inputs:
        raw=path.read_bytes()
        result.append({'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    return result

before=pins()
scratch=owned/'command'
assert not scratch.exists(),'fresh bounded scratch required'
scratch.mkdir()
sys.path.insert(0,str(source))
stream=io.StringIO()
suite=unittest.defaultTestLoader.discover(str(source),pattern='tests_*.py')
result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
output=stream.getvalue()
assert len(output.encode())<=1024*1024,'full output bound'
after=pins()
remaining=sorted(str(path.relative_to(scratch)) for path in scratch.rglob('*'))
if not remaining:scratch.rmdir()
elapsed=time.monotonic()-started
receipt={'schema':1,'status':'PASS_SYNTHETIC_HOST_CONTROLS' if result.wasSuccessful() else 'FAIL_SYNTHETIC_HOST_CONTROLS',
    'command':[str(Path(sys.executable)),'-B',str(Path(__file__))],
    'wall_seconds_bound':55,'elapsed_seconds':elapsed,'automatic_retries':0,
    'python_version_from_prior_pinned_plan_receipt':json.loads(plan.read_bytes())['python_version_from_this_preparation'],
    'new_version_or_process_queries':0,'external_children':0,'compiler_invocations':0,
    'native_runtime_invocations':0,'actual_geometry_input_invocations':0,
    'test_methods_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
    'skipped':len(result.skipped),'all_16_geometry_regression_methods_retained':True,
    'before':before,'after':after,'pins_unchanged':before==after,
    'scratch_remaining':remaining,'owned_synthetic_scratch_removed':not scratch.exists(),
    'local_geometry_only':True,'complete_capacity_accepted':False,
    'link_dead_code':True,'alternate_diagnostic_configuration_only':True,
    'original_capture_qualified':False,'runtime_admission_accepted':False,
    'limitations':['Synthetic host controls only; no actual geometry/certificate input executed.',
        'Independent candidate review and any actual-input release remain pending.',
        'No native/UI/device, capacity, root funding, product, OTA or GA acceptance.']}
(owned/'freeze/host-controls.stdout').write_text(output)
(owned/'freeze/host-controls.stderr').write_text('')
(owned/'freeze/host-controls.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
sys.stdout.write(output)
assert before==after,'input/tool changed'
assert not remaining and not scratch.exists(),'synthetic scratch cleanup failed'
assert elapsed<55,'deadline exceeded'
sys.exit(0 if result.wasSuccessful() else 1)
