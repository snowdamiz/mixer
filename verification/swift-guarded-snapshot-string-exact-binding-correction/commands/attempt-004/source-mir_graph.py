"""Offline source146 typed-MIR reference conservation. Never loads executable code."""
from __future__ import annotations
import collections, functools, hashlib, json, re
from pathlib import Path

class Refused(ValueError): pass

def sha(raw): return hashlib.sha256(raw).hexdigest()
def require(condition, reason):
    if not condition: raise Refused(reason)

def char_end(line,i):
    if line[i]!="'":return None
    match=re.match(r"'(?:[^'\\]|\\(?:u\{[0-9a-fA-F_]+\}|x[0-9a-fA-F]{2}|.))'",line[i:])
    return i+len(match[0]) if match else None

def code_only(line):
    quoted=False;escaped=False;i=0
    while i<len(line):
        c=line[i]
        if quoted:
            if escaped:escaped=False
            elif c=='\\':escaped=True
            elif c=='"':quoted=False
        elif c=='"':quoted=True
        elif c=="'":
            end=char_end(line,i)
            if end is not None:i=end;continue
        elif line[i:i+2]=='//':return line[:i]
        i+=1
    return line

def literal_tokens(text):
    """Decode every compiler cooked string; unsupported escape is a refusal.

    Bytestrings are not str origins. Comments are removed lexically, respecting
    embedded // and quotes. This is a compiler-MIR lexer, not a Rust source scan.
    """
    out=[];in_allocation=False
    for line_no,line in enumerate(text.splitlines(),1):
        if re.match(r'^alloc\w+ .*\{',line):in_allocation=True;continue
        if in_allocation:
            if line=='}':in_allocation=False
            continue
        line=code_only(line);i=0
        while i<len(line):
            if line[i]=="'":
                end=char_end(line,i)
                if end is not None:i=end;continue
            if line[i]!='"':i+=1;continue
            start=i;binary=i>0 and line[i-1]=='b';i+=1;value=[]
            while i<len(line):
                c=line[i];i+=1
                if c=='"':break
                if c!='\\':value.append(c);continue
                require(i<len(line),'truncated-escape');e=line[i];i+=1
                simple={'n':'\n','r':'\r','t':'\t','0':'\0','\\':'\\','"':'"',"'":"'"}
                if e in simple:value.append(simple[e])
                elif e=='x':
                    raw=line[i:i+2];require(len(raw)==2 and all(c in '0123456789abcdefABCDEF' for c in raw),'hex-escape');i+=2;value.append(chr(int(raw,16)))
                elif e=='u':
                    require(i<len(line) and line[i]=='{','unicode-open');end=line.find('}',i+1);require(end>=0,'unicode-close')
                    raw=line[i+1:end].replace('_','');require(raw and all(c in '0123456789abcdefABCDEF' for c in raw),'unicode-escape')
                    value.append(chr(int(raw,16)));i=end+1
                else:raise Refused('unsupported-escape:'+e)
            else:raise Refused('unclosed-compiler-literal:'+line)
            if not binary:
                decoded=''.join(value);decoded.encode('utf-8',errors='strict')
                out.append({'value':decoded,'line':line_no,'column':start+1,'utf8_bytes':len(decoded.encode('utf-8')),'scalar_leaves':len(decoded)})
    return out

def erase_generics(value):
    out=[];level=0
    for i,c in enumerate(value):
        if c=='<':level+=1
        elif c=='>' and (i==0 or value[i-1]!='-'):level-=1
        elif level==0:out.append(c)
    require(level==0,'unbalanced-generic-target')
    return ''.join(out).replace('::::','::').strip(':')

def call_target(rhs):
    # Parentheses inside a type such as Result<(),E> are not call arguments.
    level=0;quoted=False;escaped=False
    for i,c in enumerate(rhs):
        if quoted:
            if escaped:escaped=False
            elif c=='\\':escaped=True
            elif c=='"':quoted=False
        elif c=='"':quoted=True
        elif c=='<':level+=1
        elif c=='>' and (i==0 or rhs[i-1]!='-'):level-=1
        elif c=='(' and level==0:return rhs[:i]
    raise Refused('call-without-argument-list:'+rhs)

