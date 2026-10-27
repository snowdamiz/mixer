"""Fresh complete MIR/source reconstruction; no producer analyzer imported.

The later resolver controls import only the previously accepted exact-binding
analyzers. All input parsing, census, lineage and allocation transport below is
independently implemented here.
"""
from support import *
import collections, copy, gzip, importlib.util, re
LEX=re.compile(r'''//[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\(?:u\{[0-9a-fA-F_]+\}|x[0-9a-fA-F]{2}|.)|[^'\\\n])' ''',re.X)
ALLOC=re.compile(r'\balloc\d+\b')
ROOTS=[str(V/p) for p in ['swift-guarded-snapshot-loader-work-source146/owned-work/vm','swift-guarded-snapshot-outer-parent-independent/owned-work/compiler-metadata-mir/vm','swift-guarded-snapshot-scoped-binding-source/owned-work/positive/vm','swift-guarded-snapshot-owned-provider-work-storage/owned-work/capture-layout/vm']]
TYPES=['ReviewedFixtureBindingV1','FrozenFixtureV1','ImmutableIdentityPreimageV1','ImmutableFixtureIdentitiesV1','PreexistingImmutableBindingV1','OneFixtureOuterRequestV1']
BASE='experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1'
TYPE_PATHS=TYPES+[BASE+'::'+n for n in TYPES[:2]]+[BASE+'::outer_parent_v1::'+n for n in TYPES[2:]]
LIFES=re.compile(r'(?<![\w:])('+'|'.join(map(re.escape,sorted(TYPE_PATHS,key=len,reverse=True)))+r")(?:::)?<'_>")
PROBES=[[],['outer_parent_account_layout_query_v1','outer_parent_layout_query_v1'],['outer_parent_account_layout_query_v1','outer_parent_layout_query_v1','scoped_result_layout_query_v1','scoped_local_binding_compiles_v1'],['owned_provider_remaining_layout_query_v1']]
def outside(text,fn,comments=True):
    pieces=[];pos=0
    for m in LEX.finditer(text):
        pieces.append(fn(text[pos:m.start()]));token=m[0]
        if not (comments and token.startswith('//')):pieces.append(token)
        pos=m.end()
    pieces.append(fn(text[pos:]));return ''.join(pieces)
def projected(text,oldroot=False):
    if text.startswith('alloc'):return text
    def f(s):
        for p in ROOTS:s=s.replace(p,ROOTS[0] if oldroot else '<SOURCE>')
        if not oldroot:s=re.sub(r'(?<=<impl at )<SOURCE>/([^\s:]+):\d+:\d+: \d+:\d+(?=>)',r'<SOURCE>/\1:<DISPLAY-SPAN>',s)
        s=LIFES.sub(r'\1',s)
        return s.replace("selected_outer_request_v1::<'_>",'selected_outer_request_v1')
    return '\n'.join(s.rstrip() for s in outside(text,f).splitlines() if s.strip())
def allocation_shape(text):
    refs=[]
    def f(s):
        def sub(m):refs.append(m[0]);return '<ALLOC>'
        return ALLOC.sub(sub,s)
    if text.startswith('alloc'):
        out=[]
        for line in text.splitlines():
            a,sep,z=line.rpartition('│')
            out.append(f(a)+sep+z if sep else f(line))
        return '\n'.join(out),refs
    return outside(text,f,comments=False),refs
def blocks(stage):
    # Top-level boundaries are structural lines in compiler MIR. Every byte
    # belongs to a construct or to blank/top-level comment text; unknown syntax
    # fails rather than silently disappearing.
    raw=gzip.decompress((V/MIRS[stage]).read_bytes()).decode();out=[];start=None;offset=0;ignored=0
    for line in raw.splitlines(keepends=True):
        stripped=line.rstrip('\r\n')
        if start is None:
            if not stripped.strip() or stripped.startswith('//'):ignored+=len(line)
            else:
                require(not stripped[0].isspace(),'independent MIR top-level indentation')
                require(stripped.startswith(('fn ','const ','static ','alloc')) or '::{constant#' in stripped,'unrecognized top-level syntax')
                if stripped.endswith(';'):out.append(stripped)
                else:require(stripped.endswith(' {'),'non-braced top-level');start=offset
        else:
            if stripped=='}':out.append(raw[start:offset+len(line)].rstrip('\r\n'));start=None
            elif stripped:require(stripped[0].isspace(),'unexpected nested top-level line')
        offset+=len(line)
    require(start is None and offset==len(raw),'complete MIR coverage')
    return out,{'raw_sha256':sha(raw.encode()),'raw_bytes':len(raw.encode()),'characters':len(raw),'top_level_comment_or_blank_characters':ignored,'constructs':len(out),'uncovered_noncomment_bytes':0}
