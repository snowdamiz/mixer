"""Review and reproduce exact authored identities and typed instantiations.

The old independent edge roster is membership evidence only. It does not grant
type compatibility or identity by basename. Every retained alias is an exact
target-to-source-declaration relation and every positional type equation must
unify with that declaration under the explicit source146 substitutions.
"""
import collections,gzip,json,re,sys
from pathlib import Path
from mir_graph import parse_functions,sha,require,external_identity
from type_contracts import unify,unify_closure,canonical,ALIASES,SPECIALIZATIONS,CONSTANT_TYPES,callable_parts
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
    pairs=collections.Counter();identities={};mismatches=[]
    for edge in old['edges']:
        if edge['kind']!='authored':continue
        row=functions[edge['callee']];call=next(c for c in functions[edge['caller']]['calls'] if c['line']==edge['line'])
        require(call['target']==edge['target'],'authored-roster-target')
        require(len(call['arguments'])==len(row['params']),'authored-arity')
        bindings={};equations=[];closures=[]
        for template,actual in zip(list(row['params'].values())+[row['return_type']],[a['type'] for a in call['arguments']]+[call['result_type']]):
            if template!=actual:pairs[(template,actual)]+=1
            try:
                if template.startswith('impl Fn'):closures.extend(unify_closure(template,actual,bindings,functions))
                else:unify(template,actual,bindings)
            except ValueError as error:mismatches.append({'target':call['target'],'callee':edge['callee'],'template':template,'actual':actual,'reason':str(error)})
            equations.append({'declaration':template,'call':actual})
        contract=identities.setdefault(edge['target'],{'identity':external_identity(edge['target']),'definitions':{},'signatures':[],'named_callback_signatures':[]})
        contract['definitions'][row['name']]={'params':row['params'],'return_type':row['return_type'],'owner_source_line':row['owner_source_line']}
        sig={'arguments':[a['type'] for a in call['arguments']],'result':call['result_type'],'type_equations':equations,'generic_substitutions':bindings,'closure_contracts':closures}
        if sig not in contract['signatures']:contract['signatures'].append(sig)
    # A named function item must agree with the complete fn item signature.
    # Higher-ranked reference lifetimes are alpha-renamed only here; no type
    # token, reference mutability, carrier, argument or result is discarded.
    for edge in old['edges']:
        if edge['kind']!='named-authored-callback':continue
        row=functions[edge['callee']];outer=next(c for c in functions[edge['caller']]['calls'] if c['line']==edge['line'])
        marker='{'+edge['target']+'}';end=outer['target'].index(marker)
        start=outer['target'].rfind('fn(',0,end);require(start>=0,'typed-named-callback')
        fntext=outer['target'][start:end].rstrip();_,args,result=callable_parts(fntext)
        require(len(args)==len(row['params']),'named-callback-arity')
        bindings={};equations=[]
        for template,actual in zip(list(row['params'].values())+[row['return_type']],args+[result]):
            actual=re.sub(r"&'\w+\s+",'&',actual)
            unify(template,actual,bindings);equations.append({'declaration':template,'function_item':actual})
        contract=identities.setdefault(edge['target'],{'identity':external_identity(edge['target']),'definitions':{},'signatures':[],'named_callback_signatures':[]})
        contract['definitions'][row['name']]={'params':row['params'],'return_type':row['return_type'],'owner_source_line':row['owner_source_line']}
        sig={'function_item_type':fntext,'outer_target':outer['target'],'type_equations':equations,'generic_substitutions':bindings}
        if sig not in contract['named_callback_signatures']:contract['named_callback_signatures'].append(sig)
    for contract in identities.values():
        for key in ('signatures','named_callback_signatures'):contract[key].sort(key=lambda x:json.dumps(x,sort_keys=True))
    value=[{'template':a,'actual':b,'count':n} for (a,b),n in sorted(pairs.items())]
    raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    if check:require((D/'type-pair-preparation.json').read_bytes()==raw,'type-pair-preparation')
    else:(D/'type-pair-preparation.json').write_bytes(raw)
    if not check:(D/'type-unification-preparation.json').write_text(json.dumps(mismatches,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'nonidentical_positional_type_pairs':len(value),'compiled_headers':len(functions),'unresolved_type_equations':len(mismatches),'first':mismatches[:4]}))
    require(not mismatches,'all-authored-positional-equations-must-unify')
    closure_contracts={}
    for edge in old['edges']:
        if edge['kind']!='authored-callback':continue
        row=functions[edge['callee']];outer=next(c for c in functions[edge['caller']]['calls'] if c['line']==edge['line'])
        key=outer['target']+' | '+edge['target']
        relation={'outer_identity':external_identity(outer['target']),'outer_arguments':[a['type'] for a in outer['arguments']],
            'outer_result':outer['result_type'],'closure_site':edge['target'],'definitions':{}}
        contract=closure_contracts.setdefault(key,relation)
        require(all(contract[k]==relation[k] for k in relation if k!='definitions'),'closure-adapter-types-must-agree')
        contract['definitions'][row['name']]={'params':row['params'],'return_type':row['return_type'],'owner_source_line':row['owner_source_line']}
    value={'schema':1,'status':'exact-source146-authored-interface-candidate-pending-independent-review',
        'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
        'scope':'finite full target identities, exact source owner declarations, structural positional type equations and reviewed source146 specializations; no basename or generic namespace waiver',
        'type_path_aliases':ALIASES,'selected_specializations':SPECIALIZATIONS,'constant_types':CONSTANT_TYPES,
        'no_shortname_fallback':True,'new_target_or_signature_refuses':True,'contracts':identities,'closure_contracts':closure_contracts}
    raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    if check:require((D/'authored-contracts.json').read_bytes()==raw,'exact-authored-contract-rederive')
    else:(D/'authored-contracts.json').write_bytes(raw)
    print(json.dumps({'exact_authored_targets':len(identities),'typed_signatures':sum(len(c['signatures']) for c in identities.values()),'named_callback_signatures':sum(len(c['named_callback_signatures']) for c in identities.values()),'read_only':check,'authority':False}))
if __name__=='__main__':main('--check' in sys.argv)
