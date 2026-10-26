#!/usr/bin/env python3
"""Apply independently source-reviewed callback/cleanup boundaries to lossless actual traces.

This classifies host evidence, not release authority. The selected contracts permit
already-entered framework work, valid original transaction work, consumed cleanup
and rollback. They forbid a new ordinary mutation from an expired live scope.
"""
from pathlib import Path
from collections import Counter
import json
from validate_matrix_traces import expand
HERE=Path(__file__).resolve().parent

def identity(frame):
    head,position=frame.rsplit('@',1);qualified,tail=head.split('(',1);name,method=qualified.rsplit('#',1)
    return name,method,'('+tail,int(position.split(':')[0])

def main():
    sites={row['id']:row for row in json.loads((HERE/'selected-site-input-map.json').read_text())['sites']}
    categories=Counter();rows=[];unknown=[]
    cleanup={('dev.mixer.android.NativeEnvironmentV2$Observer','cleanupAll'),('dev.mixer.android.NativeOwnerV2','removeWork'),('dev.mixer.android.NativeRenderer','disposeV2'),('dev.mixer.android.NativeRenderer','cancelInputV2'),('dev.mixer.android.NativeAppearanceViewsV2$NativeSwitch','clearTouch')}
    for number in [2]:
        for path in sorted((HERE/f'matrix-execution-{number}').glob('02-*.stdout')):
            for raw in path.read_text().splitlines():
                if not raw.startswith('{'):continue
                row=json.loads(raw)
                if 'variant' not in row:continue
                current=Counter();rejections=[];source=sites[row['id']];exact=(row['class'],row['method'],row['descriptor'],row['bci'])
                for prefix,stack in expand(row['orderedTrace']):
                    if not prefix.endswith('/entry'):continue
                    parsed=[identity(frame) for frame in stack];top=parsed[0] if parsed else None;native=prefix.removesuffix('/entry')
                    if row['variant']=='clean':category='clean control continuation'
                    elif row['variant'].startswith('dirty') and row['before']['operationPresent']:category='unchanged captured transaction after lifecycle-only dirty'
                    elif not parsed:category='reviewer external platform action; no Mixer body frame'
                    elif top==exact:category='framework continuation inside the already-entered selected call'
                    elif (top[0],top[1]) in cleanup:category='independently consumed release/hide/unregister/cancellation slot'
                    elif native=='NativeBridge.abortV2' and top[:2]==('dev.mixer.android.NativeCoordinatorV2','transact'):category='known engine token abort during failure cleanup'
                    elif native=='NativeBridge.destroy' and top[:2]==('dev.mixer.android.NativeCoordinatorV2','disposeOnce'):category='consumed known session disposal'
                    elif row['variant'].endswith('throw-after-callback') and any(frame[:2] in [('dev.mixer.android.NativeRenderer','restoreV2'),('dev.mixer.android.NativeRenderer','restoreParentV2')] for frame in parsed):category='authorized rollback through original transaction scope'
                    elif source['kind']=='constructor' and exact in parsed and top[1]=='<init>' and top[3]==2:category='opaque constructor superclass continuation before caller postcheck'
                    elif native=='Drawable.invalidateSelf' and top[:2]==('dev.mixer.android.NativeAppearanceViewsV2$ControlDrawable','onStateChange') and exact in parsed:category='mechanical drawable invalidation inside entered framework setter'
                    else:
                        category='requires source disposition';rejections.append(dict(native=native,stack=stack))
                    current[category]+=1;categories[category]+=1
                rows.append(dict(id=row['id'],variant=row['variant'],source=str(path.relative_to(HERE)),counts=dict(current),unresolved_entries=len(rejections)))
                if rejections:unknown.append(dict(id=row['id'],variant=row['variant'],source=str(path.relative_to(HERE)),entries=rejections))
    assert len(rows)==1323
    result=dict(scope='Independent source-reviewed host tail classification; private helper return timing remains explicitly nested-leaf evidence',rows=1323,categories=dict(categories),unresolved_rows=len(unknown),unresolved=unknown,row_classifications=rows)
    (HERE/'matrix-tail-classification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['unresolved','row_classifications']}))

if __name__=='__main__':main()