def signature_params(params):
    result={}
    for text in split_operands(params):
        match=re.fullmatch(r'(_\d+): (.+)',text)
        require(match is not None,'complete-typed-header-parameter:'+text)
        require(match[1] not in result,'duplicate-header-parameter')
        result[match[1]]=match[2]
    return result

def parse_header(header):
    """Locate the OUTER argument list, then balance its complete type syntax.

    A function arrow is a token, never a generic close. Fn/FnMut/FnOnce return
    arrows therefore cannot terminate the enclosing parameter list. The same
    delimiter lexer verifies every parameter and the complete returned type.
    """
    require(header.startswith('fn ') and header.endswith(' {'),'function-header-shape')
    start=len(call_target(header[3:]))+3
    require(header[start]=='(','function-header-arguments')
    depth=1;cursor=start+1;quoted=False;escaped=False
    while cursor<len(header) and depth:
        c=header[cursor]
        if quoted:
            if escaped:escaped=False
            elif c=='\\':escaped=True
            elif c=='"':quoted=False
        elif c=='"':quoted=True
        elif c=="'":
            end=char_end(header,cursor)
            if end is not None:cursor=end;continue
        elif c=='(':depth+=1
        elif c==')':depth-=1
        cursor+=1
    require(depth==0 and header[cursor:cursor+4]==' -> ','complete-outer-header-arguments')
    name=header[3:start];params=header[start+1:cursor-1];returned=header[cursor+4:-2]
    require(name and returned,'complete-header-name-return')
    signature_params(params);require(len(split_operands(returned))==1,'complete-header-return-type')
    return name,params,returned

def split_operands(value):
    """Split typed MIR operands without truncating arrays, tuples or fn types."""
    parts=[];start=0;stack=[];quoted=False;escaped=False
    masked=list(value);cursor=0;in_string=False;escape=False
    while cursor<len(value):
        c=value[cursor]
        if in_string:
            if escape:escape=False
            elif c=='\\':escape=True
            elif c=='"':in_string=False
        elif c=='"':in_string=True
        elif c=="'":
            end=char_end(value,cursor)
            if end is not None:masked[cursor:end]=' '*(end-cursor);cursor=end;continue
        cursor+=1
    for i,c in enumerate(masked):
        if quoted:
            if escaped:escaped=False
            elif c=='\\':escaped=True
            elif c=='"':quoted=False
            continue
        if c=='"':quoted=True;continue
        if c in '(<[{':stack.append(c)
        elif c in ')>]}':
            if c=='>' and i and value[i-1]=='-':continue
            require(stack and stack[-1]=={')':'(',']':'[','}':'{','>':'<'}[c],'operand-delimiters:'+value)
            stack.pop()
        elif c==',' and not stack:parts.append(value[start:i].strip());start=i+1
    require(not stack and not quoted,'operand-balance:'+value)
    if value[start:].strip():parts.append(value[start:].strip())
    return parts

def operand_type(operand,locals_):
    value=re.sub(r'^(?:no_retag )?(?:copy |move )','',operand)
    if value in locals_:return locals_[value]
    if value.startswith('"'):return '&str'
    assembly=re.fullmatch(r'(in|out|inout|lateout)\([^)]*\) (_\d+)',value)
    if assembly and assembly[2] in locals_:return 'inline-asm-'+assembly[1]+':'+locals_[assembly[2]]
    if re.fullmatch(r'options\([A-Z_ |]*\)',value):return 'inline-asm-'+value
    # MIR annotates projected fields with their full compiler type. Greedy
    # suffix capture preserves internal semicolons in arrays.
    field=re.search(r': ([^\n]+)\)$',value)
    if field:return field[1]
    if value.startswith('const '):
        atom=value[6:]
        if atom.startswith('"'):return '&str'
        if atom.startswith('b"'):return 'byte-literal:'+atom
        if atom in ('true','false'):return 'bool'
        if atom.startswith("'") and char_end(atom,0)==len(atom):return 'char'
        number=re.fullmatch(r'-?(?:\d[\d_]*|0x[\da-fA-F_]+)_(\w+)',atom)
        if number:return number[1]
        if atom=='()':return '()'
        return 'exact-compiler-constant:'+atom
    # Zero-sized named function items occur as unprefixed operands. Their
    # identity is checked against the typed fn item and resolved separately.
    if re.fullmatch(r'[A-Za-z_][\w:]*',erase_generics(value)) or (value.startswith('<') and '>::' in value):return 'function-item:'+value
    raise Refused('unresolved-typed-operand:'+operand)

