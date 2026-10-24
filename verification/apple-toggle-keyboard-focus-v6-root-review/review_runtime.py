"""Audit terminal diagnostic, exact replay and all-outcome native cleanup."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
P=ROOT/'verification/apple-toggle-keyboard-focus-v6-preparation'
D=P/'runtime'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=read(D/'runtime-verdict.json'); l=read(D/'lifecycle.json'); s=read(D/'xctest-summary.json')
replay=read(OUT/'runtime-replay.stdout')
assert r['settingsDiagnostic']==replay['settingsDiagnostic']
assert r['diagnosticCompleted'] and r['setupEvidenceComplete'] and not r['settingsDiagnostic']['setupObservationSatisfied']
assert r['xcodebuildExitCode']==65 and r['bridgeFailures']==[]
assert r['applicationCasesExecuted']==0 and not r['expectedDiagnosticQualificationBoundary']
assert (s['totalTestCount'],s['passedTests'],s['failedTests'],s['skippedTests'])==(1,0,1,0)
assert 'Full Keyboard Access did not enable' in s['testFailures'][0]['failureText']
assert all(x['passed'] for x in r['cleanupResults']) and len(r['cleanupResults'])==5
assert l['cleanedUp'] and l['ownedDeviceAbsent'] and l['ephemeralWorkspaceAbsent']
assert not Path(l['ephemeralWorkspace']['path']).exists()
states=lambda snapshot:{x['udid']:x['state'] for items in snapshot['devices'].values() for x in items}
assert states(l['before'])==states(l['after']) and l['ownedSimulator'] not in states(l['after'])
assert l['beforeFrontends']==l['afterFrontends']==[]
commands=read(D/'commands.json')
assert [c['exitCode'] for c in commands if 'test-without-building' in c.get('argv',[])]==[65]
for operation in ['shutdown','delete']:
    assert [c['exitCode'] for c in commands if c.get('argv')==['/usr/bin/xcrun','simctl',operation,l['ownedSimulator']]]==[0]
attachments=read(D/'attachment-export.json')
assert attachments['passed'] and attachments['exitCode']==0
for name,info in attachments['files'].items():
    p=D/'attachments'/name
    assert p.is_file() and sha(p)==info['sha256'] and p.stat().st_size==info['bytes']
for route in r['settingsDiagnostic']['routeOpenedBindings']:
    assert route['tapFinishedUptime']<=route['captureStartedUptime'] and route['tapSequence']<route['sequence']
files={}
for p in sorted(D.rglob('*')):
    if p.is_file() and 'restored-app' not in p.relative_to(D).parts:
        assert not p.is_symlink()
        files[str(p.relative_to(ROOT))]={'sha256':sha(p),'bytes':p.stat().st_size}
captures=D/'captures'; ax=list(captures.glob('*-ax.txt')); png=list(captures.glob('*-png.png'))
review={'schema':'mixer.apple-toggle.keyboard-v6-root-runtime-review.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'accountableReviewer':'/root','sourceRevisionContext':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'selectionSHA256':sha(OUT/'selection.json'),'reviewScriptSHA256':sha(Path(__file__)),
    'packetSealSHA256':sha(P/'packet-seal.json'),'status':'completed-diagnostic-failed-setup-preserved',
    'actualEnvironment':s['devicesAndConfigurations'][0]['device'],'runtimeOuterExitCode':1,'xcodebuildExitCode':65,
    'officialTestResult':{'passed':0,'failed':1,'skipped':0,'failureText':s['testFailures'][0]['failureText']},
    'bridgeFailures':[],'diagnosticCompleted':True,'setupObservationSatisfied':False,
    'durableJournalRecords':len(list(captures.glob('0000-settings-*.json'))),'durableAXFiles':len(ax),'durableAXBytes':sum(p.stat().st_size for p in ax),'durablePNGFiles':len(png),
    'offlineReplay':{'argv':['python3','-B','verification/apple-toggle-keyboard-focus-v6-preparation/replay.py'],'exitCode':0,'matchesRuntimeSummary':True,'stdoutSHA256':sha(OUT/'runtime-replay.stdout'),'stderrSHA256':sha(OUT/'runtime-replay.stderr')},
    'cleanup':{'ownedDeviceAbsent':True,'ephemeralWorkspaceAbsent':True,'baselineStatesPreserved':True,'frontendsPreserved':True,'results':r['cleanupResults']},
    'interpretation':'Routing reached the Full Keyboard Access page and all three destination captures follow their respective completed taps. Public screenshot and AX evidence show the switch remained off. A composite-switch target is under source/evidence investigation; no hardware/Mac-lock cause or app behavior is inferred.',
    'applicationCasesUnrun':r['dependentCasesUnrun'],'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,
    'physicalPhones':'disconnected-deferred','evidenceFiles':files,
    'limitations':['Setup-only diagnostic, no app keyboard case executed.','Restored app excluded from evidence inventory; exact source/archive/product remain bound by preflight and seal.']}
(OUT/'runtime-review.json').write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({'reviewSHA256':sha(OUT/'runtime-review.json'),'evidenceFiles':len(files),'journalRecords':review['durableJournalRecords'],'cleanupPassed':True,'setupPassed':False}))
