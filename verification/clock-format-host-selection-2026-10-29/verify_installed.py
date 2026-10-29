#!/usr/bin/env python3
import importlib.util, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
CLOCK=ROOT/'verification/shared-fixture-clock-controls-correction'
sys.path.insert(0,str(CLOCK))
from strict_guard import install, DENIED
install(HERE)
import resource
def denied_resource(*args,**kwargs):
 DENIED.append('resource call');raise RuntimeError('Source review prohibits resource calls')
resource.getrusage=denied_resource
from adopt_fixture import verify
adoption=verify(installed=True)
FMT=ROOT/'verification/swift-pin-bitmap-format-lint-host-correction'
sys.path.insert(0,str(FMT))
spec=importlib.util.spec_from_file_location('root_format_admission',FMT/'admit.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
manifest,data=module.inputs()
assert len(data['baseline'])==len(data['candidate'])==136
assert (ROOT/'.github/workflows/swift-pin-bitmap-format-lint-admission.yml').read_bytes()==(FMT/'workflow.yml').read_bytes()
assert manifest['candidateTreeSHA256']=='674242606ec1f81e8bf53d6d10c0ae390c94c75e78d0a5c0e695bfb36b5eec20'
assert not DENIED
result={'schema':1,'adoptionInstalledJobVerified':True,'adoption':adoption,'formatWorkflowExact':True,'baselineMembers':136,'candidateMembers':136,'candidateTreeSHA256':manifest['candidateTreeSHA256'],'processSessionGroupSignalWaitSocketAttempts':DENIED,'runtimeRuns':0,'pythonVersion':sys.version}
(HERE/'root-controls.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:result[k] for k in ('adoptionInstalledJobVerified','formatWorkflowExact','baselineMembers','candidateMembers','runtimeRuns')},sort_keys=True))