def call_operands(rhs,target,locals_):
    tail=rhs[len(target):];require(tail.startswith('('),'call-operands-open')
    # The final MIR terminator begins after the operand list, not after a fn
    # type's return arrow inside a generic argument.
    marker=tail.rfind(') -> ');require(marker>=0,'call-operands-close')
    operands=split_operands(tail[1:marker])
    return [{'operand':v,'type':operand_type(v,locals_)} for v in operands]

def parse_functions(mir,source):
    functions={};byname=collections.defaultdict(list);bybase=collections.defaultdict(list)
    matches=list(re.finditer(r'^fn [^\n]+\n',mir,re.M))
    require(len(matches)==sum(line.startswith('fn ') for line in mir.splitlines()),'complete-function-header-parse')
    for ordinal,m in enumerate(matches):
        end=mir.index('\n}\n',m.end())+3;body=mir[m.start():end]
        name,paramtext,returned=parse_header(body.splitlines()[0])
        key=f'f{ordinal:04d}';location=re.search(r'owned-work/vm/(.+?):(\d+):\d+:',name)
        owner=source[location[1]].splitlines()[int(location[2])-1] if location else ''
        locals_={}
        for line in body.splitlines():
            local=re.fullmatch(r'\s*let (?:mut )?(_\d+): (.*);\s*',code_only(line))
            if local:locals_[local[1]]=local[2]
        locals_.update(signature_params(paramtext));locals_.setdefault('_0',returned)
        row={'name':name,'header':body.splitlines()[0],'params':signature_params(paramtext),'return_type':returned,
             'MIR_sha256':sha(body.encode()),'MIR_bytes':len(body.encode()),'base':name.rsplit('::',1)[-1],
             'owner_source_line':owner,'local_types':locals_,'calls':[],'str_assignments':[],'carrier_operations':[],'manufacture_review':[],'literal_occurrences':literal_tokens(body),'typed_statements':[]}
        cl=re.search(r'\{closure@([^}]+)\}',paramtext);row['closure_site']=cl[1] if cl else None
        for ln,line in enumerate(body.splitlines(),1):
            if not line.startswith('        '):continue
            statement=code_only(line).strip()
            if not statement:continue
            row['typed_statements'].append({'line':ln,'statement':statement})
            if any(token in statement for token in ('SwiftRunFailure','SwiftValidationFailure','experimental::Failure','control::Fault','first_failure:','Policy::')):
                row['carrier_operations'].append({'line':ln,'statement':statement})
            iscall=(' -> [' in statement or ' -> unwind ' in statement or ' -> !' in statement)
            if iscall:
                rhs=statement.split(' = ',1)[-1];target=call_target(rhs)
                if target not in ('switchInt','assert','drop'):
                    dest=re.match(r'(_\d+) = ',statement)
                    closures=sorted(set(re.findall(r'\{closure@([^}]+)\}',target)))
                    named=sorted(set(x for x in re.findall(r'\{([^{}]+)\}',target) if not x.startswith('closure@')))
                    row['calls'].append({'target':target,'statement':statement,'line':ln,
                        'result_type':locals_.get(dest[1],returned if dest and dest[1]=='_0' else '') if dest else '!',
                        'arguments':call_operands(rhs,target,locals_),
                        'callbacks':closures+named,'closures':closures,'named_callbacks':named})
            assignment=re.match(r'(_\d+) = (.*);$',statement)
            if assignment and locals_.get(assignment[1]) in ('&str',"&'static str",'&mut str'):
                rhs=assignment[2]
                if rhs.startswith('const "'):kind='compiled-literal'
                elif rhs.startswith(('copy ','move ','no_retag copy ','no_retag move ','&')):kind='reference-or-field-transfer'
                elif iscall:kind='callee-return'
                else:kind='unreviewed-producer'
                row['str_assignments'].append({'local':assignment[1],'line':ln,'statement':statement,'kind':kind})
            if any(token in statement for token in ('from_utf8','*const str','*mut str','String','(Transmute)','BoxDerefTransmute')):
                row['manufacture_review'].append(statement)
        functions[key]=row;byname[name].append(key);bybase[row['base']].append(key)
    return functions,byname,bybase

