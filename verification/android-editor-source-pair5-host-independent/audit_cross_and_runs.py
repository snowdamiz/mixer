#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json
O=Path(__file__).resolve().parent;R=O.parents[1];P=R/'verification/android-editor-source-pair5-host-integration';C=P/'candidate'
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def check_commands(E):
 cs=json.loads((E/'commands.json').read_text())
 for c in cs:
  assert c['passed'] and c['child_reaped'] and not c['timeout'] and not c['output_limit_exceeded'] and c['timeout_seconds']==60
  assert c['output_limit_bytes_each_stream']==4000000
  for stream in ['stdout','stderr']:assert ident(E/(c['label']+'.'+stream))==c[stream]
 return cs
def check_sources(E):
 sm=json.loads((E/'source-map.json').read_text());freeze=json.loads((E/'source-freeze.json').read_text());assert freeze['frozen_before_tools'];assert ident(E/'source-map.json')==freeze['source_map'];projection=hashlib.sha256(''.join(n+'\0'+sm[n]['sha256']+'\n' for n in sorted(sm)).encode()).hexdigest();assert freeze['source_tree_sha256']==projection
 assert set(sm)=={str(p.relative_to(E/'inputs')) for p in (E/'inputs').rglob('*') if p.is_file()}
 for n,v in sm.items():assert ident(E/'inputs'/n)==v and (C/n).read_bytes()==(E/'inputs'/n).read_bytes()
 return {'files':len(sm),'sha256':projection,'source_map':ident(E/'source-map.json')}
def classmap(E,name):
 rows=json.loads((E/name).read_text());assert rows=={str(p.relative_to(E/'classes')):ident(p) for p in (E/'classes').rglob('*') if p.is_file()};return rows
cross=P/'runs/cross-3';cs=check_commands(cross);closure=json.loads((cross/'source-closure.json').read_text());r=json.loads((cross/'receipt.json').read_text());source=check_sources(cross);classes=classmap(cross,'classes.json');assert len(closure['java'])==24 and len(closure['swift_c_h'])==76 and source['files']==103
assert r['source_stable'] and r['status']=='passed-crosscompile-only' and r['cleanup']=={'native_or_capture_processes_created_or_queried':False,'owned_children_reaped':True,'owned_scratch_removed':True}
for path,v in {**r['actual_tool_identities'],**r['engine_tool_identities']}.items():assert ident(Path(path).resolve())==v
commands={x['label']:x for x in cs};compile=commands['compile']['argv'];assert ['--release','17','-Xlint:all','-Werror','-proc:none']==compile[2:7]
assert compile[compile.index('-classpath')+1]=='/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar';assert compile[compile.index('-sourcepath')+1].endswith('/empty')
assert compile[compile.index('-d')+2:]==[str(cross/'inputs'/n) for n in closure['java']]
dex=commands['dex']['argv'];assert dex[1:5]==['--min-api','28','--lib','/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar'];passedclasses=dex[dex.index('--output')+2:];assert {p.split('/classes/',1)[1] for p in passedclasses}==set(classes) and len(passedclasses)==len(classes)
dexmap=json.loads((cross/'dex.json').read_text());assert dexmap=={str(p.relative_to(cross/'dex')):ident(p) for p in (cross/'dex').rglob('*') if p.is_file()}
build=commands['swift-build']['argv'];assert build[build.index('--product')+1]=='MixerAndroidEngine' and build[build.index('--swift-sdk')+1]=='aarch64-unknown-linux-android28' and build[build.index('--jobs')+1]=='2' and build[build.index('-c')+1]=='release'
for name,v in json.loads((cross/'native-products.json').read_text()).items():assert ident(cross/'native-products'/name)==v
independent={}
for n,origin in [('A','A-3'),('B','B-4')]:
 E=O/'runs'/n;replay=check_commands(E);sources=check_sources(E);cm=classmap(E,'class-map.json');producer=classmap(P/'runs'/origin,'class-map.json');assert cm==producer
 receipt=json.loads((E/'receipt.json').read_text());assert receipt['source_stable'] and receipt['status']=='passed-host-only';assert receipt['cleanup']=={'native_instances_created':False,'owned_children_reaped':True,'owned_scratch_removed':True}
 independent[n]={'commands':len(replay),'sources':sources,'class_files':len(cm),'classmap_byteidentical_to_frozen_final':True,'maximum_command_seconds':max(x['elapsed_seconds'] for x in replay)}
default=O/'runs/B-default';rdefault=json.loads((default/'receipt.json').read_text());assert rdefault['status']=='failed' and rdefault['failure']['message'].startswith('default requires root-selected fresh qualified sourcepair5 matrix');assert not (default/'commands.json').exists() and not (default/'classes').exists();assert rdefault['source_stable'];check_sources(default)
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'exact offline cross receipts and fresh host replay bindings only','cross3':{'commands':len(cs),'sources':source,'java':24,'swift_c_headers_manifests':76,'class_files':len(classes),'dex_map':dexmap,'strict_compile_and_d8_explicit_sources_exact':True,'installed_executable_tool_identities_rechecked':True,'cross_build_repeated':False,'ordinary_generated_app_module_qualified':False,'maximum_command_seconds':max(x['elapsed_seconds'] for x in cs)},'fresh_host_runs':independent,'defaultB_fail_closed_before_tools':True,'required_prior_failures_retained_by_closed_producer_manifest':True,'full_integration_CI_native_OTA_GA_accepted':False}
(O/'cross-and-replay-audit.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print('PASS cross3 exact24/76/103inputs strictSDK37/D8/SwiftJNI receipts plus freshA/B source/classes identical and defaultB fail-closed')
