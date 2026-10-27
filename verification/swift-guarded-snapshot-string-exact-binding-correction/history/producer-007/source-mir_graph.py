"""Offline source146 typed-MIR reference conservation. Never loads executable code."""
from __future__ import annotations
import collections, hashlib, json, re

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

def parse_functions(mir,source):
    functions={};byname=collections.defaultdict(list);bybase=collections.defaultdict(list)
    matches=list(re.finditer(r'^fn (.+?)\((.*?)\) -> (.+?) \{[^\n]*\n',mir,re.M))
    require(len(matches)==sum(line.startswith('fn ') for line in mir.splitlines()),'complete-function-header-parse')
    for ordinal,m in enumerate(matches):
        end=mir.index('\n}\n',m.end())+3;name=m[1];body=mir[m.start():end]
        key=f'f{ordinal:04d}';location=re.search(r'owned-work/vm/(.+?):(\d+):\d+:',name)
        owner=source[location[1]].splitlines()[int(location[2])-1] if location else ''
        locals_=dict(re.findall(r'^    let (?:mut )?(_\d+): (.*);(?:\s*//.*)?$',body,re.M));locals_.update(signature_params(m[2]))
        row={'name':name,'header':body.splitlines()[0],'params':signature_params(m[2]),'return_type':m[3],
             'MIR_sha256':sha(body.encode()),'MIR_bytes':len(body.encode()),'base':name.rsplit('::',1)[-1],
             'owner_source_line':owner,'calls':[],'str_assignments':[],'carrier_operations':[],'manufacture_review':[],'literal_occurrences':literal_tokens(body)}
        cl=re.search(r'\{closure@([^}]+)\}',m[2]);row['closure_site']=cl[1] if cl else None
        for ln,line in enumerate(body.splitlines(),1):
            if not line.startswith('        '):continue
            statement=code_only(line).strip()
            if not statement:continue
            if any(token in statement for token in ('SwiftRunFailure','SwiftValidationFailure','experimental::Failure','control::Fault','first_failure:','Policy::')):
                row['carrier_operations'].append({'line':ln,'statement':statement})
            iscall=(' -> [' in statement or ' -> unwind ' in statement or ' -> !' in statement)
            if iscall:
                rhs=statement.split(' = ',1)[-1];target=call_target(rhs)
                if target not in ('switchInt','assert','drop'):
                    dest=re.match(r'(_\d+) = ',statement)
                    row['calls'].append({'target':target,'statement':statement,'line':ln,
                        'result_type':locals_.get(dest[1],m[3] if dest and dest[1]=='_0' else '') if dest else '!',
                        'callbacks':sorted(set(re.findall(r'\{closure@([^}]+)\}',statement)))})
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

# This list states operations with reference-conserving standard interfaces.
# An unseen method or a new str constructor refuses and needs a new review.
STANDARD_METHODS=set('''add align_of and and_then any as_bytes as_micros as_mut as_mut_ptr as_ptr as_ref as_slice branch call call_mut call_once capacity cast checked_add checked_mul checked_sub chunks chunks_mut clone cmp contains copied copy_from_slice create_new ctime ctime_nsec default deref deref_mut dev div_ceil drop elapsed enumerate eq err expect extend_from_slice file_type fill filter find first flatten from from_bytes from_fn from_le_bytes from_millis from_raw_parts from_residual from_str_nonconst ge get get_mut get_or_insert index index_mut ino into_boxed_slice into_iter is_empty is_err is_file is_none is_none_or is_null is_ok is_some is_some_and iter iter_mut kind last last_mut last_os_error le len load map map_err map_or max metadata min mode mtime mtime_nsec ne new next now ok ok_or ok_or_else open or panic panic_fmt pop position push read replace resize rev saturating_add saturating_duration_since saturating_sub set size size_of step_by stream_position swap take then then_some to_le_bytes transpose truncate try_from try_into try_reserve_exact try_update unwrap unwrap_or wrapping_shl write zip'''.split())
NATIVE={'CC_SHA256','_NSGetArgc','_NSGetArgv','_NSGetEnviron','_NSGetExecutablePath','getcwd'}