def isprobe(b,stage):
    h=b.split('\n',1)[0]
    if stage==3 and h.startswith(('static OWNED_PROVIDER_LAYOUT_FORCE_V1:', 'const OWNED_PROVIDER_LAYOUT_FORCE_V1::{constant#')):return True
    return any(h.startswith('fn '+n+'(') or h.startswith(n+'::{constant#') or h.startswith('const '+n+'::{constant#') for n in PROBES[stage])
def isprovider(b):return b.startswith(('fn describe_existing_owner_candidate_v1(', 'fn describe_existing_owner_candidate_v1::', 'const describe_existing_owner_candidate_v1', 'const InputBackingDescriptionV1::'))
def decode_string(token):
    s=token[1:-1];o=[];i=0
    while i<len(s):
        if s[i]!='\\':o.append(s[i]);i+=1;continue
        i+=1;c=s[i];i+=1
        basic={'n':'\n','r':'\r','t':'\t','0':'\0','\\':'\\','"':'"',"'":"'"}
        if c in basic:o.append(basic[c])
        elif c=='x':o.append(chr(int(s[i:i+2],16)));i+=2
        elif c=='u':
            require(s[i]=='{','unicode escape open');end=s.index('}',i);o.append(chr(int(s[i+1:end].replace('_',''),16)));i=end+1
        else:raise AssertionError('unsupported cooked string escape '+c)
    result=''.join(o);result.encode('utf8');return result
def census(pool):
    kinds=collections.Counter();lits=[];alloc=[];refs=set();details=[]
    for b in pool:
        k='allocation' if b.startswith('alloc') else 'function' if b.startswith('fn ') else 'singleline_constant' if '\n' not in b else 'braced_constant_static_anonymous';kinds[k]+=1
        refs.update(allocation_shape(b)[1]);details.append({'header':b.split('\n',1)[0],'raw_sha256':sha(b.encode()),'projected_shape_sha256':sha(allocation_shape(projected(b))[0].encode())})
        if k=='allocation':
            h=re.fullmatch(r'(alloc\d+) \(.*?size: (\d+), align: (\d+)\) \{',b.split('\n',1)[0]);require(h is not None,'independent allocation header')
            alloc.append({'id':h[1],'bytes':int(h[2]),'alignment':int(h[3]),'raw_header':h[0],'raw_sha256':sha(b.encode())});continue
        for m in LEX.finditer(b):
            if m[0].startswith('"') and not (m.start()>0 and b[m.start()-1]=='b'):lits.append(decode_string(m[0]))
    ids={a['id'] for a in alloc};values=sorted(set(lits));ml=max(map(lambda s:len(s.encode()),values),default=0);ma=max((x['bytes'] for x in alloc),default=0)
    return {'constructs':len(pool),'counts':dict(kinds),'literal_occurrences':len(lits),'literal_unique':len(values),'literal_values':values,'max_literal_utf8_bytes':ml,'allocations':len(alloc),'unique_allocation_ids':len(ids),'allocation_members':alloc,'unresolved_ids':sorted(refs-ids),'max_allocation_extent':ma,'conditional_conservative_envelope':max(ml,ma)},details
def census_review(stage):
    bs,coverage=blocks(stage);prod=[b for b in bs if not isprobe(b,stage)];probe=[b for b in bs if isprobe(b,stage)]
    p,details=census(prod);q,qd=census(probe);expected=read(C/'constant-census.json')['stages'][stage]
    require(p==expected['production'] and q==expected['query_suffix'],'independent entire census differs')
    require([dict(header=b.split('\n',1)[0],raw_sha256=sha(b.encode()),raw_text=b) for b in probe]==expected['query_constructs'],'exact query body census')
    save(f'census-stage-{stage}.json',{'schema':1,'source_tree':TREES[stage],'coverage':coverage,'production':p,'query_suffix':q,'construct_inventory':details,'query_inventory':qd})
    print(json.dumps({'stage':stage,'production_constructs':len(prod),'query_constructs':len(probe),'literal_occurrences':p['literal_occurrences'],'envelope':p['conditional_conservative_envelope'],'complete_independent_census':True}))
