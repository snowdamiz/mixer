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
    out=HERE/('matrix-execution-'+str(int(sys.argv[1])));out.mkdir(exist_ok=True)
    positions=[] if sys.argv[2:]==['--bytecode-only'] else [int(x) for x in sys.argv[2:]]
    assert positions or sys.argv[2:]==['--bytecode-only']
    variants=['clean','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback']
    roster=json.loads((HERE.parent/'preaccess/site-input-map.json').read_text())['concrete_subjects']
    leaves=json.loads((HERE.parent/'leaf-review-1/admission/leaf-manifest-3.json').read_text())['files']
    inputs=[HERE/'candidate-4/source'/name for name in roster+sorted(leaves)]+[HERE/'IndependentMatrixReview.java',HERE/'IndependentTraceEncoding.java']
    sources={str(p.relative_to(HERE)):runner.record(p) for p in inputs}
    scratch_parent=HERE/'matrix-scratch';scratch_parent.mkdir(exist_ok=True);outcomes=[]
    with tempfile.TemporaryDirectory(prefix='actual-',dir=scratch_parent) as temp:
        scratch=Path(temp);classes=scratch/'classes';empty=scratch/'empty';classes.mkdir();empty.mkdir()
        listing=out/'explicit-sources.list';listing.write_text(''.join(str(p)+'\n' for p in inputs))
        result=run([str(runner.JDK/'javac'),'--release','17','-g','-Xlint:all','-Werror','-proc:none','-classpath',str(empty),'-sourcepath',str(empty),'-d',str(classes),'@'+str(listing)],out/'01-compile',sources)
        if result['exit_code']==0:
            (out/'compiled-class-hashes.json').write_text(json.dumps({str(p.relative_to(classes)):runner.record(p) for p in sorted(classes.rglob('*.class'))},indent=2)+'\n')
            class_names=[str(p.relative_to(classes)).removesuffix('.class').replace('/','.') for p in sorted((classes/'dev/mixer/android').glob('*.class')) if not p.name.startswith('Independent') and not p.name.startswith('ConcreteHostProbe') and not p.name.startswith('NativeBridge')]
            for offset in range(0,len(class_names),4):
                run([str(runner.JDK/'javap'),'-c','-p','-l','-s','-classpath',str(classes)]+class_names[offset:offset+4],out/f'01-bytecode-{offset:03d}',sources)
            for position in positions:
                variant='all'
                result=run([str(runner.JDK/'java'),'-Xms16m','-Xmx256m','-Xss512k','-XX:ActiveProcessorCount=2','-cp',str(classes),'dev.mixer.android.IndependentMatrixReview',str(HERE),'matrix',str(position),variant],out/f'02-{position:03d}-{variant}',sources)
                outcomes.append(dict(position=position,variant=variant,exit_code=result['exit_code']));print(json.dumps(outcomes[-1]),flush=True)
        else:print('Independent matrix driver compile failed; exact diagnostics retained',flush=True)
    assert not any(scratch_parent.iterdir());scratch_parent.rmdir()
    (out/'cleanup.json').write_text(json.dumps(dict(owned_children_reaped=True,exclusive_scratch_removed=True,native_or_capture_started=False,outcomes=outcomes,scope='Independent exact-target seven-case execution; source tail/contract classification remains separate'),indent=2)+'\n')


if __name__=='__main__':main()
