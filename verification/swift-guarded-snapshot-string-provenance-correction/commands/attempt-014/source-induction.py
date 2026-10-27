"""Source declarations plus typed MIR evidence for conditional str induction.

The complete typed statement inventory is retained in graph.json. The filtered
carrier index below is a conservative navigation aid, not an exclusion based on
spelling and not an OTA authorization procedure. Exact source/compiler custody,
resolved calls and explicit typed external contracts are required together.
"""
import collections,json,re
from mir_graph import code_only,literal_tokens,sha,require

def source_declarations(source):
    declarations=[]
    for path,text in sorted(source.items()):
        # Preserve offsets while removing comments, and mask cooked literals
        # before balancing declaration bodies. No impl method body is included.
        clean='\n'.join(code_only(line) for line in text.splitlines())
        for match in re.finditer(r'\b(struct|enum)\s+([A-Za-z_]\w*)',clean):
            cursor=match.end();angle=0;start=None;terminal=None
            while cursor<len(clean):
                c=clean[cursor]
                if c=='<':angle+=1
                elif c=='>':angle-=1
                elif not angle and c in '{(;':start=cursor;terminal=c;break
                cursor+=1
            require(start is not None,'source-declaration-terminator')
            if terminal==';':end=start+1
            else:
                opening=terminal;closing='}' if opening=='{' else ')';depth=1;cursor=start+1;quoted=False;escape=False
                while cursor<len(clean) and depth:
                    c=clean[cursor]
                    if quoted:
                        if escape:escape=False
                        elif c=='\\':escape=True
                        elif c=='"':quoted=False
                    elif c=='"':quoted=True
                    elif c==opening:depth+=1
                    elif c==closing:depth-=1
                    cursor+=1
                require(depth==0,'source-declaration-balanced')
                end=cursor
            declaration=clean[match.start():end]
            declarations.append({'path':path,'kind':match[1],'name':match[2],
                'declaration':declaration,'declaration_sha256':sha(declaration.encode()),
                'tokens':sorted(set(re.findall(r'\b[A-Za-z_]\w*\b',declaration)))})
    return declarations