@functools.lru_cache(maxsize=1)
def authored_catalog():
    raw=(Path(__file__).resolve().parent/'authored-contracts.json').read_bytes()
    require(sha(raw)==AUTHORED_CATALOG_SHA256,'exact-authored-catalog-custody')
    return json.loads(raw)['contracts']

@functools.lru_cache(maxsize=1)
def callback_catalog():
    raw=(Path(__file__).resolve().parent/'authored-contracts.json').read_bytes()
    require(sha(raw)==AUTHORED_CATALOG_SHA256,'exact-callback-catalog-custody')
    return json.loads(raw)['closure_contracts']

AUTHORED_CATALOG_SHA256='PREPARE'

def resolve(target,functions,byname,bybase):
    """Exact definitions precede a finite reviewed compiler-alias contract.

    No generic erasure, owner basename, module suffix or trait substring is a
    resolution rule. The full receiver, trait, member and type arguments form
    the catalog key. In particular an exact module miss has no fallback.
    """
    if target in byname:return byname[target]
    contract=authored_catalog().get(target)
    if contract is None:return []
    require(contract['identity']==external_identity(target),'authored-exact-identity')
    destinations=[]
    for name,definition in contract['definitions'].items():
        for key in byname.get(name,[]):
            row=functions[key]
            require(all(row[field]==definition[field] for field in ('params','return_type','owner_source_line')),'authored-definition-contract:'+target)
            destinations.append(key)
    return destinations

def validate_authored_call(target,call,destinations,functions):
    from type_contracts import unify,unify_closure
    contract=authored_catalog().get(target)
    actual={'arguments':[a['type'] for a in call['arguments']],'result':call['result_type']}
    if contract is not None:
        require(any(all(sig[k]==actual[k] for k in actual) for sig in contract['signatures']),'unreviewed-authored-typed-signature:'+target)
    for key in destinations:
        row=functions[key];require(len(row['params'])==len(call['arguments']),'authored-call-arity:'+target)
        bindings={}
        for template,value in zip(list(row['params'].values())+[row['return_type']],actual['arguments']+[actual['result']]):
            if template.startswith('impl Fn'):unify_closure(template,value,bindings,functions)
            else:unify(template,value,bindings)
        if contract is None:require(not bindings,'unreviewed-direct-authored-substitution:'+target)
    return actual

def validate_named_callback(callback,outer_target,destinations,functions):
    from type_contracts import unify,callable_parts
    contract=authored_catalog().get(callback)
    require(contract is not None,'unreviewed-authored-function-item:'+callback)
    sigs=[s for s in contract['named_callback_signatures'] if s['outer_target']==outer_target]
    require(len(sigs)==1,'unreviewed-authored-function-item-type:'+callback)
    sig=sigs[0];_,args,result=callable_parts(sig['function_item_type'])
    for key in destinations:
        row=functions[key];require(len(row['params'])==len(args),'named-authored-arity')
        bindings={}
        for template,actual in zip(list(row['params'].values())+[row['return_type']],args+[result]):
            unify(template,re.sub(r"&'\w+\s+",'&',actual),bindings)
    return sig

def validate_closure_callback(closure,call,destinations,functions):
    key=call['target']+' | '+closure
    contract=callback_catalog().get(key)
    require(contract is not None,'unreviewed-exact-closure-adapter:'+key)
    require(contract['outer_identity']==external_identity(call['target']),'closure-adapter-identity')
    require(contract['outer_arguments']==[a['type'] for a in call['arguments']] and contract['outer_result']==call['result_type'],'closure-adapter-typed-signature')
    actual={functions[k]['name']:{f:functions[k][f] for f in ('params','return_type','owner_source_line')} for k in destinations}
    require(actual==contract['definitions'],'closure-definition-typed-signature:'+closure)
    return contract

ROOTS=('run_one_fixture_v1','run_prepaid_fixture_v1','run_one_loaded_fixture_v1',
       'destroy_returned_fixture_v1','release_after_retirement_v1')

def external_identity(target):
    """Retain complete qualified identities, never a method basename waiver."""
    if target.startswith('<') and ' as ' in target:
        depth=0
        for i,c in enumerate(target):
            if c=='<':depth+=1
            elif c=='>' and (i==0 or target[i-1]!='-'):
                depth-=1
                if depth==0:break
        inner=target[1:i];receiver,trait=inner.split(' as ',1)
        return {'receiver':receiver,'trait':trait,'member':target[i+3:],'namespace':'qualified-exact-trait'}
    plain=erase_generics(target)
    return {'receiver':target.rsplit('::',1)[0] if '::' in target else '',
            'trait':None,'member':plain.rsplit('::',1)[-1],
            'namespace':plain.rsplit('::',1)[0] if '::' in plain else plain}