def classify_external(target,result_types):
    plain=erase_generics(target);method=plain.split('::')[-1]
    if method in NATIVE and target.startswith('retained_profile_loader_v1::platform::'):
        return 'platform-numeric-or-raw-byte-interface-no-authored-str'
    require(not target.startswith(('experimental_','experimental::','control::','swift::','retained_profile_loader_v1::','<P as','<B as','<D as','<C as','<impl MeterControl as')),'unclosed-authored-edge:'+target)
    require(target.startswith(('std::','core::','Option::','Result::','Vec::','Instant::','OpenOptions::','Duration::','Atomic::','Cell::','Layout::','Arguments::','array::','FileType::','Path::','<','panic')),'unreviewed-external-namespace:'+target)
    require(method in STANDARD_METHODS,'unreviewed-external-method:'+target)
    if target.startswith('<') and ' as ' in target:
        receiver=target[1:].split(' as ',1)[0]
        if re.fullmatch(r'[A-Za-z][A-Za-z0-9_:]*',receiver) and method not in ('eq','ne','ge','le','cmp'):
            require(receiver.startswith('std::') or receiver in ('u8','u32','u64','usize','Instant','OsStr','R'),'unknown-nominal-trait-producer:'+target)
        elif not re.fullmatch(r'[A-Za-z][A-Za-z0-9_:]*',receiver):
            require(receiver.startswith(('Result<','Option<','std::','&','[','Vec<','Arc<','Flatten<','Enumerate<','Zip<','Rev<','StepBy<','Chunks<','ChunksMut<','{closure@','impl FnOnce')),'unknown-generic-trait-producer:'+target)
    if method=='from_raw_parts':require('u8>' in target,'unreviewed-raw-reference-construction')
    if method=='from_bytes':require('OsStr' in target,'unreviewed-bytes-to-string')
    if method=='from_str_nonconst':require(target.startswith('Arguments::'),'unreviewed-string-constructor')
    if method in ('open','read','write','metadata','last_os_error','kind','stream_position','file_type','is_file'):
        return 'native-file-error-interface-opaque-backing-separate-no-authored-code-string'
    if any(re.search(r'\bstr\b',t) for t in result_types):
        require(method in ('take','expect','from_residual','iter','enumerate','into_iter','next','get','index','as_ref','map','map_or','unwrap_or','deref','clone'), 'unreviewed-external-str-return:'+target)
        return 'reference-conserving-container-projection-or-element-transfer'
    if '{closure@' in target:return 'reference-conserving-adapter-all-authored-callbacks-expanded'
    return 'standard-logical-interface-no-new-authored-str-origin'

def analyze(mir,source):
    functions,byname,bybase=parse_functions(mir,source)
    rootkeys=[key for root in ROOTS for key in byname[root]]
    require(all(byname[root] for root in ROOTS),'all-selected-roots')
    # Compiler-generated drop glue is private; the only relevant authored Drop
    # hook is the actual PrepaidOwned leak-on-unwind accounting hook.
    rootkeys.extend(k for k in bybase['drop'] if 'PrepaidOwnedV1' in functions[k]['owner_source_line'])
    todo=list(rootkeys);seen=set();edges=[];external=collections.defaultdict(list)
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
            destinations=resolve(call['target'],functions,byname,bybase)
            if destinations:
                # Multiple compiler bodies for one declaration include CTFE and
                # identical macro occurrences. Include every matching body.
                for dest in destinations:edges.append({'caller':key,'callee':dest,'kind':'authored','line':call['line'],'target':call['target']});todo.append(dest)
            else:external[call['target']].append({'caller':key,'line':call['line'],'result_type':call['result_type'],'statement':call['statement']})
            for closure in call['callbacks']:
                callbacks=[k for k,v in functions.items() if v['closure_site']==closure]
                require(callbacks,'unclosed-authored-callback:'+closure)
                for dest in callbacks:edges.append({'caller':key,'callee':dest,'kind':'authored-callback','line':call['line'],'target':closure});todo.append(dest)
    frontier=[]
    for target,sites in sorted(external.items()):
        types=sorted(set(x['result_type'] for x in sites));kind=classify_external(target,types)
        frontier.append({'target':target,'kind':kind,'result_types':types,'sites':sites})
    nodes={key:functions[key] for key in sorted(seen)}
    allocations=[]
    for match in re.finditer(r'^(alloc\w+) \((.*?)size: (\d+), align: (\d+)\) \{',mir,re.M):
        allocations.append({'id':match[1],'bytes':int(match[3]),'alignment':int(match[4]),'header':match[0][:-2]})
    require(len(allocations)==sum(line.startswith('alloc') and line.endswith('{') for line in mir.splitlines()),'complete-constant-allocation-parse')
    literals=literal_tokens(mir);values=sorted(set(x['value'] for x in literals));bound=max(len(x.encode()) for x in values)
    assignments=[dict(value,function=key) for key,row in nodes.items() for value in row['str_assignments']]
    incoming=[{'function':key,'parameter':p,'type':typ} for key,row in nodes.items() for p,typ in row['params'].items() if re.search(r'\bstr\b',typ)]
    return {'schema':1,'roots':rootkeys,'declared_roots':list(ROOTS),'compiled_function_bodies':len(functions),'nodes':nodes,
        'edges':sorted(edges,key=lambda x:(x['caller'],x['line'],x['kind'],x['callee'])),
        'external_frontier':frontier,'source_str_assignments':assignments,'direct_str_parameters':incoming,
        'literal_pool':{'scope':'entire exact compiler MIR including constants and promotions; conservative superset of selected route origins',
            'occurrences':len(literals),'values':values,'max_utf8_bytes':bound,'max_scalar_leaves':max(len(x) for x in values)},
        'constant_allocations':{'scope':'all frozen compiler constant allocations; includes relocation-bearing aggregates as deliberate overcoverage','count':len(allocations),'members':allocations,'max_bytes':max(x['bytes'] for x in allocations)},
        'L_str_source_candidate':max(bound,max(x['bytes'] for x in allocations)),
        'no_runtime_from_bytes_to_authored_str':True,'actual_runtime':False,'operational_grant':False}