def derive(graph,source,review,original,independent,mir):
    # Rebind every semantic excerpt to its exact frozen source bytes. These
    # receipts cover the loader, fresh control, failure latch, policy exclusion,
    # Reader/Meter/Fault forwards, return/error retention and named additions.
    excerpts=[]
    for excerpt in review['excerpts']:
        text=source[excerpt['source146_path']]
        require(sha(text.encode())==excerpt['source_sha256'],'source-semantic-sha')
        actual='\n'.join(text.splitlines()[excerpt['start']-1:excerpt['end']])
        # A retained review excerpt may intentionally end inside its last line.
        require(actual.startswith(excerpt['text']),'source-semantic-excerpt')
        excerpts.append(excerpt)
    declarations=source_declarations(source)
    # Policy is a control dependency of policy_identity, not a direct str field
    # in source146. Retain it and containers of it in the conservative trace.
    control_dependencies={'Policy'}
    names={d['name'] for d in declarations if 'str' in d['tokens']}|control_dependencies
    while True:
        expanded=names|{d['name'] for d in declarations if set(d['tokens'])&names}
        if expanded==names:break
        names=expanded
    # Associated/generic return carriers are part of the exact selected
    # specialization obligation; they are never accepted as arbitrary inputs.
    def carrier(typ):return bool(re.search(r'\bstr\b',typ) or set(re.findall(r'\b[A-Za-z_]\w*\b',typ))&names or '::Failure' in typ)
    inbound=collections.defaultdict(list)
    for edge in graph['edges']:inbound[edge['callee']].append(edge)
    ports=[];bodies={};calls=[]
    frontier={f['target']:f for f in graph['external_frontier']}
    for key,row in graph['nodes'].items():
        locals_={name:typ for name,typ in row['local_types'].items() if carrier(typ)}
        for parameter,typ in row['params'].items():
            if carrier(typ):ports.append({'function':key,'parameter':parameter,'type':typ,'incoming':inbound[key],
                'alternate_caller_status':'open unless the exact unmodified-loader/fresh-control contract is proved; length/lifetime/pointer width is insufficient'})
        operations=[]
        for statement in row['typed_statements']:
            refs=set(re.findall(r'\b_\d+\b',statement['statement']))
            referenced={p:locals_[p] for p in sorted(refs&locals_.keys())}
            if referenced or any(n in statement['statement'] for n in names):
                operations.append(dict(statement,referenced_carrier_local_types=referenced))
        bodycalls=[]
        for call in row['calls']:
            if carrier(call['result_type']) or any(carrier(a['type']) for a in call['arguments']):
                edges=[e for e in graph['edges'] if e['caller']==key and e['line']==call['line']]
                authored=[e for e in edges if e['kind']=='authored']
                if not authored:require(call['target'] in frontier,'carrier-call-unresolved')
                evidence={'function':key,'line':call['line'],'target':call['target'],'result_type':call['result_type'],
                    'arguments':call['arguments'],'expanded_edges':edges,
                    'rule':'expanded exact authored body' if authored else frontier[call['target']]['kind']}
                calls.append(evidence);bodycalls.append(evidence)
        if locals_ or carrier(row['return_type']) or operations:
            bodies[key]={'name':row['name'],'MIR_sha256':row['MIR_sha256'],'carrier_local_types':locals_,
                'return_type':row['return_type'],'return_carries_str':carrier(row['return_type']),
                'operations':operations,'carrier_calls':bodycalls,
                'complete_statement_inventory':'graph.json nodes.'+key+'.typed_statements'}
    edgekey=lambda e:(e['caller'],e['callee'],e['line'],e['kind'],e['target'])
    oldedges={edgekey(e) for e in original['edges']};newedges={edgekey(e) for e in graph['edges']}
    independentedges={edgekey(e) for e in independent['edges']}
    require(oldedges<=newedges,'original-authored-edges-omitted')
    require(newedges==independentedges,'independently-reconstructed-typed-edges')
    require(set(original['nodes'])<=set(graph['nodes']),'original-bodies-omitted')
    for key,row in independent['nodes'].items():
        require(graph['nodes'][key]['MIR_sha256']==row['MIR_sha256'] and graph['nodes'][key]['MIR_bytes']==row['MIR_bytes'],'independent-body:'+key)
    require(len(graph['nodes'])==525 and len(graph['edges'])==1908,'corrected-fixed-point-counts')
    require(len(graph['source_str_assignments'])==80,'all-scoped-str-assignments')
    named=[e for e in graph['edges'] if e['kind']=='named-authored-callback']
    require(len(named)==28 and len({(e['caller'],e['line']) for e in named})==22,'all-named-callbacks')
    oldassign={(a['function'],a['line'],a['local']) for a in original['source_str_assignments']}
    added=[a for a in graph['source_str_assignments'] if (a['function'],a['line'],a['local']) not in oldassign]
    require({(a['function'],a['local'],a['line']) for a in added}=={('f0279','_35',256),('f1035','_29',203)},'two-missing-nested-transfers')
    require(all(a['kind']=='reference-or-field-transfer' for a in added),'new-transfer-conservation')
    origins=literal_tokens(mir)
    require(len(origins)==3189 and len({o['value'] for o in origins})==1397,'complete-compiler-literal-origin-pool')
    return {'schema':1,'status':'conditional-source146-induction-candidate-pending-independent-review',
        'rule':'Primitive str origins are pinned compiler literals/constant allocations. All selected calls resolve to exact authored bodies, expanded closure/named bodies or explicit typed external contracts. All typed statements are retained for aggregate/enum/field/reference conservation review. Arbitrary caller carriers remain open.',
        'source_semantic_excerpts':excerpts,'carrier_declarations':[d for d in declarations if d['name'] in names],
        'carrier_names_conservative':sorted(names),'additional_control_dependencies':sorted(control_dependencies),
        'policy_frozen_source146':'Frozen(&Limits) stores scalar/profile limits, not an arbitrary str field; its alternative policy_identity branch is excluded by exact Policy::swift construction. Policy substitution never qualifies through lifetime or length.',
        'nested_and_direct_ports':ports,'body_induction':bodies,
        'original_graph_preserved':True,'independent_graph_reproduced':True,'added_edges':[dict(zip(('caller','callee','line','kind','target'),e)) for e in sorted(newedges-oldedges)],
        'added_bodies':sorted(set(graph['nodes'])-set(original['nodes'])),'added_direct_str_assignments':added,
        'named_authored_sites':22,'named_authored_edges':28,'standard_named_callbacks':graph['standard_named_callbacks'],
        'origin_pool':{'compiled_bodies':graph['compiled_function_bodies'],'literal_occurrences':origins,
            'allocations':graph['constant_allocations'],'max_literal_UTF8_bytes':92,'max_allocation_bytes':5080},
        'opaque_native_backing':['Path/OsStr','io::Error private/native backing'],
        'necessary_conditions':['exact unmodified loader-produced selected proof','fresh control: first_failure=None and cleanup_invariant=None','no incoming failure/Fault/custom Reader/Meter strings','no Policy::Frozen substitution','no intervening mutation','exact selected callbacks and specializations'],
        'scope':'source146 only; outer candidate 27deef is separate future rebind; no automatic coverage',
        'L_str_selected':False,'root_selected':False,'whole_budget_selected':False,'OTA_or_GA':False}