def compare(old,new):
    require(len(old)==len(new),'independent full transport count')
    mapping={};inverse={};od={};nd={};oc=collections.defaultdict(set);nc=collections.defaultdict(set);context=None;positions=[];nonalloc=[]
    def bind(a,b):
        require(mapping.get(a,b)==b and inverse.get(b,a)==a,'allocation role non-bijection');mapping[a]=b;inverse[b]=a
    def match(a,b):
        aa,ar=allocation_shape(a);bb,br=allocation_shape(b);require(aa==bb,'complete typed operation/payload mismatch '+a[:180]);require(len(ar)==len(br),'allocation role arity')
        for x,y in zip(ar,br):bind(x,y)
    for i,(a,b) in enumerate(zip(old,new)):
        a=projected(a);b=projected(b)
        require(a.startswith('alloc')==b.startswith('alloc'),'construct kind mismatch')
        if a.startswith('alloc'):
            x=ALLOC.match(a)[0];y=ALLOC.match(b)[0];require(od.get(x,a)==a and nd.get(y,b)==b,'repeated ID payload mismatch')
            od[x]=a;nd[y]=b;oc[x].add(context);nc[y].add(context);positions.append((x,y))
        else:
            match(a,b);context=sha(allocation_shape(a)[0].encode());nonalloc.append({'index':i,'header':a.split('\n',1)[0],'shape_sha256':context})
    visited=set()
    while len(visited)<len(od):
        todo=[a for a in mapping if a in od and a not in visited]
        if not todo:
            left=collections.defaultdict(list);right=collections.defaultdict(list)
            for a in set(od)-visited:left[(allocation_shape(od[a])[0],tuple(sorted(oc[a])))].append(a)
            for b in set(nd)-set(inverse):right[(allocation_shape(nd[b])[0],tuple(sorted(nc[b])))].append(b)
            for key,aa in left.items():
                bb=right.get(key,[])
                if len(aa)==len(bb)==1:bind(aa[0],bb[0])
            todo=[a for a in mapping if a in od and a not in visited];require(todo,'unresolved ambiguous allocation mapping')
        for a in todo:
            require(mapping[a] in nd,'relocation unresolved');match(od[a],nd[mapping[a]]);visited.add(a)
    require(set(mapping)==set(od) and set(inverse)==set(nd),'complete allocation identity coverage')
    require(all(mapping[a]==b for a,b in positions),'allocation occurrence positions disagree with role-derived mapping')
    return {'constructs':len(old),'functions':sum(b.startswith('fn ') for b in old),'singleline_constants':sum('\n' not in b for b in old),'allocation_occurrences':len(positions),'allocation_ids':len(od),'mapping':mapping,'all_nonallocation_rows':nonalloc,'allocation_pairing_uses_offset_or_position':False,'complete_typed_body_payload_extent_alignment_relocation_equality':True}
def transport_review(which):
    cur,_=blocks(3);cur=[b for b in cur if not isprobe(b,3)]
    if which=='scoped':
        old,_=blocks(2);old=[b for b in old if not isprobe(b,2)];cur=[b for b in cur if not isprovider(b)]
        r=compare(old,cur);require(r['constructs']==6006 and r['singleline_constants']==1785,'full6006 amendment missing');expected=read(C/'full-base-correspondence.json')
    else:
        old,_=blocks(0);oldconst=next(b for b in old if b.startswith('const COMPILED: '));values=[decode_string(m[0]) for m in LEX.finditer(oldconst) if m[0].startswith('"')]
        require(len(values)==5 and all(len(x.encode())==64 for x in values),'exact original identity literals')
        def payload(b):
            if not b.startswith('alloc'):return None
            raw=[]
            for line in b.splitlines()[1:-1]:
                p=line.split('│')
                if len(p)!=3 or not all(re.fullmatch('[0-9a-f]{2}',w) for w in p[1].split()):return None
                raw.extend(int(w,16) for w in p[1].split())
            return bytes(raw)
        removed=[b for b in old if payload(b) in {s.encode() for s in values}];require(len(removed)==5,'exact five allocation removals')
        index=collections.defaultdict(list)
        for i,b in enumerate(cur):
            if not b.startswith('alloc'):index[allocation_shape(projected(b))[0]].append(i)
        used=set();rows=[];unmatched=[]
        for b in old:
            if b.startswith('alloc'):continue
            choices=[i for i in index[allocation_shape(projected(b))[0]] if i not in used]
            if not choices:unmatched.append(b);continue
            i=choices[0];used.add(i);rows.append({'old_header':b.split('\n',1)[0],'current_header':cur[i].split('\n',1)[0],'old_raw_sha256':sha(b.encode()),'current_raw_sha256':sha(cur[i].encode())})
        require(unmatched==[oldconst],'all original nonallocation bodies except COMPILED correspond')
        new=[b for i,b in enumerate(cur) if b.startswith('alloc') or i in used]
        r=compare([b for b in old if b not in removed and b!=oldconst],new);require(r['constructs']==5987 and r['functions']==2009,'original whole conservation');r['nonallocation_occurrence_mapping']=rows;r['five_removed_allocations']=[b.split('\n',1)[0] for b in removed];expected=read(C/'original-allocation-transport.json')
    require(r['mapping']==expected['allocation_mapping'],'independently derived mapping differs from candidate')
    save('transport-'+which+'.json',r);print(json.dumps({k:v for k,v in r.items() if not isinstance(v,(list,dict))}))
def main():
    mode=sys.argv[1]
    if mode=='census':census_review(int(sys.argv[2]))
    elif mode=='transport':transport_review(sys.argv[2])
    else:raise AssertionError('unknown owned review mode')
if __name__=='__main__':main()
