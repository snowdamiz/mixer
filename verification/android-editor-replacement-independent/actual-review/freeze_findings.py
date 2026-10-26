#!/usr/bin/env python3
from pathlib import Path
import datetime, hashlib, json, shutil
D=Path(__file__).resolve().parent
T=D/'findings-focus-history';T.mkdir(exist_ok=False)
def copy(src,dst):
    target=T/dst;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(D/src,target)
for name in ['focus-history-requirements.md','source-verification.json','producer-seal.json','root-custody.json']:
    copy(name,name)
for name in ['AdditionalReplacementControls.java','ReplacementReviewControls.java','DescriptorClosure.java']:
    copy('independent-controls-6/source/'+name,'controls/'+name)
for name in ['receipt.json','compile.stdout','compile.stderr','blurred-A-replacement.stdout','blurred-A-replacement.stderr','focused-B-echo-after-A-blur.stdout','focused-B-echo-after-A-blur.stderr']:
    copy('independent-controls-6/'+name,'execution/'+name)
for name in ['NativeAppearanceViewsV2.java','NativeRenderer.java']:
    copy('frozen/source/'+name,'source/'+name)
for name in ['source-map.json','class-map.json','receipt.json']:
    copy('frozen/runs/host-1/'+name,'complete-host-replay/'+name)
readme='''# Frozen focus-history finding packet

Two required compatibility controls fail against the exact root-released derivative. Root confirmed both behaviors must work; verdict changes-required. Read focus-history-requirements.md for observations, source loci and bounded prospective correction requirements. No producer edits or acceptance are selected here.

The complete source and host closure were independently admitted and replayed. The execution receipt binds exact JDK command arguments, source snapshots, output and reaped children. To retest an explicitly owned future complete-source host closure, compile controls/AdditionalReplacementControls.java against its classes with javac --release 17 -Xlint:all -Werror -proc:none and an empty sourcepath, then run dev.mixer.android.AdditionalReplacementControls with case blurred-A-replacement or focused-B-echo-after-A-blur and the pinned descriptor path. These controls require ordinary success and fail on this candidate. Keep the failed baseline output unchanged.

Controlled authored Android/JNI leaves are a JVM model. No native, UI, capture or process inventory was started or queried. Reflective helper access identifies real private fields; the two failing sequences themselves use ordinary focus/connection/accessibility/IME routes, not invariant corruption.
'''
(T/'README.md').write_text(readme)
members=[]
for path in sorted(T.rglob('*')):
    if path.is_file():
        data=path.read_bytes();members.append({'path':str(path.relative_to(T)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Two actual-source focus-history compatibility failures and prospective bounded correction requirements; no implementation edits','producer_seal_sha256':'4c906824fe5e2e925c3ad5ca7c4ae94ba3b1e7dd6c58e77805dd3862c165c9a3','verdict':'changes-required','members':members,'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members)}
out=json.dumps(seal,indent=2)+'\n';(T/'seal.json').write_text(out);print(json.dumps({'seal':str(T/'seal.json'),'sha256':hashlib.sha256(out.encode()).hexdigest(),'members':len(members),'bytes':seal['member_bytes']}))
