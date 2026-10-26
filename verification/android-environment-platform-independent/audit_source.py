#!/usr/bin/env python3
"""Offline official-API and exact protected-source audit; no release authority."""
import datetime,difflib,hashlib,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OWN=Path(__file__).resolve().parent
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def main():
 xml=Path('/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/data/api-versions.xml');root=ET.parse(xml).getroot()
 rows=[]
 def member(cls,kind,name,expected):
  c=root.find(f"class[@name='{cls}']");assert c is not None,cls
  m=c.find(f"{kind}[@name='{name}']");assert m is not None,(cls,name)
  floor=max(int(c.get('since','1')),int(m.get('since',c.get('since','1'))));assert floor==expected,(cls,name,floor)
  rows.append({'class':cls,'kind':kind,'signature':name,'floor':floor})
 member('android/view/WindowInsets','method','getInsets(I)Landroid/graphics/Insets;',30)
 member('android/view/WindowInsets$Type','method','systemBars()I',30)
 member('android/view/WindowInsets$Type','method','displayCutout()I',30)
 member('android/content/res/Configuration','field','fontWeightAdjustment',31)
 member('android/content/res/Configuration','field','FONT_WEIGHT_ADJUSTMENT_UNDEFINED',31)
 for name in ['getContrast()F','addContrastChangeListener(Ljava/util/concurrent/Executor;Landroid/app/UiModeManager$ContrastChangeListener;)V','removeContrastChangeListener(Landroid/app/UiModeManager$ContrastChangeListener;)V']:
  member('android/app/UiModeManager','method',name,34)
 for name in ['isHighContrastTextEnabled()Z','addHighContrastTextStateChangeListener(Ljava/util/concurrent/Executor;Landroid/view/accessibility/AccessibilityManager$HighContrastTextStateChangeListener;)V','removeHighContrastTextStateChangeListener(Landroid/view/accessibility/AccessibilityManager$HighContrastTextStateChangeListener;)V']:
  member('android/view/accessibility/AccessibilityManager','method',name,36)
 member('android/provider/Settings$Global','method','getFloat(Landroid/content/ContentResolver;Ljava/lang/String;)F',17)
 member('android/content/Context','method','getMainExecutor()Ljava/util/concurrent/Executor;',28)
 member('android/content/res/Configuration','method','getLocales()Landroid/os/LocaleList;',24)
 member('android/util/TypedValue','method','applyDimension(IFLandroid/util/DisplayMetrics;)F',1)
 base=ROOT/'native/android/app/src/dev/mixer/android';env=(base/'NativeEnvironmentV2.java').read_text();renderer=(base/'NativeRenderer.java').read_text();coordinator=(base/'NativeCoordinatorV2.java').read_text()
 assert 'Build.VERSION.SDK_INT < 36' in env and 'Build.VERSION.SDK_INT<36' in renderer
 c5=ROOT/'verification/android-private-owner-independent-review/implementation-review-4/candidate-5/source/native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java'
 delta=''.join(difflib.unified_diff(c5.read_text().splitlines(True),env.splitlines(True),fromfile='accepted-C5-Observer',tofile='bounded-A-Observer'))
 (OWN/'observer-delta.txt').write_text(delta)
 # Exact unchanged source statements are custody/static scope checks, not native effects evidence.
 interval='''int status = NativeBridge.commitV2(session, token);
                if (status == 0) {
                    renderer.finishV2(candidate, journal);'''
 assert interval in coordinator
 barrier_path=ROOT/'verification/android-private-owner-integration-implementation/barrier-map.json';barrier=json.loads(barrier_path.read_text());anchors=[]
 for row in barrier['records']:
  for anchor in row['candidates']:
   p=ROOT/row['source'];source=p.read_text();lines=source.splitlines(True)
   offset=sum(len(line) for line in lines[:anchor['line']-1])+anchor['column']-1
   assert source[offset:].startswith(anchor['text']),(row['baseline'],anchor)
   anchors.append({'baseline':row['baseline'],'source':row['source'],'line':anchor['line'],'column':anchor['column'],'text':anchor['text']})
 assert len(barrier['records'])==189
 descriptor=ROOT/'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'
 assert identity(descriptor)=={'bytes':9587,'sha256':'1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3'}
 value={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':sys.argv,'python':sys.version,'official_API_metadata':identity(xml),'API_members':rows,'API_member_count':len(rows),'both_pre36_guards_present':True,'default_descriptor':identity(descriptor),'barrier_map':identity(barrier_path),'barrier_records':len(barrier['records']),'exact_anchor_checks':len(anchors),'anchors':anchors,'unchanged_success_commit_to_finish_statements':True,'observer_delta':identity(OWN/'observer-delta.txt'),'capture_construction':'One private NativeEnvironmentV2 constructor, one Observer.capture mint; unchanged current/generation/sink/retirement code independently inspected','status':'passed source/API/custody only','native_runtime_or_public_or_OTA_or_GA_authority':False,'no_native_capture_UI_process_inventory_or_Git':True,'CLI_read_or_hashed':False}
 save(OWN/'source-audit.json',value);print(json.dumps({'status':'PASS offline exact-source/API audit only','official_API_members':len(rows),'barrier_records':len(barrier['records']),'exact_anchors':len(anchors),'native_or_release_authority':False}))
if __name__=='__main__':main()
