#!/usr/bin/env python3
"""Independent typed-MIR census and conservative call/constant reconstruction.

Imports no producer analysis. The candidate graph is loaded only after our
independent fixed point, to compare claimed coverage and expose missing edges.
This is an offline source-interface review, never runtime or OTA authority.
"""
import collections,gzip,hashlib,json,pathlib,re
D=pathlib.Path(__file__).resolve().parent;R=D.parents[1];V=R/'verification'
BASE=V/'swift-guarded-snapshot-loader-work-source146';P=V/'swift-guarded-snapshot-string-provenance'
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(n,j):(D/n).write_text(json.dumps(j,indent=2,sort_keys=True)+'\n')
def lex(line):
    """Remove MIR comments while independently decoding cooked str tokens."""
    code=[];values=[];i=0
    while i<len(line):
        if line.startswith('//',i):break
        c=line[i]
        if c=="'":
            char=re.match(r"'(?:[^'\\]|\\(?:u\{[0-9a-fA-F_]+\}|x[0-9a-fA-F]{2}|.))'",line[i:])
            if char:code.append(char[0]);i+=len(char[0]);continue
        if c!='"':code.append(c);i+=1;continue
        start=i;i+=1;buf=[]
        while i<len(line):
            c=line[i];i+=1
            if c=='"':break
            if c!='\\':buf.append(c);continue
            c=line[i];i+=1
            if c=='u':
                assert line[i]=='{';end=line.index('}',i);buf.append(chr(int(line[i+1:end].replace('_',''),16)));i=end+1
            elif c=='x':buf.append(chr(int(line[i:i+2],16)));i+=2
            else:buf.append({'n':'\n','r':'\r','t':'\t','0':'\0','\\':'\\','"':'"',"'":"'"}[c])
        else:raise AssertionError('unclosed string')
        code.append(line[start:i]);text=''.join(buf)
        if start==0 or line[start-1]!='b':values.append(text)
    return ''.join(code).strip(),values
def generic_free(s):
    out=[];stack=0
    for i,c in enumerate(s):
        if c=='<':stack+=1
        elif c=='>' and (i==0 or s[i-1]!='-'):stack-=1
        elif not stack:out.append(c)
        assert stack>=0
    assert stack==0
    return ''.join(out).replace('::::','::').strip(':')
def split_call(s):
    """Find actual argument list, respecting nested fn types and angle args."""
    angle=0;quoted=False;escape=False
    for i,c in enumerate(s):
        if quoted:
            if escape:escape=False
            elif c=='\\':escape=True
            elif c=='"':quoted=False
        elif c=='"':quoted=True
        elif c=='<':angle+=1
        elif c=='>' and (i==0 or s[i-1]!='-'):angle-=1
        elif c=='(' and angle==0:return s[:i],s[i:]
    raise AssertionError('no argument list '+s)
