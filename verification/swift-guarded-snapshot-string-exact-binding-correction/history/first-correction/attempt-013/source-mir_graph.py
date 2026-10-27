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
    return dict(re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)',params))

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
    matches=list(re.finditer(r'^fn (.+?)\((.*?)\) -> (.+?) \{[^\n]*\n',mir,re.M))
    require(len(matches)==sum(line.startswith('fn ') for line in mir.splitlines()),'complete-function-header-parse')
    for ordinal,m in enumerate(matches):
        end=mir.index('\n}\n',m.end())+3;name=m[1];body=mir[m.start():end]
        key=f'f{ordinal:04d}';location=re.search(r'owned-work/vm/(.+?):(\d+):\d+:',name)
        owner=source[location[1]].splitlines()[int(location[2])-1] if location else ''
        locals_={}
        for line in body.splitlines():
            local=re.fullmatch(r'\s*let (?:mut )?(_\d+): (.*);\s*',code_only(line))
            if local:locals_[local[1]]=local[2]
        locals_.update(signature_params(m[2]));locals_.setdefault('_0',m[3])
        row={'name':name,'header':body.splitlines()[0],'params':signature_params(m[2]),'return_type':m[3],
             'MIR_sha256':sha(body.encode()),'MIR_bytes':len(body.encode()),'base':name.rsplit('::',1)[-1],
             'owner_source_line':owner,'local_types':locals_,'calls':[],'str_assignments':[],'carrier_operations':[],'manufacture_review':[],'literal_occurrences':literal_tokens(body),'typed_statements':[]}
        cl=re.search(r'\{closure@([^}]+)\}',m[2]);row['closure_site']=cl[1] if cl else None
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
                        'result_type':locals_.get(dest[1],m[3] if dest and dest[1]=='_0' else '') if dest else '!',
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

def resolve(target,functions,byname,bybase):
    if target in byname:return byname[target]
    selected=None
    if target.startswith('<B as ClosedBranchV1>::'):selected='SnapshotBranchV1'
    elif 'as SharedControlV1>::shared_control' in target:selected='SnapshotAccessV1'
    elif target.startswith('<P as ClosedAdoptionV1>::'):selected='SnapshotAdoptionV1'
    elif 'as experimental::account::MeterControl>::' in target:selected='SwiftControl'
    elif target.startswith(('<D as Declaration>::','<D as Default>::')):selected='SwiftDeclaration'
    elif target.startswith('<swift::ValidatedSwiftReactor as experimental::cache::borrowed::SnapshotView>::'):selected='ValidatedSwiftReactor'
    if selected:
        return [key for key in bybase[target.rsplit('::',1)[-1]] if re.search(r'\b'+selected+r'\b',functions[key]['owner_source_line']) or functions[key]['return_type'].split('::')[-1]==selected]
    if target.startswith('<') and ' as ' in target and re.fullmatch(r'[A-Za-z][A-Za-z0-9_:]*',target[1:].split(' as ',1)[0]):
        receiver=target[1:].split(' as ',1)[0];receiver_base=receiver.split('::')[-1].lstrip('&');base=target.rsplit('::',1)[-1];good=[]
        for key in bybase[base]:
            row=functions[key];first=row['params'].get('_1','').lstrip('&').removeprefix('mut ').split('::')[-1]
            if first==receiver_base or row['return_type'].split('::')[-1]==receiver_base:good.append(key)
        if good:
            module=receiver.rsplit('::',1)[0] if '::' in receiver else ''
            exact=[k for k in good if functions[k]['name'].startswith(module+'::<impl at ')] if module else []
            return exact or good
    plain=erase_generics(target)
    if plain in byname:return byname[plain]
    base=plain.rsplit('::',1)[-1];owner=plain.rsplit('::',1)[0].rsplit('::',1)[-1] if '::' in plain else ''
    if not owner:return []
    good=[key for key in bybase[base] if re.search(r'\b'+re.escape(owner)+r'\b',functions[key]['owner_source_line'])]
    module=plain.rsplit('::',2)[0] if plain.count('::')>=2 else ''
    exact=[key for key in good if functions[key]['name'].startswith(module+'::<impl at ')] if module else []
    return exact or good

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
    return json.loads((Path(__file__).resolve().parent/'external-contracts.json').read_text())['contracts']

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
                # Multiple compiler bodies for one declaration include CTFE and
                # identical macro occurrences. Include every matching body.
                for dest in destinations:edges.append({'caller':key,'callee':dest,'kind':'authored','line':call['line'],'target':call['target']});todo.append(dest)
            else:external[call['target']].append({'caller':key,'line':call['line'],'result_type':call['result_type'],'statement':call['statement']})
            for closure in call['closures']:
                callbacks=[k for k,v in functions.items() if v['closure_site']==closure]
                require(callbacks,'unclosed-authored-callback:'+closure)
                for dest in callbacks:edges.append({'caller':key,'callee':dest,'kind':'authored-callback','line':call['line'],'target':closure});todo.append(dest)
            for callback in call['named_callbacks']:
                callbacks=resolve(callback,functions,byname,bybase)
                if not callbacks:
                    standard_callbacks.append(dict(standard_named_callback(callback,call['target']),caller=key,line=call['line']))
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
    return {'schema':2,'roots':rootkeys,'declared_roots':list(ROOTS),'compiled_function_bodies':len(functions),'nodes':nodes,
        'edges':sorted(edges,key=lambda x:(x['caller'],x['line'],x['kind'],x['callee'])),
        'external_frontier':frontier,'standard_named_callbacks':sorted(standard_callbacks,key=lambda x:(x['caller'],x['line'])),'source_str_assignments':assignments,'direct_str_parameters':incoming,
        'literal_pool':{'scope':'entire exact compiler MIR including constants and promotions; conservative superset of selected route origins',
            'occurrences':len(literals),'values':values,'max_utf8_bytes':bound,'max_scalar_leaves':max(len(x) for x in values)},
        'constant_allocations':{'scope':'all frozen compiler constant allocations; includes relocation-bearing aggregates as deliberate overcoverage','count':len(allocations),'unique_ids':len(declared_ids),'unresolved_ids':unresolved,'members':allocations,'max_bytes':max(x['bytes'] for x in allocations)},
        'L_str_source_candidate':max(bound,max(x['bytes'] for x in allocations)),
        'no_runtime_from_bytes_to_authored_str':True,'actual_runtime':False,'operational_grant':False}
