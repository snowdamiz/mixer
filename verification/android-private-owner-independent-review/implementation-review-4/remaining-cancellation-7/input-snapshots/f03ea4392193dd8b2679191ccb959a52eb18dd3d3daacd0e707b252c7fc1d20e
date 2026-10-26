#!/usr/bin/env python3
"""Explicit actual-source host closure; imports only review-owned sealed child runner mechanics."""
from pathlib import Path
import importlib.util
import hashlib
import json
import sys
import tempfile
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
MECHANICS=ROOT/'verification/android-private-owner-independent-review/leaf-review-1/run_leaf_sanity.py'
spec=importlib.util.spec_from_file_location('independent_bounded_process_mechanics',MECHANICS)
mechanics=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mechanics)
JDK=Path('/opt/homebrew/opt/openjdk/bin')

def record(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def run(argv,stem,source):
    snapshots=stem.parent/'input-snapshots';snapshots.mkdir(exist_ok=True)
    retained={}
    for name,value in source.items():
        candidate=HERE/name
        if candidate.is_file():
            assert record(candidate)==value,(name,'source changed before execution')
            destination=snapshots/value['sha256']
            if not destination.exists():shutil.copy2(candidate,destination)
            retained[name]=str(destination.relative_to(HERE))
    python_inputs={}
    for item in sorted(HERE.glob('*.py')):
        value=record(item);destination=snapshots/value['sha256']
        if not destination.exists():shutil.copy2(item,destination)
        python_inputs[item.name]=dict(**value,retained=str(destination.relative_to(HERE)))
    receipt=mechanics.run(argv,stem,source)
    receipt['retained_source_bytes']=retained
    receipt['review_orchestrator_inputs']=python_inputs
    receipt['scope']='independent targeted host execution of exact frozen candidate5 actual sources; not complete matrix or native qualification'
    receipt['owned_bounded_process_helper_sha256']=hashlib.sha256(MECHANICS.read_bytes()).hexdigest()
    receipt['independent_runner_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    stem.with_suffix('.command.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def main():
    out=HERE/f'targeted-{int(sys.argv[1]) if len(sys.argv)>1 else 1}';out.mkdir(exist_ok=True)
    roster=json.loads((ROOT/'verification/android-private-owner-independent-review/preaccess/site-input-map.json').read_text())
    leaves=json.loads((ROOT/'verification/android-private-owner-independent-review/leaf-review-1/admission/leaf-manifest-3.json').read_text())
    inputs=[HERE/'candidate-5/source'/name for name in roster['concrete_subjects']+sorted(leaves['files'])]
    inputs.append(HERE/'IndependentOwnerFocusReview.java')
    sources={str(p.relative_to(HERE)):record(p) for p in inputs}
    for name in ['independent-descriptor.json','independent-packet-1.json','independent-packet-2.json','independent-helper-packet.json']:sources[name]=record(HERE/name)
    scratch_parent=HERE/'scratch';scratch_parent.mkdir(exist_ok=True)
    outcomes=[]
    with tempfile.TemporaryDirectory(prefix='focus-',dir=scratch_parent) as temp:
        scratch=Path(temp);empty=scratch/'empty';classes=scratch/'classes';empty.mkdir();classes.mkdir()
        listing=out/'explicit-sources.list';listing.write_text(''.join(str(p)+'\n' for p in inputs))
        compile_receipt=run([str(JDK/'javac'),'--release','17','-g','-Xlint:all','-Werror','-proc:none','-classpath',str(empty),'-sourcepath',str(empty),'-d',str(classes),'@'+str(listing)],out/'01-compile',sources)
        if compile_receipt['exit_code']!=0:
            print('COMPILE FAILED; retained exact stderr',flush=True)
        else:
            (out/'compiled-class-hashes.json').write_text(json.dumps({str(p.relative_to(classes)):record(p) for p in sorted(classes.rglob('*.class'))},indent=2)+'\n')
            for n,name in enumerate(['dev.mixer.android.NativeOwnerV2','dev.mixer.android.NativeRenderer$1','dev.mixer.android.NativeEnvironmentV2','dev.mixer.android.NativeRenderer$2','dev.mixer.android.NativeAppearanceViewsV2$NativeField$1','dev.mixer.android.NativeEnvironmentV2$Observer','dev.mixer.android.NativeRenderer','dev.mixer.android.NativeCoordinatorV2','dev.mixer.android.NativeAppearanceViewsV2$Record$1','dev.mixer.android.NativeAppearanceViewsV2$Gate','dev.mixer.android.NativeOwnerV2$Work']):
                run([str(JDK/'javap'),'-c','-p','-l','-s','-classpath',str(classes),name],out/f'02-bytecode-{n}',sources)
            modes=[] if sys.argv[2:]==['--bytecode-only'] else sys.argv[2:] or ['lifecycle','fresh-input','terminal']
            for mode in modes:
                r=run([str(JDK/'java'),'-Xms16m','-Xmx256m','-Xss512k','-XX:ActiveProcessorCount=2','-cp',str(classes),'dev.mixer.android.IndependentOwnerFocusReview',str(HERE),mode],out/('03-'+mode),sources)
                outcomes.append(dict(mode=mode,exit_code=r['exit_code']))
                print(json.dumps(outcomes[-1]),flush=True)
    assert not any(scratch_parent.iterdir());scratch_parent.rmdir()
    (out/'cleanup.json').write_text(json.dumps(dict(owned_children_reaped=True,exclusive_scratch_removed=True,native_or_capture_started=False,scope='exact frozen Java actual-source host target; matrix incomplete',outcomes=outcomes),indent=2)+'\n')

if __name__=='__main__':main()