def main():
    text=gzip.decompress((BASE/'whole-source146.mir.gz').read_bytes()).decode();lines=text.splitlines(keepends=True)
    ref=json.loads((BASE/'source-reference-map.json').read_text())
    source={m['path']:(R/m['source']).read_text() for m in ref['members'] if m['path'].endswith('.rs')}
    functions={};byname=collections.defaultdict(list);bymethod=collections.defaultdict(list);closureindex=collections.defaultdict(list)
    literals=[];allocations=[];statics=[];constants=[];i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith('alloc') and line.rstrip().endswith('{'):
            m=re.fullmatch(r'(alloc\w+) \((.*?)size: (\d+), align: (\d+)\) \{\n?',line);assert m,line
            allocations.append({'id':m[1],'bytes':int(m[3]),'header':line.strip()})
            i+=1
            while lines[i].strip()!='}':i+=1
            i+=1;continue
        if line.startswith(('static ','const ')):
            (statics if line.startswith('static ') else constants).append({'line':i+1,'header':line.strip()})
        _,vs=lex(line);literals.extend(vs)
        if not line.startswith('fn '):i+=1;continue
        start=i;i+=1
        while lines[i]!='}\n':i+=1
        body=''.join(lines[start:i+1]);header=line.strip();head,ret=header[:-2].rsplit(') -> ',1)
        n=head.index('(');name=head[3:n];params=dict(re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)',head[n+1:]))
        loc=re.search(r'/owned-work/vm/([^:]+):(\d+):',name);owner=''
        if loc:owner=source[loc[1]].splitlines()[int(loc[2])-1]
        key='f%04d'%len(functions);row={'name':name,'header':header,'MIR_sha256':sha(body.encode()),'MIR_bytes':len(body.encode()),'params':params,'return_type':ret,
            'owner_source_line':owner,'method':name.rsplit('::',1)[-1],'calls':[],'string_assignments':[],'carrier_operations':[],'sensitive_operations':[],'indirect_calls':[]}
        localtypes=dict(params);localtypes['_0']=ret
        for local in body.splitlines():
            stripped=local.strip()
            m=re.match(r'let (?:mut )?(_\d+): (.*?);',stripped)
            if m:localtypes[m[1]]=m[2]
        cl=re.search(r'\{closure@([^}]+)\}',head[n+1:])
        if cl:closureindex[cl[1]].append(key)
        for ln,statement in enumerate(body.splitlines(),1):
            if ln>1:
                _,vs=lex(statement);literals.extend(vs)
            if not statement.startswith('        '):continue
            code,_=lex(statement)
            if not code:continue
            call=None
            if re.search(r' -> (?:\[|unwind |!)',code):
                rhs=code.split(' = ',1)[-1];target,args=split_call(rhs)
                if target not in ('switchInt','assert','drop'):
                    dest=code.split(' = ',1)[0] if ' = ' in code else None
                    call={'line':ln,'target':target,'statement':code,'result_type':localtypes.get(dest,'!'),
                        'closures':sorted(set(re.findall(r'\{closure@([^}]+)\}',code))),
                        'named_callbacks':sorted(set(re.findall(r'\{([^{}]+)\}',target)))}
                    row['calls'].append(call)
                    if re.fullmatch(r'(?:copy |move )?_\d+',target):row['indirect_calls'].append(call)
            ass=re.match(r'(_\d+) = (.*);$',code)
            if ass and localtypes.get(ass[1]) in ('&str',"&'static str",'&mut str'):
                rhs=ass[2]
                origin='literal' if rhs.startswith('const "') else 'preserved_reference' if rhs.startswith(('copy ','move ','&','no_retag ')) else 'authored_or_external_return' if call else 'unknown'
                row['string_assignments'].append({'line':ln,'destination':ass[1],'statement':code,'origin':origin})
            if any(t in code for t in ('SwiftRunFailure','SwiftValidationFailure','experimental::Failure','control::Fault','first_failure:','Policy::')):
                row['carrier_operations'].append({'line':ln,'statement':code})
            if any(t in code for t in ('from_utf8','String','*const str','*mut str','Transmute','from_raw_parts','cast::<','transmute')):
                row['sensitive_operations'].append({'line':ln,'statement':code})
        functions[key]=row;byname[name].append(key);bymethod[row['method']].append(key);i+=1
    assert len(functions)==2009
    special={'B':'SnapshotBranchV1','P':'SnapshotAdoptionV1','D':'SwiftDeclaration','impl MeterControl':'SwiftControl','B::Access':'SnapshotAccessV1'}
    def resolve(target):
        if target in byname:return byname[target]
        # Resolve qualified traits by exact selected type; standard generic
        # receivers are kept external, never resolved from a method name alone.
        if target.startswith('<') and ' as ' in target:
            receiver=target[1:].split(' as ',1)[0]
            if 'SharedControlV1>::shared_control' in target:receiver='SnapshotAccessV1'
            receiver=special.get(receiver,receiver)
            owner=generic_free(receiver).split('::')[-1].removeprefix('&').removeprefix('mut ')
            method=generic_free(target.rsplit('>::',1)[-1])
            candidates=[]
            for k in bymethod[method]:
                row=functions[k]
                first=row['params'].get('_1','').lstrip('&').removeprefix('mut ')
                first=generic_free(first).split('::')[-1]
                returned=generic_free(row['return_type']).split('::')[-1]
                if owner in (first,returned):candidates.append(k)
            return candidates
        plain=generic_free(target)
        if plain in byname:return byname[plain]
        if '::' not in plain:return []
        owner,method=plain.rsplit('::',1);ownername=owner.rsplit('::',1)[-1]
        # Authored impl headers supply receiver identity; include every body for
        # that receiver and method (CTFE and repeated macro bodies included).
        candidates=[k for k in bymethod[method] if ownername in re.findall(r'\b[A-Za-z_]\w*\b',functions[k]['owner_source_line'])]
        if owner.count('::'):
            module=owner.rsplit('::',1)[0]
            scoped=[k for k in candidates if functions[k]['name'].startswith(module+'::')]
            if scoped:return scoped
        return candidates
    roots=[]
    for name in ('run_one_fixture_v1','run_prepaid_fixture_v1','run_one_loaded_fixture_v1','destroy_returned_fixture_v1','release_after_retirement_v1'):
        assert byname[name];roots.extend(byname[name])
    roots.extend(k for k,row in functions.items() if row['method']=='drop' and 'PrepaidOwnedV1' in row['owner_source_line'])
    work=list(roots);seen=set();edges=[];external=[];named=[]
    while work:
        k=work.pop()
        if k in seen:continue
        seen.add(k)
        for call in functions[k]['calls']:
            dests=resolve(call['target'])
            for dest in dests:
                edges.append({'caller':k,'callee':dest,'line':call['line'],'kind':'authored','target':call['target']});work.append(dest)
            if not dests:external.append(dict(call,caller=k))
            for closure in call['closures']:
                assert closureindex[closure],closure
                for dest in closureindex[closure]:
                    edges.append({'caller':k,'callee':dest,'line':call['line'],'kind':'authored-callback','target':closure});work.append(dest)
            for callback in call['named_callbacks']:
                dests=resolve(callback)
                item={'caller':k,'line':call['line'],'target':callback,'outer_target':call['target'],'callees':dests}
                named.append(item)
                for dest in dests:
                    edges.append({'caller':k,'callee':dest,'line':call['line'],'kind':'named-authored-callback','target':callback});work.append(dest)
    # Producer data enters only as a comparison target, never traversal input.
    candidate=json.loads((P/'graph.json').read_text());claimed=set(candidate['nodes'])
    ours={k:functions[k] for k in sorted(seen)}
    body_disagreements=[k for k in sorted(claimed&seen) if functions[k]['MIR_sha256']!=candidate['nodes'][k]['MIR_sha256'] or functions[k]['MIR_bytes']!=candidate['nodes'][k]['MIR_bytes']]
    key=lambda e:(e['caller'],e['callee'],e['line'],e['kind'],e['target'])
    oe={key(e) for e in edges if e['kind']!='named-authored-callback'};ce={key(e) for e in candidate['edges']}
    named_authored=[x for x in named if x['callees']]
    result={'schema':1,'independent_no_producer_import':True,'compiled_function_bodies':len(functions),'selected_bodies':len(seen),'authored_and_closure_edges':len(oe),'named_authored_callback_edges':sum(len(x['callees']) for x in named_authored),
        'missing_candidate_bodies':sorted(seen-claimed),'extra_candidate_bodies':sorted(claimed-seen),'MIR_body_disagreements':body_disagreements,
        'independent_edges_missing_in_candidate':[list(x) for x in sorted(oe-ce)],'candidate_edges_not_independently_resolved':[list(x) for x in sorted(ce-oe)],
        'named_callback_sites':named,'direct_str_assignments':sum(len(x['string_assignments']) for x in ours.values()),'carrier_operations':sum(len(x['carrier_operations']) for x in ours.values()),
        'indirect_calls':[dict(c,function=k) for k,r in ours.items() for c in r['indirect_calls']],
        'sensitive_operations':{k:r['sensitive_operations'] for k,r in ours.items() if r['sensitive_operations']},
        'direct_str_ports':[{'function':k,'name':r['name'],'parameter':p,'type':t,'incoming':[e for e in edges if e['callee']==k]} for k,r in ours.items() for p,t in r['params'].items() if re.search(r'\bstr\b',t)],
        'literal_occurrences':len(literals),'literal_unique':len(set(literals)),'literal_max_utf8':max(map(lambda x:len(x.encode()),literals)),
        'allocations':allocations,'allocation_count':len(allocations),'allocation_max':max(x['bytes'] for x in allocations),
        'statics':statics,'constant_headers':constants,'source_runtime_or_grant':False}
    dump('typed-graph.json',{'roots':roots,'nodes':ours,'edges':edges,'external_sites':external})
    dump('analysis.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('statics','constant_headers','allocations','direct_str_ports','sensitive_operations','named_callback_sites')},sort_keys=True))
if __name__=='__main__':main()
