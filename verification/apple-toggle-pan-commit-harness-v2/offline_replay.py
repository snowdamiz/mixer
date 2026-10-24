"""DIAGNOSTIC_ONLY historical observations; never a retroactive native pass."""
import datetime
import hashlib
import json
import pathlib
import sys
import commit_oracle as o

BASE=o.BASE;ROOT=o.ROOT
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
captures=BASE.parent/'apple-toggle-pan-commit/runtime/captures'
rows=[]
for file in sorted(captures.glob('*-after-*.json')):
    a=json.loads(file.read_bytes());raw=a['verdict']
    if raw['case'] not in o.SPECS:continue
    beforefile=file.with_name(file.name.replace('-after-','-before-'));b=json.loads(beforefile.read_bytes())['observation']
    result=o.verdict(raw['candidate'],raw['case'],raw['action'],b,a['observation'])
    rows.append({'case':raw['case'],'beforeCapture':str(beforefile.relative_to(ROOT)),'beforeCaptureSHA256':sha(beforefile),
                 'afterCapture':str(file.relative_to(ROOT)),'afterCaptureSHA256':sha(file),
                 'originalVerdict':raw,'diagnosticReevaluation':result})
assert len(rows)==16 and all(r['originalVerdict']['passed'] is False for r in rows)
value={'schema':'mixer.apple-toggle.pan-commit-harness-v2-offline-replay.1','status':'DIAGNOSTIC_ONLY',
       'command':[sys.executable,'-B',str(pathlib.Path(__file__).resolve().relative_to(ROOT))],
       'pythonVersion':sys.version,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'nativeAccepted':False,'retroactivePass':False,'nativeExecuted':False,'sourceClosureUnchanged':True,
       'sourceFiles':{str(p.relative_to(ROOT)):sha(p) for p in [pathlib.Path(__file__).resolve(),BASE/'commit_oracle.py',BASE/'cases.json']},
       'cases':rows,'diagnosticPredicatesSatisfied':sum(r['diagnosticReevaluation']['passed'] for r in rows),
       'scope':'Original native run remains failed/incomplete; fresh full43method native replay still required after root reviews this new seal'}
(BASE/'offline-replay.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({'status':value['status'],'cases':len(rows),'diagnosticPredicatesSatisfied':value['diagnosticPredicatesSatisfied'],
                  'failures':[{r['case']:[n for n,v in r['diagnosticReevaluation']['predicates'].items() if not v]} for r in rows if not r['diagnosticReevaluation']['passed']]}))
