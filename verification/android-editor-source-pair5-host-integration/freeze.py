#!/usr/bin/env python3
"""Freeze the complete owned partial integration packet after final cleanup."""
from pathlib import Path
import datetime,hashlib,json,shutil
D=Path(__file__).resolve().parent
if (D/'seal.json').exists():raise SystemExit('Already frozen; create a separately owned derivative')
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,value):p.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
for cache in sorted(D.rglob('__pycache__'),reverse=True):
 if cache.is_dir():shutil.rmtree(cache)
C=D/'candidate';bindings=json.loads((D/'final-candidate-bindings.json').read_text())
actual={str(p.relative_to(C)):ident(p) for p in sorted(C.rglob('*')) if p.is_file()}
assert set(bindings)==set(actual)
for name,value in actual.items():assert all(bindings[name].get(k)==v for k,v in value.items()),name
passes={}
for name in ('A-3','B-4','cross-3','original-pc-c16'):
 E=D/'runs'/name;r=json.loads((E/'receipt.json').read_text());assert r['status'].startswith('passed'),name
 assert all(v is (False if k.startswith('native') else True) for k,v in r['cleanup'].items()),(name,r['cleanup'])
 if 'source_stable' in r:assert r['source_stable'],name
 commands=json.loads((E/'commands.json').read_text());assert all(c['passed'] for c in commands),name
 assert all(c['timeout_seconds']==60 and c['output_limit_bytes_each_stream']==4_000_000 and c['child_reaped'] for c in commands),name
 passes[name]={'receipt':ident(E/'receipt.json'),'commands':len(commands),'maximum_child_seconds':max(c['elapsed_seconds'] for c in commands),'class_map':ident(E/'class-map.json') if (E/'class-map.json').exists() else ident(E/'classes.json') if (E/'classes.json').exists() else None}
rows=json.loads((D/'runs/B-4/imeControls-rows.json').read_text());familyrows=rows['familyRows'];keyrows=rows['sendKeyRefusals']
assert len(familyrows)==96 and len(keyrows)==6 and all(r['passed'] for r in familyrows+keyrows)
assert sum(r['injectedSuccessor'] for r in familyrows)==8
negative=D/'runs/B-default-fail-closed-2';r=json.loads((negative/'receipt.json').read_text());assert r['status']=='failed' and r['failure']['message'].startswith('default requires root-selected fresh qualified sourcepair5 matrix');assert not (negative/'classes').exists() and not (negative/'commands.json').exists()
failed={}
for name in ('A-1','B-1','B-2','B-3','cross-2'):
 E=D/'runs'/name;r=json.loads((E/'receipt.json').read_text());assert r['status']=='failed';failed[name]={'receipt':ident(E/'receipt.json'),'failure':r.get('failure'),'source_stable':r.get('source_stable')}
summary={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'ready-for-independent-partial-host-integration-review','scope':'A/B host migration, exact copied source custody and unsigned Java/D8/ordinary-engine-Swift/JNI evidence only','canonical_changes':False,'coherent_integration_accepted':False,'passes':passes,'actual_toolchain':'Homebrew JDK25.0.4.1; --release17 -Xlint:all -Werror -proc:none; empty host classpath/sourcepath; no -g; pinnedSDK37; D8min28; Swift6.3.3 Android28 ARM64','host_A':{'cases':222,'assertions':1180,'editor_busy_preservation_completion_callbacks_modeled':False},'host_B':{'main_assertions':1822,'family_rows':len(familyrows),'families':len(set(r['family'] for r in familyrows)),'states':sorted(set(r['state'] for r in familyrows)),'labeled_injected_successor_rows':sum(r['injectedSuccessor'] for r in familyrows),'direct_sendKey_refusal_rows':len(keyrows),'all_original_V1_method_bytes_preserved':True,'fresh_accepted_prepared_hostile_focus_membership_and_selected_own_forward_replay':True,'unchanged_original_PC_C16_freshly_passes':True},'required_original_failure_retained':'Original identity-matrix own forward native row remains actual exit1 at Record.cancelClaim; selected derivative and isolated native/commit controls are separate passes','preserved_failures':failed,'cross2_timeout':'Retained hard60s Swift build timeout; no bound increase; final sameflags cross3 succeeds after owned B JVM work finishes','default_matrix':'Actual final default refuses before tools, as required; explicit --skip-matrix recorded only for scoped development; fresh schema/checker/source16/descriptor38/class/BCI binding is a separately bound future derivative','pending':['fresh default compiled matrix source/class/descriptor/BCI/context binding','independent and root coherent integration acceptance','ordinary generated app-module consumers from CLI lane','native runtime IME/keyboard/focus/selection/composition/accessibility/TalkBack/OEM/API28-35/physical parity','immutable published external FieldLog packages','public V2/signing/store/OTA/operations/GA'],'native_ui_capture_or_process_inventory_started_or_queried':False}
save(D/'summary.json',summary)
# Record only source paths to promote after independent/root acceptance; product16 is root-owned.
targets=[]
for p in sorted((C/'native/android/tests').rglob('*')):
 if p.is_file():targets.append({'canonical_path':str(p.relative_to(C)),'candidate_path':str(p.relative_to(D)),**ident(p)})
save(D/'test-targets.json',{'schema':1,'targets':targets,'promotion_authority':'Root only after acceptance','product_sdk_bridge_engine_targets':[]})
# Nested original manifests/seals are actual packet members; only this packet's own two are excluded.
members=[{'path':str(p.relative_to(D)),**ident(p)} for p in sorted(D.rglob('*')) if p.is_file() and p not in (D/'manifest.json',D/'seal.json')]
manifest={'schema':1,'scope':'Complete closed owned partial Android source-pair5 host integration packet','member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),'members':members};save(D/'manifest.json',manifest)
projection=lambda rows:hashlib.sha256(''.join(r['path']+'\0'+r['sha256']+'\n' for r in rows).encode()).hexdigest()
seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':summary['status'],'scope':summary['scope'],'manifest':ident(D/'manifest.json'),'member_count':manifest['member_count'],'member_bytes':manifest['member_bytes'],'member_projection_sha256':projection(members),'candidate_projection_sha256':projection([{'path':n,**actual[n]} for n in sorted(actual)]),'summary':ident(D/'summary.json'),'default_compiled_matrix_binding_pending':True,'coherent_integration_or_native_OTA_GA_accepted':False};save(D/'seal.json',seal)
for row in members:assert ident(D/row['path'])=={k:row[k] for k in ('bytes','sha256')},row['path']
assert {str(p.relative_to(D)) for p in D.rglob('*') if p.is_file()}=={r['path'] for r in members}|{'manifest.json','seal.json'}
print(json.dumps({'seal':ident(D/'seal.json'),'manifest':seal['manifest'],'member_count':seal['member_count'],'member_bytes':seal['member_bytes'],'candidate_projection_sha256':seal['candidate_projection_sha256'],'scope':seal['scope']},indent=2))
