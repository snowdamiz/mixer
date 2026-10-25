#!/usr/bin/env python3
"""Read-only sealed source/host evidence verifier. No subprocess/network/imports of upstream code."""
import hashlib, io, json, pathlib, sys, tarfile
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def stable(v):return (json.dumps(v,indent=2,sort_keys=True)+'\n').encode()
def read(name):return json.loads((HERE/name).read_bytes())
checks=[]
def check(name, condition):
    assert condition,name
    checks.append(name)
def archive(path):
    with tarfile.open(path) as t:
        ms=t.getmembers();check('archive regular unique safe members '+str(path),all(m.isfile() and not m.name.startswith('/') and '..' not in pathlib.PurePosixPath(m.name).parts for m in ms) and len({m.name for m in ms})==len(ms))
        return {m.name:t.extractfile(m).read() for m in ms}
bindings=read('input-bindings.json')
for name, binding in bindings.items():
    b=(ROOT/name).read_bytes();check('immutable input '+name,binding=={'bytes':len(b),'sha256':sha(b)})
check('accepted diagnosis hash',bindings['verification/apple-reference-focus-lifecycle-diagnosis/handoff.json']['sha256']=='0e54a5c61dbefe9908b53c1f1a5d96440187b3d9cd561395337e7a89f4896452')
check('accepted baseline hash',bindings['verification/apple-focus-system-observation/review-source-package.tar.gz']['sha256']=='d1262c1e16a4decdca0ecbfdc278b7eaa1282f47d68776bfdede235157019cda')
check('exact V8 result hash',bindings['verification/apple-focus-system-native-result/handoff.json']['sha256']=='0d4ff885c95e54386cd06e53794077defa7acac5cf63525583a8053f053c90de')
baseline=archive(ROOT/'verification/apple-focus-system-observation/review-source-package.tar.gz')
candidate=archive(HERE/'review-source-package.tar.gz')
manifest=read('source-manifest.json')
members={n:{'bytes':len(b),'sha256':sha(b)} for n,b in sorted(candidate.items())}
check('candidate exact member hashes',manifest['members']==members)
check('candidate archive and tree digest',manifest['sourceArchiveSHA256']==sha((HERE/'review-source-package.tar.gz').read_bytes()) and manifest['memberTreeSHA256']==sha(stable(members)))
check('40 baseline and 42 candidate members',len(baseline)==40 and len(candidate)==42)
changed=[n for n in sorted(baseline) if baseline[n]!=candidate[n]]
added=sorted(set(candidate)-set(baseline))
check('only one existing member changed',changed==manifest['changedMembers']==['accepted/source/Prototype/main.swift'])
check('two owned helpers added',added==manifest['addedMembers']==['accepted/source/Prototype/PassiveLifecycleData.swift','accepted/source/Prototype/PassiveLifecycleObserver.swift'])
check('39 unchanged members byte exact',sum(b==candidate[n] for n,b in baseline.items())==39)
old=baseline['accepted/source/Prototype/main.swift'].decode();new=candidate['accepted/source/Prototype/main.swift'].decode()
expected=old.replace('    let theme: UIThemeV2\n','    let theme: UIThemeV2\n    let passiveLifecycleObserver = PassiveLifecycleObserver()\n',1)
expected=expected.replace('                                                  controls: [self.toggle, self.referenceButton, self.nextButton])\n','                                                  controls: [self.toggle, self.referenceButton, self.nextButton])\n            self.passiveLifecycleObserver.sample(site: site, contextSequence: sequence)\n',1)
expected=expected.replace(', "focusSystemDiagnostic": FocusSystemObservation.shared.value]',', "focusSystemDiagnostic": FocusSystemObservation.shared.value, "passiveLifecycleDiagnostic": passiveLifecycleObserver.value]',1)
expected=expected.replace('        let window = UIWindow(frame: UIScreen.main.bounds); window.rootViewController = PrototypeController()\n','        let window = UIWindow(frame: UIScreen.main.bounds)\n        let controller = PrototypeController(); window.rootViewController = controller\n        controller.passiveLifecycleObserver.start(application: application, window: window)\n',1)
check('exact minimal main hook transformation',new==expected)
check('launch registration before original makeKeyAndVisible',new.index('controller.passiveLifecycleObserver.start')<new.index('window.makeKeyAndVisible()'))
check('original focus-system implementation untouched',baseline['accepted/source/Prototype/DiagnosticTrace.swift']==candidate['accepted/source/Prototype/DiagnosticTrace.swift'])
check('all original oracle actions and transport members untouched',all(baseline[n]==candidate[n] for n in baseline if n.startswith('accepted/harness/') or n.startswith('accepted/runtime/')))
contract=read('contract.json')
check('source member and bounds contract',contract['sourceArchiveMembers']==42 and contract['unchangedBaselineMembers']==39 and contract['maximumRows']==64 and contract['maximumEncodedBytes']==16384 and not contract['authoritative'] and not contract['atomic'])
check('actual future source closure recorded',contract['futureGenericBuild']['swiftSourceCount']==sum(n.endswith('.swift') for n in candidate) and not contract['futureGenericBuild']['selected'])
check('generic closure explicitly includes both helper files',len([n for n in candidate if n.startswith('accepted/source/Prototype/') and n.endswith('.swift')])==12)
source=candidate['accepted/source/Prototype/PassiveLifecycleData.swift'].decode();adapter=candidate['accepted/source/Prototype/PassiveLifecycleObserver.swift'].decode()
check('shared Foundation source no UIKit import','import UIKit' not in source and source.startswith('import Foundation\n'))
check('closed schema reservation source retained','rowSchema' in source and 'mixer.apple-toggle.passive-lifecycle-row.1' in source and 'reserve: true' in source and 'Self.encodedField(envelope(rows: next, reserve: true))' in source)
check('passive weak synchronous adapter shape','[weak self, faults]' in adapter and 'queue: nil' in adapter and 'guard Thread.isMainThread' in adapter and 'window.windowScene' in adapter)
check('new sources no active input or scheduling',all(token not in source+adapter for token in ['Timer(', 'scheduledTimer', 'asyncAfter', 'Thread.sleep', 'Task.sleep', 'requestFocus', 'setNeedsFocusUpdate', 'updateFocusIfNeeded', 'makeKeyAndVisible', 'connectedScenes', '.windows', 'sendAction', 'typeKey']))
receipt=read('host-tests/receipt.json');commands=read('host-tests/commands.json')
check('host receipt passed against exact candidate archive',receipt['passed'] and receipt['sourceArchiveSHA256']==manifest['sourceArchiveSHA256'])
check('shared Foundation file actually host tested',receipt['testedSources']['accepted/source/Prototype/PassiveLifecycleData.swift']==members['accepted/source/Prototype/PassiveLifecycleData.swift'])
b=(HERE/'HostTests.swift').read_bytes();check('exact host test source bound',receipt['testedSources']['HostTests.swift']=={'bytes':len(b),'sha256':sha(b)})
check('finite host methods and byte result',receipt['summary']['passed'] and receipt['summary']['checks']==116 and receipt['summary']['maximumTestFieldBytes']<=16384)
check('native and UIKit remain unrun',not receipt['uikitCompiled'] and receipt['genericSimulatorBuilds']==receipt['nativeExecutions']==receipt['nativeQueries']==0)
check('host commands only version compile Foundation and test',[c['name'] for c in commands]==['swift-version','compile-foundation-host','execute-foundation-host'])
for c in commands:
    check('command terminal success '+c['name'],c['exitCode']==0 and not c['timedOut'])
    for stream in ['stdout','stderr']:
        check('bound output '+c['name']+' '+stream,sha((HERE/'host-tests'/(c['name']+'.'+stream)).read_bytes())==c[stream+'SHA256'])
    check('command bound candidate '+c['name'],c['sourceArchiveSHA256']==manifest['sourceArchiveSHA256'])