@functools.lru_cache(maxsize=1)
def external_catalog():
    raw=(Path(__file__).resolve().parent/'external-contracts.json').read_bytes()
    require(sha(raw)=='8eabc3d20b792685daa160c77e4e210c7098738b113b3242cafc5fa3ac54f8c7','typed-interface-catalog-custody')
    return json.loads(raw)['contracts']

def classify_external(target,result_types,argument_types=None):
    """Closed, source146-specific typed interface catalog.

    This intentionally does not claim a general standard library classifier.
    A new instantiation, namespace, receiver, trait or argument/result shape is
    refused, even if its member has a familiar name. Catalog admission requires
    source/interface review and a new independent review, not a graph hash.
    """
    catalog=external_catalog()
    require(target in catalog,'unreviewed-exact-external-contract:'+target)
    contract=catalog[target]
    require(contract['identity']==external_identity(target),'external-identity-mismatch:'+target)
    require(argument_types is not None,'typed-external-arguments-required:'+target)
    require(len(result_types)==len(argument_types),'typed-external-signature-arity:'+target)
    for result,args in zip(result_types,argument_types):
        require({'result':result,'arguments':args} in contract['signatures'],'unreviewed-external-typed-signature:'+target)
    return contract['conservation']

NAMED_STANDARD_PREDICATES={
    'Option::<experimental_swift_reactor::cache::ScanPlan>::is_some':
        "for<'a> fn(&'a Option<experimental_swift_reactor::cache::ScanPlan>) -> bool {Option::<experimental_swift_reactor::cache::ScanPlan>::is_some}",
    'Option::<[u8; 32]>::is_none':
        "for<'a> fn(&'a Option<[u8; 32]>) -> bool {Option::<[u8; 32]>::is_none}",
}

def standard_named_callback(callback,outer_target):
    require(callback in NAMED_STANDARD_PREDICATES,'unclosed-named-function-item:'+callback)
    require(NAMED_STANDARD_PREDICATES[callback] in outer_target,'named-predicate-typed-signature:'+callback)
    require(outer_target.startswith('<std::slice::Iter<') and ' as Iterator>::any::<' in outer_target,'named-predicate-standard-adapter')
    return {'target':callback,'typed_function_item':NAMED_STANDARD_PREDICATES[callback],
            'contract':'exact standard Option discriminant predicate; bool return; no manufactured or modified str'}

