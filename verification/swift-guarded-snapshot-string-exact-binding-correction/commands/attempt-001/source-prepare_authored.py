"""Review and reproduce exact authored identities and typed instantiations.

The old independent edge roster is membership evidence only. It does not grant
type compatibility or identity by basename. Every retained alias is an exact
target-to-source-declaration relation and every positional type equation must
unify with that declaration under the explicit source146 substitutions.
"""
import collections,gzip,json,re,sys
from pathlib import Path
from mir_graph import parse_functions,sha,require,external_identity
D=Path(__file__).resolve().parent;R=D.parents[1];V=R/'verification'

def inputs():
    base=V/'swift-guarded-snapshot-loader-work-source146'
    ref=json.loads((base/'source-reference-map.json').read_text())
    source={m['path']:(R/m['source']).read_text() for m in ref['members'] if m['path'].endswith('.rs')}
    mir=gzip.decompress((base/'whole-source146.mir.gz').read_bytes()).decode()
    functions,byname,bybase=parse_functions(mir,source)
    old=json.loads((V/'swift-guarded-snapshot-string-provenance-independent/typed-graph.json').read_text())
    return mir,source,functions,old

def main(check=False):
    mir,source,functions,old=inputs()
    pairs=collections.Counter();identities={}
    for edge in old['edges']:
        if edge['kind']!='authored':continue
        row=functions[edge['callee']];call=next(c for c in functions[edge['caller']]['calls'] if c['line']==edge['line'])
        require(call['target']==edge['target'],'authored-roster-target')
        require(len(call['arguments'])==len(row['params']),'authored-arity')
        for template,actual in zip(list(row['params'].values())+[row['return_type']],[a['type'] for a in call['arguments']]+[call['result_type']]):
            if template!=actual:pairs[(template,actual)]+=1
    value=[{'template':a,'actual':b,'count':n} for (a,b),n in sorted(pairs.items())]
    raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    if check:require((D/'type-pair-preparation.json').read_bytes()==raw,'type-pair-preparation')
    else:(D/'type-pair-preparation.json').write_bytes(raw)
    print(json.dumps({'nonidentical_positional_type_pairs':len(value),'compiled_headers':len(functions)}))
if __name__=='__main__':main('--check' in sys.argv)
