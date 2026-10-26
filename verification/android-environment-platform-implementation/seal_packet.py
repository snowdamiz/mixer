#!/usr/bin/env python3
"""Seal/check this bounded native candidate. Integrity is not support or release authority."""
import argparse,datetime,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PACKET=Path(__file__).resolve().parent
OWNED=[
 'native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java',
 'native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java',
 'native/android/tests/NativeEnvironmentV2ObserverHostTests.java',
 'native/android/tests/NativeEnvironmentPlatformV2HostTests.java',
 'native/android/tests/run-environment-platform-host.py',
 'native/android/tests/run-environment-observer-host.py',
 'native/android/tests/run-private-owner-host.py',
 'native/android/tests/run-private-owner-crosscompile.py',
 'docs/android-environment-platform-implementation.md',
]
OBSERVER_LEAVES=('android/app/Activity.java','android/app/UiModeManager.java','android/content/res/Configuration.java','android/content/res/Resources.java','android/os/LocaleList.java','android/provider/Settings.java','android/view/WindowInsets.java','android/util/TypedValue.java','android/view/View.java','android/view/accessibility/AccessibilityManager.java','dev/mixer/android/AppearanceGeometryV2.java','dev/mixer/android/ObserverHostProbe.java')
OWNED += ['native/android/tests/NativeEnvironmentV2ObserverHostLeaves/'+p for p in OBSERVER_LEAVES]
for prefix,probe in (('NativeOwnerV2HostLeaves','OwnerHostProbe'),('NativeOwnerV2ConcreteHostLeaves','ConcreteHostProbe')):
 OWNED += ['native/android/tests/'+prefix+'/'+s for s in ('android/os/LocaleList.java','android/provider/Settings.java','dev/mixer/android/'+probe+'.java')]
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def files():return sorted(OWNED+[str(p.relative_to(ROOT)) for p in PACKET.rglob('*') if p.is_file() and p.name!='manifest.json'])
def evidence():
 expected={'final-environment':'passed-host-only','final-A':'passed-host-only','final-B':'passed-host-only','attempt-7-cross':'passed-crosscompile-only'}
 for name,status in expected.items():
  receipt=json.loads((PACKET/name/'receipt.json').read_text())
  assert receipt['status']==status,(name,receipt['status'])
  assert receipt['source_stable'],name
  assert receipt['cleanup']['owned_scratch_removed'] and receipt['cleanup']['owned_children_reaped'],name
  assert not receipt['native_or_capture_processes_started_or_queried'],name
 for p in PACKET.glob('*/receipt.json'):
  receipt=json.loads(p.read_text());assert receipt['cleanup']['owned_scratch_removed'] and receipt['cleanup']['owned_children_reaped'],str(p)
 preserve=json.loads((PACKET/'canonical-preservation.json').read_text())
 assert len(preserve['checked'])==16 and all(r['matches'] and identity(ROOT/p)==r['expected'] for p,r in preserve['checked'].items())
 return {n:identity(PACKET/n/'receipt.json') for n in expected}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');a=parser.parse_args()
 receipts=evidence();manifest=PACKET/'manifest.json'
 if not a.check:
  assert not manifest.exists(),'frozen manifest already exists'
  selection=ROOT/'verification/android-environment-platform-root-review/selection.json'
  assert identity(selection)['sha256']=='55214c11fcf73b9a788421e70a99546f696a72b76183001ad3ed93e3639c6ba7'
  value={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,str(Path(__file__).relative_to(ROOT))],'python':sys.version,'context_revision':'fb4c8f074f1a3e5eb2b1b1a45b44f0fa61a7cc62','context_revision_is_inherited_not_live_git':True,'selection':identity(selection),'status':'frozen bounded A native implementation candidate for independent review; no profile acceptance','files':{p:identity(ROOT/p) for p in files()},'owned_source_paths':OWNED,'final_receipts':receipts,'source_projection':{'sdk_count':22,'sdk':'unchanged; separate profile lane verifies complete projection','adapter_count':23,'adapter':'updated NativeEnvironmentV2 + new NativeEnvironmentPlatformV2; other21 unchanged','profile_id_selected_by_root':'mixer.android-source-pair.4','profile_bytes_accepted':False,'descriptor_and_wires':'unchanged'},'checks':{'observer_cases':162,'platform_cases':131,'platform_assertions':671,'A_cases':222,'A_assertions':1180,'B_checks':14477,'class_signature_constant_pool_inspection':'passed','official_JDK_SDK_D8_compile':'passed compilation only','retained_failed_attempts':['attempt-1-environment','attempt-2-environment','attempt-5-B']},'pending':['Android API28..36 native class loading and runtime','API28..35 rendering support and library/editor/inset/value blockers','public V2 routing','physical phones and native accessibility/design parity','immutable published separate-repository FieldLog dogfood','OTA/signing/store/operations/accountable GA'],'native_or_capture_processes_started_or_queried':False,'git_operations':False,'new_dependencies':[]}
  save(manifest,value)
 value=json.loads(manifest.read_text());assert set(value['files'])==set(files()),'packet membership drift'
 for path,expected in value['files'].items():assert identity(ROOT/path)==expected,path
 assert value['final_receipts']==receipts
 print(json.dumps({'status':'PASS bounded native packet custody only','members':len(value['files']),'manifest':identity(manifest),'native_runtime_public_or_GA_accepted':False},sort_keys=True))
if __name__=='__main__':main()
