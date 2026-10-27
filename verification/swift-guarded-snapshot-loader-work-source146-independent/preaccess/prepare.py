#!/usr/bin/env python3
"""Preaccess baseline only; active loader146 candidate is never read."""
from pathlib import Path
import datetime
import hashlib
import json
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0,str(HERE.parent))
from evaluator import evaluate, Refused, type_width
V = ROOT/'verification'
checks = []
inputs = {}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read(p):
    b = p.read_bytes()
    inputs[p.relative_to(ROOT).as_posix()] = {'sha256':sha(b),'bytes':len(b)}
    return b


def check(label, value):
    if not value:
        raise AssertionError(label)
    checks.append(label)


def main():
    p = V/'swift-semantic-adapter-root-review/guarded-snapshot-loader-work-host-acceptance.json'
    check('corrected145 root acceptance',sha(read(p))=='e819f93e5219c631255c4322f291539c72b2660f8b7cb593a51cb4beb78742c7')
    ind = V/'swift-guarded-snapshot-loader-work-independent'
    packets = [(ind/'review','28d14ca65eed39ac22b01f562ccc74178f3ee361c2c0a73d16e0da9b122f4be5'),(ind/'correction-review','5b15b973477808ff0aeafb00b53006b763d71f5b30d71de5995854aa5193e876'),(ind/'source146-preaccess','96dd7fc1f0d502816847fc94d46a00917a7e954416f41334bcadc8af70187b75'),(V/'swift-guarded-snapshot-loader-work-correction','b7142125a8b00f0fbf9ade17d2c7697e42c1ef20d972a995dddfd452e92eff4e')]
    for folder,digest in packets:
        check('frozen seal '+folder.name,sha(read(folder/'seal.json'))==digest)
        seal = json.loads(read(folder/'seal.json'))
        for m in seal['members']:
            b = read(folder/m['path'])
            check('frozen member '+folder.name+'/'+m['path'],len(b)==m['bytes'] and sha(b)==m['sha256'])
    correction = V/'swift-guarded-snapshot-loader-work-correction'
    ledger = json.loads(read(correction/'mir-ledger.json'))
    geometry = json.loads(read(correction/'cap-geometry.json'))
    baseline = evaluate(geometry,ledger)
    check('independent bottom-up scalar baseline',baseline=={'wrapper':97394558768720,'coefficient':1748020339,'W_loader':895083809874789059,'visited':219,'operational_grant':False})
    grid = []
    for b in [0,1,2,31,128,4096,1000000,511999999,512000000]:
        r = evaluate(dict(geometry,credits=b),ledger)
        check('varied checked credit baseline '+str(b),r['W_loader']==97394558768720+(b+1)*1748020339)
        grid.append({'B':b,**r})
    for target,width in [('<Type as PartialEq>::ne',1),('<Option<Type> as PartialEq>::eq',1),('<&[Type] as PartialEq>::ne',128),('<&[Type] as PartialEq<[Type; 1]>>::eq',1)]:
        check('closed receiver independent '+target,type_width(target)==width)
    for target in ['<Vec<Type> as PartialEq>::eq','<Option<&Type> as PartialEq>::eq','<&[Type] as PartialEq<[Type; 2]>>::eq','<&[Type] as PartialEq<[Type; N]>>::eq','<OtherType as PartialEq>::eq']:
        try:type_width(target)
        except Refused:check('unknown receiver refusal '+target,True)
        else:raise AssertionError('unknown accepted')
    signatures = {n:{'owner':r['owner'],'mir_sha256':r['mir_sha256'],'local_actions':r['local_actions'],'row_sha256':sha(json.dumps(r,sort_keys=True,separators=(',',':')).encode())} for n,r in ledger['nodes'].items()}
    data = {'schema':1,'status':'preaccess-baseline-only-before-loader146-candidate-read','checks':len(checks),'active_loader146_candidate_read':False,'source146_accepted':False,'baseline_source145':ledger['source_tree_sha256'],'accepted_baseline':baseline,'credit_grid':grid,'nodes':signatures,'proofs_to_compose_only_after_exact146_mapping':{'MIR_definitions':219,'loop_sites':40,'dereferences':1456,'projected_stores':37,'credit_partition_cases':972,'native_controls':320,'false_generic_reference_base_claim_accepted':False},'new_compiler_or_product_or_native_execution':False}
    for name,value in [('baseline.json',data),('checks.json',{'labels':checks}),('input-custody.json',{'files':inputs})]:
        (HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'passed':True,'checks':len(checks),'candidate_read':False,'baseline':baseline}))


if __name__=='__main__':main()