def analyze(mir,source):
    functions,byname,bybase=parse_functions(mir,source)
    rootkeys=[key for root in ROOTS for key in byname[root]]
    require(all(byname[root] for root in ROOTS),'all-selected-roots')
    # Compiler-generated drop glue is private; the only relevant authored Drop
    # hook is the actual PrepaidOwned leak-on-unwind accounting hook.
    rootkeys.extend(k for k in bybase['drop'] if 'PrepaidOwnedV1' in functions[k]['owner_source_line'])
    todo=list(rootkeys);seen=set();edges=[];external=collections.defaultdict(list);standard_callbacks=[]
    while todo:
        key=todo.pop()
        if key in seen:continue
        seen.add(key);row=functions[key]
        for assignment in row['str_assignments']:require(assignment['kind']!='unreviewed-producer','unknown-str-producer:'+assignment['statement'])
        for statement in row['manufacture_review']:
            require(not any(token in statement for token in ('from_utf8','*const str','*mut str','String')),'new-unreviewed-string-manufacturer:'+statement)
            if '(Transmute)' in statement:require(' as usize (Transmute)' in statement,'unreviewed-transmute')
            if 'BoxDerefTransmute' in statement:require(' as *const [u8] ' in statement,'unreviewed-box-transmute')
        for call in row['calls']:
            require(not re.fullmatch(r'(?:copy |move )?_\d+',call['target']),'unresolved-indirect-callee:'+call['target'])
            require(not any(a['type'].startswith('inline-asm-') for a in call['arguments']),'selected-inline-asm-not-authorized')
            destinations=resolve(call['target'],functions,byname,bybase)
            if destinations:
                validate_authored_call(call['target'],call,destinations,functions)
                # Multiple compiler bodies for one declaration include CTFE and
                # identical macro occurrences. Include every matching body.
                for dest in destinations:edges.append({'caller':key,'callee':dest,'kind':'authored','line':call['line'],'target':call['target']});todo.append(dest)
            else:external[call['target']].append({'caller':key,'line':call['line'],'result_type':call['result_type'],'arguments':call['arguments'],'statement':call['statement']})
            for closure in call['closures']:
                callbacks=[k for k,v in functions.items() if v['closure_site']==closure]
                require(callbacks,'unclosed-authored-callback:'+closure)
                validate_closure_callback(closure,call,callbacks,functions)
                for dest in callbacks:edges.append({'caller':key,'callee':dest,'kind':'authored-callback','line':call['line'],'target':closure});todo.append(dest)
            for callback in call['named_callbacks']:
                callbacks=resolve(callback,functions,byname,bybase)
                if not callbacks:
                    standard_callbacks.append(dict(standard_named_callback(callback,call['target']),caller=key,line=call['line']))
                if callbacks:validate_named_callback(callback,call['target'],callbacks,functions)
                for dest in callbacks:edges.append({'caller':key,'callee':dest,'kind':'named-authored-callback','line':call['line'],'target':callback});todo.append(dest)
    frontier=[]
    for target,sites in sorted(external.items()):
        types=sorted(set(x['result_type'] for x in sites))
        rows=[functions[x['caller']]['calls'] for x in sites]
        calls=[next(c for c in row if c['line']==site['line']) for row,site in zip(rows,sites)]
        kind=classify_external(target,[c['result_type'] for c in calls],[[a['type'] for a in c['arguments']] for c in calls])
        frontier.append({'target':target,'kind':kind,'result_types':types,'sites':sites})
    nodes={key:functions[key] for key in sorted(seen)}
    allocations=[]
    for match in re.finditer(r'^(alloc\w+) \((.*?)size: (\d+), align: (\d+)\) \{',mir,re.M):
        allocations.append({'id':match[1],'bytes':int(match[3]),'alignment':int(match[4]),'header':match[0][:-2]})
    require(len(allocations)==sum(line.startswith('alloc') and line.endswith('{') for line in mir.splitlines()),'complete-constant-allocation-parse')
    literals=literal_tokens(mir);values=sorted(set(x['value'] for x in literals));bound=max(len(x.encode()) for x in values)
    assignments=[dict(value,function=key) for key,row in nodes.items() for value in row['str_assignments']]
    incoming=[{'function':key,'parameter':p,'type':typ} for key,row in nodes.items() for p,typ in row['params'].items() if re.search(r'\bstr\b',typ)]
    declared_ids={x['id'] for x in allocations}
    unresolved=sorted(set(re.findall(r'\balloc\d+\b',mir))-declared_ids)
    require(not unresolved,'unresolved-compiler-allocation')
    return {'schema':2,'roots':rootkeys,'declared_roots':list(ROOTS),'compiled_function_bodies':len(functions),
        'compiled_body_inventory':{key:{field:row[field] for field in ('name','MIR_sha256','MIR_bytes')} for key,row in functions.items()},'nodes':nodes,
        'edges':sorted(edges,key=lambda x:(x['caller'],x['line'],x['kind'],x['callee'])),
        'external_frontier':frontier,'standard_named_callbacks':sorted(standard_callbacks,key=lambda x:(x['caller'],x['line'])),'source_str_assignments':assignments,'direct_str_parameters':incoming,
        'literal_pool':{'scope':'entire exact compiler MIR including constants and promotions; conservative superset of selected route origins',
            'occurrences':len(literals),'values':values,'max_utf8_bytes':bound,'max_scalar_leaves':max(len(x) for x in values)},
        'constant_allocations':{'scope':'all frozen compiler constant allocations; includes relocation-bearing aggregates as deliberate overcoverage','count':len(allocations),'unique_ids':len(declared_ids),'unresolved_ids':unresolved,'members':allocations,'max_bytes':max(x['bytes'] for x in allocations)},
        'L_str_source_candidate':max(bound,max(x['bytes'] for x in allocations)),
        'no_runtime_from_bytes_to_authored_str':True,'actual_runtime':False,'operational_grant':False}
