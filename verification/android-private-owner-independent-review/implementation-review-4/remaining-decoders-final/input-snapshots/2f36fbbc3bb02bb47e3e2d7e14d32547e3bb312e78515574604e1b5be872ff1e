#!/usr/bin/env python3
"""Bounded actual14+leaf3 closure for a named, explicitly review-owned independent source."""
from pathlib import Path
import json
import sys
import tempfile
import run_targeted_review as runner
HERE=Path(__file__).resolve().parent
name=sys.argv[1];assert name in ['IndependentV1Review','IndependentOwnerContractReview','IndependentRemainingReview']
out=HERE/sys.argv[2];out.mkdir(exist_ok=True)
roster=json.loads((HERE.parent/'preaccess/site-input-map.json').read_text())['concrete_subjects']
leaves=json.loads((HERE.parent/'leaf-review-1/admission/leaf-manifest-3.json').read_text())['files']
inputs=[HERE/'candidate-5/source'/n for n in roster+sorted(leaves)]+[HERE/(name+'.java')]
source={str(p.relative_to(HERE)):runner.record(p) for p in inputs}
for p in sorted(HERE.glob('*.json')):
    if p.name not in ['custody.json']:source[str(p.relative_to(HERE))]=runner.record(p)
for p in sorted((HERE/'remaining-inputs').glob('*')):source[str(p.relative_to(HERE))]=runner.record(p)
parent=HERE/'independent-subject-scratch';parent.mkdir()
with tempfile.TemporaryDirectory(dir=parent) as temp:
    scratch=Path(temp);classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir()
    listing=out/'explicit-sources.list';listing.write_text(''.join(str(p)+'\n' for p in inputs))
    result=runner.run([str(runner.JDK/'javac'),'--release','17','-g','-Xlint:all','-Werror','-proc:none','-classpath',str(empty),'-sourcepath',str(empty),'-d',str(classes),'@'+str(listing)],out/'01-compile',source)
    if result['exit_code']==0:
        (out/'compiled-class-hashes.json').write_text(json.dumps({str(p.relative_to(classes)):runner.record(p) for p in sorted(classes.rglob('*.class'))},indent=2)+'\n')
        result=runner.run([str(runner.JDK/'java'),'-Xms16m','-Xmx256m','-Xss512k','-XX:ActiveProcessorCount=2','-cp',str(classes),'dev.mixer.android.'+name,str(HERE)]+sys.argv[3:],out/'02-run',source)
    print(json.dumps(dict(subject=name,exit_code=result['exit_code'])))
assert not any(parent.iterdir());parent.rmdir();(out/'cleanup.json').write_text('{"owned_children_reaped":true,"exclusive_scratch_removed":true,"native_or_capture_started":false}\n')
