#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,shutil,datetime,re
D=Path(__file__).resolve().parent;F=D/'intermediate-historical-21';assert not F.exists();F.mkdir();inv=json.loads((D/'host-class-inventory.json').read_bytes());history=json.loads((D/'historical-dispositions.json').read_bytes());pending=[r for r in history['records'] if r['disposition']=='requires-semantic-disposition'];assert len(pending)==21
rows=inv['rows'];manual={'NativeRenderer:L225:C51:1':('NativeRenderer.java',459,'<init>','NativeAppearanceViewsV2$Record'),'NativeRenderer:L240:C56:1':('NativeRenderer.java',476,'<init>','NativeAppearanceViewsV2$Gate'),'NativeAppearanceViewsV2:L96:C37:1':('NativeAppearanceViewsV2.java',218,'<init>','TextView'),'NativeAppearanceViewsV2:L97:C39:1':('NativeAppearanceViewsV2.java',219,'<init>','NativeButton'),'NativeAppearanceViewsV2:L98:C42:1':('NativeAppearanceViewsV2.java',220,'<init>','NativeField'),'NativeAppearanceViewsV2:L99:C39:1':('NativeAppearanceViewsV2.java',221,'<init>','NativeSwitch'),'NativeAppearanceViewsV2:L100:C44:1':('NativeAppearanceViewsV2.java',222,'<init>','Group'),'NativeAppearanceViewsV2:L100:C89:2':('NativeAppearanceViewsV2.java',223,'<init>','NativeScroll'),'NativeAppearanceViewsV2:L102:C40:1':('NativeAppearanceViewsV2.java',227,'<init>','Group'),'NativeAppearanceViewsV2:L103:C83:1':('NativeAppearanceViewsV2.java',229,'<init>','TextView'),'NativeAppearanceViewsV2:L104:C87:2':('NativeAppearanceViewsV2.java',232,'<init>','TextView')}
for r in pending:
 old=r['historical_source_expression'];key=r['historical_id']
 if key in manual:
  source,line,name,owner=manual[key];matches=[a for a in rows if Path(a['source']).name==source and a['source_line']==line and a['target']['name']==name and a['target']['owner'].endswith(owner)];reason='Retain semantic constructor/branch subject. Bind freshly compiled constructor call rather than matching constructor spelling to <init>. Native constructor entry/final-return proof and seven-state behavior remain pending.'
 elif old.startswith('super.'):
  name=old.split('(')[0].split('.')[-1];arity=old.count(',')+1;matches=[a for a in rows if 'direct-editor' in a['categories'] and a['target']['owner']=='android/view/inputmethod/InputConnection' and a['target']['name']==name and (('TextAttribute;' in a['target']['descriptor'])==(arity==3) if name in ('setComposingText','setComposingRegion') else True)];reason='Replace obsolete inherited-wrapper native call with exact direct adapter lambda target, preserving overload descriptor. Region-attribute call has distinct descriptor even though controlled host leaf shares a two-argument implementation. No callback or scalar-success coverage is transferred.'
 else:
  name='setOnFocusChangeListener' if 'setOnFocusChangeListener' in old else 'setFilters' if 'setFilters' in old else 'setOnEditorActionListener' if 'setOnEditorActionListener' in old else 'setPadding'
  matches=[a for a in rows if Path(a['source']).name=='NativeAppearanceViewsV2.java' and a['class'].endswith('$Record') and a['target']['name']==name]
  if name=='setPadding':matches=[a for a in matches if a['source_line'] in (333,334)]
  reason='Retain native registration/setter subject with changed complete callback body or multiline expression. Current callback/lambda bodies and authority guards must be reviewed independently; spelling/line matching does not grant execution credit.'
 assert matches,(key,old)
 r['proposed_semantic_disposition']=reason;r['fresh_compiled_candidates']=matches;r['status']='root-review-pending; exact candidate identities supplied; no behavioral qualification'
 for a in matches:
  cf=next(c for c in inv['classes'] if c['class']==a['class']);dest=F/'classes'/Path(cf['file']).relative_to('runs/host-2/classes');dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists():shutil.copy2(D/cf['file'],dest)
for name in ('NativeRenderer.java','NativeAppearanceViewsV2.java','NativeEditorConnectionV2.java'):
 q=F/'accepted-source'/name;q.parent.mkdir(exist_ok=True);shutil.copy2(D/'inputs/accepted/source'/name,q)
for name in ('root-count-amendment.md','root-count-selection.json','audit-receipt.json','javap-independent-check.json','input-custody.json'):shutil.copy2(D/name,F/name)
(F/'findings.json').write_text(json.dumps({'schema':1,'status':'sealed-intermediate-semantic-candidate-finding','scope':'Exactly21 previously unresolved historical V2 source expressions, with fresh exact compiled identity candidates for root semantic review','candidate_source_tree':inv['product_tree'],'records':pending,'all21_have_fresh_compiled_identity_candidates':True,'historical_V2_total':189,'V1_controls_separate':5,'seven_state_or_native_qualification':False},indent=2)+'\n')
(F/'README.md').write_text('''# Intermediate semantic finding

This read-only packet binds all 21 unresolved historical source expressions to freshly parsed host class/method/JVM descriptor/BCI/opcode/callee/source-hash candidate identities. It proposes constructor branch preservation, changed listener/setter review, and replacement of obsolete wrapper calls by direct-adapter overloads. Root must review the semantic dispositions; neither line matching nor these compiled identities grants callback or behavior coverage.

Selected exact16 source tree: `a5e4888b96995bf768062bd9c2f1573dc440a4fe22270a205ab5550e79f625e4`. The complete static inventory separately has 209 product classes and 7,252 invocation sites per host/SDK compile. Actual host traces observed 697 sites, 89 in the direct adapter, across 62 unchanged shape/behavior commands. All five original V1 controls execute separately. Exact SDK descriptor SET38, SDK37/D8 min-api28 and 22 integrity negatives pass. Runtime compiler is OpenJDK25.0.4.1 with `--release17`, not JDK17 runtime evidence.

The full per-boundary seven-state/callback/failure-state qualification remains active and incomplete. Native runtime, exact OOME injection, API-specific runtime linkage, Swift/JNI app integration, OTA, public V2 and GA remain pending. No UI, emulator/simulator/device or capture process was used or inventoried.
''')
def identity(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
members=[{'path':str(p.relative_to(F)),**identity(p)} for p in sorted(F.rglob('*')) if p.is_file()];(F/'manifest.json').write_text(json.dumps({'members':members},indent=2)+'\n');seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'read-only-intermediate-finding; full-qualification-incomplete','manifest':identity(F/'manifest.json'),'members':members+[{'path':'manifest.json',**identity(F/'manifest.json')}],'root_semantic_acceptance_pending':True,'native_OTA_or_GA_accepted':False};(F/'seal.json').write_text(json.dumps(seal,indent=2)+'\n');print(str(F),'members',len(seal['members']),'bytes',sum(m['bytes'] for m in seal['members']),'seal',identity(F/'seal.json'))
