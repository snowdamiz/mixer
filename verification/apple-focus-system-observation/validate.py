#!/usr/bin/env python3
"""Read-only post-build host/source audit. No native/Git/network command."""
import difflib,hashlib,json,pathlib,sys,unittest
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent
ROOT=H.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def stable(v):return (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
checks=[]
def check(name,ok,detail=None):
 checks.append({'name':name,'passed':ok is True,'detail':detail})
 if ok is not True:raise AssertionError(name)
inputs=json.loads((H/'input-bindings.json').read_bytes())
for name,v in inputs['files'].items():
 raw=(H/name).read_bytes();check('exact accepted input '+name,len(raw)==v['bytes'] and sha(raw)==v['sha256'])
original=H/'inputs/accepted';candidate=H/'candidate/accepted'
base_files={str(p.relative_to(original)):p for p in original.rglob('*') if p.is_file()}
new_files={str(p.relative_to(candidate)):p for p in candidate.rglob('*') if p.is_file()}
check('exact40member candidate closure',set(base_files)==set(new_files) and len(new_files)==40)
changed=[n for n in sorted(base_files) if base_files[n].read_bytes()!=new_files[n].read_bytes()]
check('only selected2source members changed',changed==['source/Prototype/DiagnosticTrace.swift','source/Prototype/main.swift'],changed)
changes=json.loads((H/'source-changes.json').read_bytes())['changedMembers']
for name,binding in changes.items():
 check('bound candidate '+name,sha((candidate/'source/Prototype'/name).read_bytes())==binding['afterSHA256'])
trace=(candidate/'source/Prototype/DiagnosticTrace.swift').read_text();old_trace=(original/'source/Prototype/DiagnosticTrace.swift').read_text()
fragment=(H/'FocusSystemObservation.swift.fragment').read_text()
restored=trace.removesuffix(fragment).replace('    var focusSystemObserver: ((String, Int?) -> Void)?\n','').replace('        focusSystemObserver?(source + "-callback", focusContextRevision)\n','')
check('original strict trace and context implementation exact',restored==old_trace)
main=(candidate/'source/Prototype/main.swift').read_text();old_main=(original/'source/Prototype/main.swift').read_text()
weak='        DiagnosticTrace.shared.focusSystemObserver = { [weak self] site, sequence in\n            guard let self else { return }\n            FocusSystemObservation.shared.capture(site: site, contextSequence: sequence, stage: self.stage, controller: self,\n                                                  controls: [self.toggle, self.referenceButton, self.nextButton])\n        }\n'
restored=main.replace(weak,'').replace('        DiagnosticTrace.shared.focusSystemObserver?("snapshot", nil)\n        return [','        [').replace(', "focusSystemDiagnostic": FocusSystemObservation.shared.value','')
check('original snapshot content and controller behavior exact',restored==old_main)
added=[]
for name in changed:
 a=base_files[name].read_text().splitlines();b=new_files[name].read_text().splitlines()
 added.extend(line[1:] for line in difflib.unified_diff(a,b) if line.startswith('+') and not line.startswith('+++'))
new='\n'.join(added)
for forbidden in ['becomeFirstResponder','requestFocusUpdate','setNeedsFocusUpdate','updateFocusIfNeeded','setFocus','preferredFocusEnvironments','addTimer','scheduledTimer','asyncAfter','typeKey(','RunLoop','DispatchQueue']:
 check('no added focus/input/lifecycle scheduling mutation '+forbidden,forbidden not in new)
check('read-only getters and pointer comparison present','UIFocusSystem.focusSystem(for: environment)' in fragment and '(item as AnyObject) === $0' in fragment and 'scene.focusSystem' in fragment)
check('weak capture source exact',weak in main)
check('largest status and counters reserved','dropped: counterLimit, revision: counterLimit, status: "incomplete-entry-size"' in fragment)
check('unchanged publicTab/harness/runtime38members',len(base_files)-len(changed)==38)
tc=json.loads((H/'typecheck-attempt-3/receipt.json').read_bytes())
check('final complete source closure typechecked',tc['passed'] is True and tc['nativeAttempts']==tc['nativeQueries']==tc['appProducts']==0 and tc['scratchRemoved'] is True)
source_bindings=json.loads((H/'typecheck-attempt-3/source-bindings.json').read_bytes())
for path,v in source_bindings.items():check('final typechecked bytes '+path,sha((H/path).read_bytes())==v['sha256'])
commands=json.loads((H/'typecheck-attempt-3/commands.json').read_bytes())
check('full accepted/modifiedPrototype and exact4harness checked',set(c['name'] for c in commands)=={'swift-version','dependency-MixerCore','dependency-MixerUI','baseline-prototype','candidate-prototype','unchanged-harness-four'} and all(c['exitCode']==0 for c in commands))
for c in commands:
 for stream in ['stdout','stderr']:check('retained command output '+c['name']+'/'+stream,sha((H/'typecheck-attempt-3'/(c['name']+'.'+stream)).read_bytes())==c[stream+'SHA256'])
def warning_messages(path):return [line.split('warning: ',1)[1] for line in path.read_text().splitlines() if 'warning: ' in line]
check('modifiedPrototype warnings match exact baseline',warning_messages(H/'typecheck-attempt-3/baseline-prototype.stderr')==warning_messages(H/'typecheck-attempt-3/candidate-prototype.stderr'),warning_messages(H/'typecheck-attempt-3/candidate-prototype.stderr'))
check('no owned compiler scratch remains',not (H/'.owned-typecheck').exists())
suite=unittest.defaultTestLoader.discover(str(H),pattern='test_observation.py')
result=unittest.TextTestRunner(stream=sys.stderr,verbosity=2).run(suite)
check('host controls',result.wasSuccessful(),{'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)})
output={'schema':1,'passed':True,'scope':'Closed supplemental source/host slice only; synthetic fixtures and pinned-SDK typechecking; no app product or native run','checks':checks,'hostTests':result.testsRun,'originalOraclePassed':False,'originalFailingPredicates':['actualNativeFocusTraversal'],'settingsPreviouslyPassed':True,'nativeAttempts':0,'nativeQueries':0,'nativeAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred','candidateMembers':40,'changedMembers':changed,'candidateTreeSHA256':sha(stable({n:{'bytes':len(p.read_bytes()),'sha256':sha(p.read_bytes())} for n,p in sorted(new_files.items())}))}
sys.stdout.buffer.write(stable(output))
