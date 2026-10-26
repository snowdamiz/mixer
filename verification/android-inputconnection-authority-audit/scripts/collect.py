#!/usr/bin/env python3
"""Bounded source collection only. Never runs Android or product code."""
from pathlib import Path
import base64, hashlib, json, platform, shutil, subprocess, sys, urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1]
def identity(p):
    b=p.read_bytes(); return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
sources = [
 'AGENTS.md','mixer-product-plan.md',
 'docs/android-api28-v2-support-prerequisite.md',
 'docs/android-api28-v2-support-prerequisite-review.md',
 'verification/android-environment-platform-root-review/profile4-acceptance.json',
 *['native/android/app/src/dev/mixer/android/'+n+'.java' for n in (
 'NativeAppearanceViewsV2','NativeOwnerV2','OwnerLifecycleV2','NativeRenderer',
 'NativeEnvironmentV2','NativeEnvironmentPlatformV2','NativeCoordinatorV2',
 'NativeBridge','UiPacket','AppearanceDescriptorV2','AppearanceResolverV2','InstalledAppearanceV2')]]
records=[]
for rel in sources:
    src=ROOT/rel; dest=OUT/'inputs'/rel; dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,dest); records.append({'path':rel,**identity(dest)})
assert records[5]['sha256']=='a217d0b178869f3e5c3fc2d80f30f559a22c76a303195e62bfcb73d3cce91cce'
official=[]
base='https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/'
for rel in ['core/java/android/view/inputmethod/InputConnection.java',
            'core/java/android/view/inputmethod/InputConnectionWrapper.java',
            'core/java/android/view/inputmethod/BaseInputConnection.java',
            'core/java/com/android/internal/inputmethod/EditableInputConnection.java',
            'core/java/android/widget/TextView.java',
            'core/java/android/widget/Editor.java']:
    url=base+rel+'?format=TEXT'; req=urllib.request.Request(url,headers={'User-Agent':'Mixer-source-audit/1'})
    dest=OUT/'official/aosp36'/Path(rel).name
    try:
        response=urllib.request.urlopen(req,timeout=45); raw=response.read(); data=base64.b64decode(raw)
        dest.write_bytes(data)
        official.append({'source':url,'path':str(dest.relative_to(OUT)),**identity(dest),'status':response.status})
    except Exception as e:
        official.append({'source':url,'error':repr(e)})
sdk=Path('/opt/homebrew/share/android-commandlinetools/platforms/android-37.0')
for name in ['data/api-versions.xml','source.properties','package.xml']:
    src=sdk/name; dest=OUT/'official/sdk37'/Path(name).name; shutil.copyfile(src,dest)
    official.append({'source':str(src),'path':str(dest.relative_to(OUT)),**identity(dest)})
official.append({'source':str(sdk/'android.jar'),**identity(sdk/'android.jar')})
commands=[]
for args in [['/opt/homebrew/opt/openjdk/bin/javap','-version'],
 ['/opt/homebrew/opt/openjdk/bin/javap','-classpath',str(sdk/'android.jar'),'-p','-s','android.view.inputmethod.InputConnection','android.view.inputmethod.InputConnectionWrapper']]:
    run=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    n=len(commands)+1; (OUT/f'logs/javap-{n}.stdout.txt').write_text(run.stdout); (OUT/f'logs/javap-{n}.stderr.txt').write_text(run.stderr)
    commands.append({'argv':args,'exit':run.returncode,'stdout':f'logs/javap-{n}.stdout.txt','stderr':f'logs/javap-{n}.stderr.txt'})
receipt={'at':datetime.now(timezone.utc).isoformat(),'command':'python3 verification/android-inputconnection-authority-audit/scripts/collect.py',
 'python':sys.version,'platform':platform.platform(),'sources':records,'official':official,'commands':commands,
 'scope':'source/official metadata inspection only; no product execution, native launch, process inventory, capture, dependency or Git change',
 'precollection_failure':{'command':'/usr/libexec/java_home','exit':1,'stderr':'Unable to locate a Java Runtime; explicit existing Homebrew javap used instead'}}
(OUT/'collection.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'sources':len(records),'official':len(official),'fetch_failures':[x for x in official if 'error'in x],'commands':commands},indent=2))