check('owned host scratch cleaned',receipt['ownedHostScratchRemoved'] and not (HERE/'.host-work').exists())
check('owned source scratch cleaned',not (HERE/'scratch').exists())
historical=read('history/host-tests-readable-rows/receipt.json')
check('historical 109 methods retained',historical['passed'] and historical['summary']['checks']==109)
check('historical exact source archive retained',sha((HERE/'history/readable-rows-source-package.tar.gz').read_bytes())==historical['sourceArchiveSHA256'])
check('historical exact test source retained',sha((HERE/'history/HostTests-readable-rows.swift').read_bytes())==historical['testedSources']['HostTests.swift']['sha256'])
refs=read('official/bindings.json');check('14 pinned official references',len(refs)==14)
for ref in refs:
    b=(ROOT/ref['path']).read_bytes();check('official data '+ref['path'],ref['url'].startswith('https://developer.apple.com/') and len(b)==ref['bytes'] and sha(b)==ref['sha256'])
result=json.loads((ROOT/'verification/apple-focus-system-native-result/result.json').read_bytes())
check('historical Settings pass Tab failure preserved',result['officialMethods']=={'test000PublicSettingsFullKeyboardAccess':'Passed','test010ReferenceFirstTab':'Failed'} and not result['nativePassed'])
check('no native or GA acceptance in contract',not contract['gaAccepted'] and contract['physicalPhones']=='disconnected-deferred' and contract['historicalNativeResult']['xcodeExitCode']==65)
if (HERE/'handoff.json').exists():
    sealed=read('handoff.json')
    for name,member in sealed['members'].items():
        b=(ROOT/name).read_bytes();check('sealed member '+name,member=={'bytes':len(b),'sha256':sha(b)})
    actual={str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p.name!='handoff.json'}|{'docs/apple-passive-lifecycle-observer.md'}
    check('sealed exact ownership file closure',set(sealed['members'])==actual)
print(json.dumps({'schema':1,'passed':True,'checks':len(checks),'inputFiles':len(bindings),'sourceMembers':len(candidate),'unchangedSourceMembers':39,'sourceArchiveSHA256':manifest['sourceArchiveSHA256'],'hostMethods':receipt['summary']['checks'],'uikitCompiled':False,'nativeExecution':False,'gaAccepted':False,'scope':'Read-only source archive, immutable-input and finite host-evidence consistency; source-shape checks do not prove UIKit behavior'},sort_keys=True))
