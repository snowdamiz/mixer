#!/usr/bin/env python3
"""Bounded direct actual-source matrix/discovery command orchestration; own code only."""
from pathlib import Path
import json
import sys
import tempfile
import run_targeted_review as runner

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def run(argv,stem,sources):
    result=runner.run(argv,stem,sources)
    result['independent_matrix_orchestrator_sha256']=runner.record(Path(__file__))['sha256']
    result['independent_matrix_input_hashes']={p.name:runner.record(p) for p in sorted(HERE.glob('matrix-*')) if p.is_file()}
    stem.with_suffix('.command.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    out=HERE/('matrix-discovery-'+str(int(sys.argv[1])));out.mkdir(exist_ok=True)
    scenarios=sys.argv[2:]
    assert scenarios
    roster=json.loads((HERE.parent/'preaccess/site-input-map.json').read_text())['concrete_subjects']
    leaves=json.loads((HERE.parent/'leaf-review-1/admission/leaf-manifest-3.json').read_text())['files']
    inputs=[HERE/'candidate-5/source'/name for name in roster+sorted(leaves)]+[HERE/'IndependentMatrixReview.java']
    sources={str(p.relative_to(HERE)):runner.record(p) for p in inputs}
    scratch_parent=HERE/'matrix-scratch';scratch_parent.mkdir(exist_ok=True);outcomes=[]
    with tempfile.TemporaryDirectory(prefix='actual-',dir=scratch_parent) as temp:
        scratch=Path(temp);classes=scratch/'classes';empty=scratch/'empty';classes.mkdir();empty.mkdir()
        listing=out/'explicit-sources.list';listing.write_text(''.join(str(p)+'\n' for p in inputs))
        result=run([str(runner.JDK/'javac'),'--release','17','-g','-Xlint:all','-Werror','-proc:none','-classpath',str(empty),'-sourcepath',str(empty),'-d',str(classes),'@'+str(listing)],out/'01-compile',sources)
        if result['exit_code']==0:
            (out/'compiled-class-hashes.json').write_text(json.dumps({str(p.relative_to(classes)):runner.record(p) for p in sorted(classes.rglob('*.class'))},indent=2)+'\n')
            for number,scenario in enumerate(scenarios):
                result=run([str(runner.JDK/'java'),'-Xms16m','-Xmx256m','-Xss512k','-XX:ActiveProcessorCount=2','-cp',str(classes),'dev.mixer.android.IndependentMatrixReview',str(HERE),'discover',scenario],out/f'02-{number:03d}-{scenario}',sources)
                outcomes.append(dict(scenario=scenario,exit_code=result['exit_code']));print(json.dumps(outcomes[-1]),flush=True)
        else:print('Independent matrix driver compile failed; exact diagnostics retained',flush=True)
    assert not any(scratch_parent.iterdir());scratch_parent.rmdir()
    (out/'cleanup.json').write_text(json.dumps(dict(owned_children_reaped=True,exclusive_scratch_removed=True,native_or_capture_started=False,outcomes=outcomes,scope='Actual-subject scenario discovery only; not full seven-case qualification'),indent=2)+'\n')


if __name__=='__main__':main()
