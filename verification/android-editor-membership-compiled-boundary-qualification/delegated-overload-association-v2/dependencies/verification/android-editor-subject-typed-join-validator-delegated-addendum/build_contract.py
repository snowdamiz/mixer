#!/usr/bin/env python3
"""Build the narrow data-join policy from the selected frozen source context."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SEM=ROOT/'verification/android-editor-membership-compiled-boundary-qualification/semantic-review-candidate-v1'
BASE=ROOT/'verification/android-editor-subject-typed-join-validator'
CORRECTION=ROOT/'verification/android-editor-subject-typed-join-validator-correction'
F='dev/mixer/android/NativeAppearanceViewsV2$NativeField'
E='dev/mixer/android/NativeEditorConnectionV2'
FRAME_CONTRACTS=[
    (E+'$Api33','lambda$setComposingRegion$4','(IILandroid/view/inputmethod/TextAttribute;)Ljava/lang/Boolean;',7,66),
    (F,'nativeValue','(Ldev/mixer/android/NativeAppearanceViewsV2$NativeField$Attempt;Ljava/lang/Object;Ljava/util/function/Supplier;)Ljava/lang/Object;',87,1137),
    (E+'$Base','nativeValue','(Ljava/lang/Object;Ljava/util/function/Supplier;)Ljava/lang/Object;',10,26),
    (E+'$Api33','lambda$setComposingRegion$5','(IILandroid/view/inputmethod/TextAttribute;)Ljava/lang/Boolean;',50,66),
    (F,'dispatch','(Ldev/mixer/android/NativeAppearanceViewsV2$NativeField$Attempt;Ljava/lang/String;Ljava/lang/Object;Ljava/util/function/Supplier;)Ljava/lang/Object;',108,1118),
    (E+'$Base','call','(Ljava/lang/String;Ljava/lang/Object;Ljava/util/function/Supplier;)Ljava/lang/Object;',11,25),
    (E+'$Api33','setComposingRegion','(IILandroid/view/inputmethod/TextAttribute;)Z',16,66),
]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    assert sha(BASE/'seal.json')=='fed4e7f14c82d1f17b69a4ef2a6809e34edfba0adc67b5c773944e809b839c5d'
    assert sha(BASE/'policy.json')=='ada20df1315a40d0376f04f8fbb9a5d6985e9ce7f83c456e980eb7b197c184e5'
    assert sha(SEM/'seal.json')=='361412b6ee2124ace685a2242390ece375d0327b119876b13db27dc95ea3f5e6'
    assert sha(CORRECTION/'seal.json')=='18fd1576d22572e6cb8e9a68c5d0d83a3042f4b465d2b258fb53a9c930de71c9'
    assert sha(CORRECTION/'typed_join.py')=='c3a24d05de9670b404357f509a8e1b42924a83cc0c43342a9cdc6630862722db'
    seal=json.loads((SEM/'seal.json').read_text())
    for name in ['active-semantic-obligations.json','product-context.json']:
        entry=next(m for m in seal['members'] if m['path']==name)
        assert sha(SEM/name)==entry['sha256']
    subjects={s['id']:s for s in json.loads((SEM/'active-semantic-obligations.json').read_text())['subjects']}
    base=json.loads((BASE/'policy.json').read_text())
    frames=[]
    for cls,method,descriptor,bci,line in FRAME_CONTRACTS:
        subject=subjects[cls+'#'+method+descriptor]
        call=next(i for i in subject['invocations'] if i['bci']==bci)
        assert call['line']==line
        frames.append({'class':cls,'method':method,'descriptor':descriptor,'bci':bci,'line':line,'source_sha256':subject['source_sha256'],'class_sha256':subject['class_sha256'],'opcode':call['opcode'],'callee':call['target']})
    states={}
    for name in ['current','successor','terminal','dirty','stale','fatal','changing','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback']:
        pre=name in ['terminal','dirty','stale','changing']
        exception=name in ['fatal','ordinary-throw-after-callback','fatal-throw-after-callback']
        states[name]={'phase':'public-entry' if pre else 'native-hook-entry' if name.endswith('at-entry') else 'native-hook-before-return',
            'selected_native_entries':0 if pre else 1,'normal_completion_count':0 if pre or exception else 2,
            'public_result':'original-ordinary-exception' if name=='ordinary-throw-after-callback' else 'original-first-fatal' if exception else name in ('current','successor'),
            'native_boolean_result':None if pre or exception else True,
            'native_body_result':'pending-no-normal-completion' if exception else 'observed-two-normal-returns' if not pre else 'not-entered',
            'canonical_alias':'clean' if name=='current' else name if name in base['canonical_states'] else None}
    policy={'schema':'mixer-delegated-raw-policy-v1','family':'setComposingRegionWithAttributes','method':'BaseInputConnection.setComposingRegion',
        'inner_descriptor':'(II)Z','outer_descriptor':'(IILandroid/view/inputmethod/TextAttribute;)Z',
        'product_context':base['context_id'],'source_map_sha256':base['source_map_sha256'],'class_map_sha256':base['class_map_sha256'],
        'base_packet_sha256':sha(BASE/'seal.json'),'base_policy_sha256':sha(BASE/'policy.json'),
        'mandatory_corrected_dependency':{'packet':str(CORRECTION.relative_to(ROOT)),'seal_sha256':sha(CORRECTION/'seal.json'),'module_sha256':sha(CORRECTION/'typed_join.py'),'policy_sha256':sha(CORRECTION/'policy.json')},
        'semantic_packet_sha256':sha(SEM/'seal.json'),
        'example_packet_sha256':'68916bf61a5204f022c7e0e6190dd698f621924b25389c3ffcd4989fbbed3104',
        'exact_selected_frames':frames,'states':states,'native_body_or_helper_admission':False,'execution_closure':'pending-external-trusted-source-closure','qualified':False}
    (HERE/'policy.json').write_text(json.dumps(policy,indent=2)+'\n')
    print(json.dumps({'policy_sha256':sha(HERE/'policy.json'),'states':len(states),'exact_frames':len(frames)}))
if __name__=='__main__':main()
