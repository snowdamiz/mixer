#!/usr/bin/env python3
"""Author the bounded source146 external interface catalog, never generalize it.

Only the pinned independent typed graph supplies frontier membership. This
preparation is not called by the binder; --check is read-only. Every contract
remains a candidate for fresh independent review. No wildcard contract exists.
"""
import gzip,json,sys
from pathlib import Path
from mir_graph import parse_functions,external_identity,sha,require
D=Path(__file__).resolve().parent;R=D.parents[1];V=R/'verification'
I=V/'swift-guarded-snapshot-string-provenance-independent'
def canonical(j):return json.dumps(j,sort_keys=True,separators=(',',':')).encode()
def main(check=False):
    seal=json.loads((I/'seal.json').read_text())
    require(sha((I/'seal.json').read_bytes())=='741e104537fc3ddc57fc499a764cca9fedaa2b42d2fe109eeb590504b01241d9','independent-pin')
    for name in ('typed-graph.json','source-semantic-review.json'):
        member=next(m for m in seal['members'] if m['path']==name)
        require(sha((I/name).read_bytes())==member['sha256'],'independent-member:'+name)
    independent=json.loads((I/'typed-graph.json').read_text())
    base=V/'swift-guarded-snapshot-loader-work-source146'
    ref=json.loads((base/'source-reference-map.json').read_text())
    source={m['path']:(R/m['source']).read_text() for m in ref['members'] if m['path'].endswith('.rs')}
    functions,_,_=parse_functions(gzip.decompress((base/'whole-source146.mir.gz').read_bytes()).decode(),source)
    old=json.loads((V/'swift-guarded-snapshot-string-provenance/graph.json').read_text())
    kinds={x['target']:x['kind'] for x in old['external_frontier']}
    contracts={}
    for site in independent['external_sites']:
        target=site['target'];call=next(c for c in functions[site['caller']]['calls'] if c['line']==site['line'])
        require(call['target']==target and call['result_type']==site['result_type'],'independent-call-signature:'+str((site['caller'],site['line'],call['target'],call['result_type'],site['result_type'])))
        identity=external_identity(target)
        # No approval by startswith(std/core), reference/generic receiver, or
        # comparison basename. This finite roster is a full exact identity list.
        contract=contracts.setdefault(target,{'identity':identity,'signatures':[],
            'conservation':kinds[target],
            'review_scope':'exact source146 typed interface only; no namespace, receiver, trait or generic wildcard',
            'native_backing_separate':kinds[target].startswith(('native-','platform-'))})
        signature={'arguments':[a['type'] for a in call['arguments']],'result':call['result_type']}
        if signature not in contract['signatures']:contract['signatures'].append(signature)
    for contract in contracts.values():contract['signatures'].sort(key=lambda x:canonical(x))
    value={'schema':1,'status':'correction-producer-reviewed-exact-interface-catalog-pending-independent-review',
        'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
        'independent_frontier_file_sha256':sha((I/'typed-graph.json').read_bytes()),
        'no_general_classifier':True,'new_instantiations_refuse':True,'contracts':contracts}
    raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    if check:require((D/'external-contracts.json').read_bytes()==raw,'external-contracts-exact-rederive')
    else:
        require(not (D/'seal.json').exists(),'already-frozen')
        (D/'external-contracts.json').write_bytes(raw)
    print(json.dumps({'contracts':len(contracts),'typed_signatures':sum(len(c['signatures']) for c in contracts.values()),'read_only':check,'authority':False},sort_keys=True))
if __name__=='__main__':main('--check' in sys.argv)
