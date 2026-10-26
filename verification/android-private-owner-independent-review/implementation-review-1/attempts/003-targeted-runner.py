#!/usr/bin/env python3
"""Explicit actual-source host closure; imports only review-owned sealed child runner mechanics."""
from pathlib import Path
import importlib.util
import hashlib
import json
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
MECHANICS=ROOT/'verification/android-private-owner-independent-review/leaf-review-1/run_leaf_sanity.py'
spec=importlib.util.spec_from_file_location('independent_bounded_process_mechanics',MECHANICS)
mechanics=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mechanics)
JDK=Path('/opt/homebrew/opt/openjdk/bin')

def record(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def run(argv,stem,source):
    receipt=mechanics.run(argv,stem,source)
    receipt['scope']='independent targeted host execution of exact frozen candidate2 actual sources; not complete matrix or native qualification'
    receipt['owned_bounded_process_helper_sha256']=hashlib.sha256(MECHANICS.read_bytes()).hexdigest()
    stem.with_suffix('.command.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def main():
    out=HERE/f'targeted-{int(sys.argv[1]) if len(sys.argv)>1 else 1}';out.mkdir(exist_ok=True)
    roster=json.loads((ROOT/'verification/android-private-owner-independent-review/preaccess/site-input-map.json').read_text())
    leaves=json.loads((ROOT/'verification/android-private-owner-independent-review/leaf-review-1/admission/leaf-manifest-3.json').read_text())
    inputs=[HERE/'candidate-2/source'/name for name in roster['concrete_subjects']+sorted(leaves['files'])]
    inputs.append(HERE/'IndependentOwnerFocusReview.java')
    sources={str(p.relative_to(HERE)):record(p) for p in inputs}
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
            for n,name in enumerate(['dev.mixer.android.NativeOwnerV2','dev.mixer.android.NativeRenderer$1','dev.mixer.android.NativeEnvironmentV2']):
                run([str(JDK/'javap'),'-c','-p','-l','-s','-classpath',str(classes),name],out/f'02-bytecode-{n}',sources)
            for mode in ['lifecycle','fresh-input','terminal']:
                r=run([str(JDK/'java'),'-Xms16m','-Xmx256m','-Xss512k','-XX:ActiveProcessorCount=2','-cp',str(classes),'dev.mixer.android.IndependentOwnerFocusReview',str(HERE),mode],out/('03-'+mode),sources)
                outcomes.append(dict(mode=mode,exit_code=r['exit_code']))
                print(json.dumps(outcomes[-1]),flush=True)
    assert not any(scratch_parent.iterdir());scratch_parent.rmdir()
    (out/'cleanup.json').write_text(json.dumps(dict(owned_children_reaped=True,exclusive_scratch_removed=True,native_or_capture_started=False,scope='exact frozen Java actual-source host target; matrix incomplete',outcomes=outcomes),indent=2)+'\n')

if __name__=='__main__':main()
