from pathlib import Path
import hashlib, json, shutil, signal

S=Path(__file__).resolve().parent;Q=S.parent;R=Q.parents[1];D=S/'full-candidate-v1'
OUT=D/'selected-original-behavior-roster.json'
if OUT.exists():raise SystemExit('retained original roster exists')
signal.alarm(60)
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
review=R/'verification/android-editor-preservation-membership-independent/actual-review'
assert ident(review/'review-seal.json')['sha256']=='8d51b0e6d04b152621e9e6f9ad3b6c46b3301853ed5d0c545fd4781a66c36c6d'
custody=json.loads((S/'selected-support-custody.json').read_bytes())
assert custody['packets'][0]['closed_pathset'] and custody['packets'][0]['members_verified']==1297
shadow=S/'final-selected-support/frozen-focus';shadow.mkdir()
source=review/'independent-controls/FocusHistoryControls.java';destination=shadow/'FocusHistoryControls.java';shutil.copyfile(source,destination);assert ident(source)==ident(destination)
known={}
for p in sorted((Q/'passive-return-probe-v4/inputs/tests').glob('*.java'))+sorted(D.glob('*.java')):
 name=('dev.mixer.android.' if b'package dev.mixer.android;' in p.read_bytes() else '')+p.stem
 assert name not in known
 known[name]={'path':str(p.relative_to(R)),**ident(p)}
cases={};refused=[]
for run in ('host-1','controls-1','selected-2'):
 path=review/'runs'/run/'commands.json'
 for command in json.loads(path.read_bytes()):
  argv=command['argv']
  if Path(argv[0]).name!='java' or '-cp' not in argv:continue
  tail=argv[argv.index('-cp')+2:];name=tail[0];args=tail[1:]
  if command['exit']!=0:
   refused.append({'run':run,'command':command['name'],'class':name,'args':args,'scope':'Retained superseded failed historical assertion; never selected as passing.'});continue
  variant='frozen-focus' if command['name'].startswith('unchanged-FH-') else 'main'
  normalized=['<descriptor>' if value.endswith('/descriptor.json') else value for value in args]
  assert all(not value.startswith('/') for value in normalized),'unselected absolute original argument'
  key=(variant,name,tuple(normalized))
  if key not in cases:
   selected_source={'path':str(destination.relative_to(R)),**ident(destination)} if variant=='frozen-focus' else known[name]
   cases[key]={'case_id':command['name'],'variant':variant,'class':name,'args':normalized,'source':selected_source,'historical_aliases':[],'scope':'Actual unchanged original main/assertions; semantic per-subject typed joins separately required.'}
  cases[key]['historical_aliases'].append({'run':run,'name':command['name'],'command_roster':str(path.relative_to(R)),**ident(path)})
value={'schema':1,'selected_review_seal':ident(review/'review-seal.json'),'cases':list(cases.values()),'unique_behavior_invocations':len(cases),'historical_passed_aliases':sum(len(x['historical_aliases'])for x in cases.values()),'historical_failed_excluded':refused,'source_rewrite':False,'selected_114_scope':'The frozen 114 count includes compiler/tool/disassembly commands. This behavior-only roster preserves exact passed JVM case aliases, separate frozen Focus source, and the independently selected identity/own-forward correction; no count-only substitution.'}
OUT.write_text(json.dumps(value,indent=2)+'\n');signal.alarm(0);print(json.dumps({'unique_behavior_invocations':len(cases),'historical_passed_aliases':value['historical_passed_aliases'],'historical_failed_excluded':len(refused)}))
