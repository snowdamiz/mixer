#!/usr/bin/env python3
"""Independent official-AST supplemental source identity index, not behavior proof."""
from pathlib import Path
import json
import tempfile
import run_targeted_review as runner

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def main():
    out=HERE/'source-call-index-1';out.mkdir(exist_ok=True)
    baseline=HERE.parent/'preaccess/baseline/native/android/app/src/dev/mixer/android'
    current=HERE/'candidate-4/source/native/android/app/src/dev/mixer/android'
    source=HERE/'SourceCallIndex.java'
    product=[folder/(name+'.java') for folder in [baseline,current] for name in ['NativeRenderer','NativeAppearanceViewsV2']]
    inputs={str(p.relative_to(ROOT)):runner.record(p) for p in [source]+product}
    scratch_parent=HERE/'index-scratch';scratch_parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ast-',dir=scratch_parent) as temp:
        scratch=Path(temp);classes=scratch/'classes';empty=scratch/'empty';classes.mkdir();empty.mkdir()
        r=runner.run([str(runner.JDK/'javac'),'--release','17','-g','-Xlint:all','-Werror','-proc:none','-classpath',str(empty),'-sourcepath',str(empty),'-d',str(classes),str(source)],out/'01-compile-tool',inputs)
        assert r['exit_code']==0
        (out/'tool-class-hashes.json').write_text(json.dumps({str(p.relative_to(classes)):runner.record(p) for p in classes.rglob('*.class')},indent=2)+'\n')
        r=runner.run([str(runner.JDK/'java'),'-Xms16m','-Xmx256m','-Xss512k','-XX:ActiveProcessorCount=2','-cp',str(classes),'SourceCallIndex']+[str(p) for p in product],out/'02-index-sources',inputs)
        assert r['exit_code']==0
    assert not any(scratch_parent.iterdir());scratch_parent.rmdir()
    (out/'cleanup.json').write_text(json.dumps(dict(owned_tool_children_reaped=True,exclusive_scratch_removed=True,product_subjects_compiled_or_executed=False,scope='official javac AST parse of pinned source identity only'),indent=2)+'\n')
    rows=[json.loads(line) for line in (out/'02-index-sources.stdout').read_text().splitlines()]
    roster=json.loads((HERE.parent/'preaccess/inputs/verification/android-private-owner-effect-roster-amendment/required-host-roster.json').read_text())['baseline_callback_barriers']
    bindings=[];remaining=[]
    for item in roster:
        old=[row for row in rows if '/preaccess/baseline/' in row['source'] and row['source'].endswith(Path(item['source']).name) and row['line']==item['line'] and row['column']==item['column']]
        if len(old)!=1:
            remaining.append(dict(id=item['id'],reason='baseline AST anchor mismatch',matches=len(old)));continue
        old=old[0]
        key=lambda row:(row['classes'],row['methods'],row['select'])
        prior=[row for row in rows if '/preaccess/baseline/' in row['source'] and key(row)==key(old)]
        matches=[row for row in rows if '/candidate-4/source/' in row['source'] and key(row)==key(old)]
        ordinal=prior.index(old)
        if len(prior)!=len(matches):
            remaining.append(dict(id=item['id'],reason='semantic-region occurrence count changed',old=len(prior),current=len(matches),baseline=old,candidates=matches));continue
        bindings.append(dict(id=item['id'],baseline=old,current=matches[ordinal],ordinal_in_same_region=ordinal+1,
            mapping_scope='AST identity candidate; actual runtime descriptor/BCI/caller discrimination still required'))
    (out/'baseline-mapping.json').write_text(json.dumps(dict(schema=1,scope='Supplemental source identity only; no qualified site rows',baseline_sites=len(roster),mapped=len(bindings),unresolved=remaining,bindings=bindings),indent=2)+'\n')
    print(json.dumps(dict(status='supplemental-AST-source-index',calls=len(rows),mapped=len(bindings),unresolved=len(remaining),product_tests=0)))


if __name__=='__main__':main()
