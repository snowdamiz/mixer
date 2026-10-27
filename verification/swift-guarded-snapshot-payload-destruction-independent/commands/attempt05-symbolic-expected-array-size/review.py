"""Independent, read-only source146 payload ownership and arithmetic controls.

No compiler or product is executed. The only imported candidate program is its
pure arithmetic model; source declarations are independently tokenized below.
"""
from __future__ import annotations
import collections
import copy
import gzip
import hashlib
import json
from pathlib import Path
import random
import re
import struct
import sys

sys.dont_write_bytecode = True
D = Path(__file__).resolve().parent
R = D.parents[1]
V = R / 'verification'
P = V / 'swift-guarded-snapshot-payload-destruction-cost'
L = V / 'swift-guarded-snapshot-source146-leaf-payload-layouts'
C = V / 'swift-guarded-snapshot-host-composition'
B = V / 'swift-guarded-snapshot-funding-implementation/source/vm'
F = V / 'swift-guarded-snapshot-loader-work-source146'
TREE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST = '027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
U64 = 2**64 - 1
checks, inputs = [], {}


def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(x): return json.dumps(x, sort_keys=True, separators=(',', ':')).encode()
def require(name, condition):
    if not condition: raise AssertionError(name)
    checks.append(name)
def raw(path):
    b = path.read_bytes()
    inputs[str(path.relative_to(R))] = dict(bytes=len(b), sha256=sha(b))
    return b
def read(path): return json.loads(raw(path))
def identity(path, b): return dict(path=path, bytes=len(b), sha256=sha(b))
def write(name, value): (D / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def packet(path, digest, members, total):
    data = raw(path / 'seal.json')
    require('seal:' + path.name, sha(data) == digest)
    seal = json.loads(data)
    require('member-count:' + path.name, len(seal['members']) == members)
    seen = set()
    for m in seal['members']:
        q = Path(m['path'])
        require('member-safe:' + path.name + '/' + str(q),
                not q.is_absolute() and '..' not in q.parts and str(q) not in seen)
        seen.add(str(q))
        require('member-bytes:' + path.name + '/' + str(q), identity(str(q), raw(path/q)) == m)
    require('member-total:' + path.name, sum(m['bytes'] for m in seal['members']) == total)


def tokens(text):
    """Small lexical scanner, including nested comments and quoted literals.

    This is deliberately distinct from the producer's comment-removal regex.
    It is only used on the exact hash-bound declarations, never arbitrary OTA.
    """
    out, i = [], 0
    while i < len(text):
        c = text[i]
        if c.isspace(): i += 1; continue
        if text.startswith('//', i):
            j = text.find('\n', i); i = len(text) if j == -1 else j+1; continue
        if text.startswith('/*', i):
            depth, i = 1, i+2
            while depth and i < len(text):
                if text.startswith('/*', i): depth += 1; i += 2
                elif text.startswith('*/', i): depth -= 1; i += 2
                else: i += 1
            if depth: raise ValueError('unclosed-comment')
            continue
        start = i
        # Source raw/ordinary strings must not introduce fake declarations.
        if c in ('r', 'b') and i+1 < len(text):
            j = i+1
            if c == 'b' and text[j:j+1] == 'r': j += 1
            while text[j:j+1] == '#': j += 1
            if text[j:j+1] == '"':
                hashes = text[i:j].count('#'); end = text.find('"'+'#'*hashes, j+1)
                if end == -1: raise ValueError('unclosed-raw-string')
                i = end+1+hashes; out.append((text[start:i], start, i)); continue
        if c == '"' or (c == "'" and i+2 < len(text) and (text[i+2] == "'" or text[i+1] == '\\')):
            quote, i = c, i+1
            while i < len(text):
                if text[i] == '\\': i += 2
                elif text[i] == quote: i += 1; break
                else: i += 1
            out.append((text[start:i], start, i)); continue
        if c.isalpha() or c == '_' or (c == "'" and i+1 < len(text)):
            i += 1
            while i < len(text) and (text[i].isalnum() or text[i] == '_'): i += 1
        elif c.isdigit():
            i += 1
            while i < len(text) and (text[i].isalnum() or text[i] == '_'): i += 1
        elif text.startswith('::', i): i += 2
        else: i += 1
        out.append((text[start:i], start, i))
    return out


def split(ts, delimiter=','):
    result, start, stack = [], 0, []
    pairs = {'(':')', '[':']', '{':'}', '<':'>'}
    for i, t in enumerate(ts):
        s = t[0]
        if s in pairs: stack.append(pairs[s])
        elif s in (')',']','}','>'):
            if not stack or stack.pop() != s: raise ValueError('unbalanced-tokens')
        elif s == delimiter and not stack:
            if i > start: result.append(ts[start:i])
            start = i+1
    if stack: raise ValueError('unclosed-tokens')
    if start < len(ts): result.append(ts[start:])
    return result


def matching(ts, i):
    pairs = {'(':')','[':']','{':'}','<':'>'}
    stack = [pairs[ts[i][0]]]
    j = i+1
    while stack:
        s = ts[j][0]
        if s in pairs: stack.append(pairs[s])
        elif s in (')',']','}','>'):
            if stack.pop() != s: raise ValueError('mismatch')
        j += 1
    return j


def trim_attributes(ts):
    test = False
    while ts and ts[0][0] == '#':
        j = matching(ts, 1)
        test |= ''.join(t[0] for t in ts[:j]) == '#[cfg(test)]'
        ts = ts[j:]
    if ts and ts[0][0] == 'pub':
        ts = ts[1:]
        if ts and ts[0][0] == '(': ts = ts[matching(ts,0):]
    return ts, test


def declared_types(source, name, path):
    ts = tokens(source)
    matches = []
    for i in range(len(ts)-2):
        if ts[i][0] not in ('struct','enum') or ts[i+1][0] != name: continue
        j = i+2
        if ts[j][0] == '<': j = matching(ts, j)
        if ts[j][0] not in ('{','('): continue
        end = matching(ts,j)
        kind = ts[i][0]
        body, delim = ts[j+1:end-1], ts[j][0]
        def fields(part, named):
            result = []
            for field in split(part):
                field, disabled = trim_attributes(field)
                if disabled: continue
                if named:
                    if len(field) < 3 or field[1][0] != ':': raise ValueError('field-syntax:' + name)
                    field = field[2:]
                result.append(''.join(t[0] for t in field))
            return result
        variants = []
        if kind == 'enum':
            for variant in split(body):
                variant, disabled = trim_attributes(variant)
                if disabled: continue
                payload = []
                if len(variant)>1 and variant[1][0] in ('{','('):
                    payload=fields(variant[2:matching(variant,1)-1], variant[1][0]=='{')
                variants.append(dict(name=variant[0][0],fields=payload))
        else: variants = [dict(name=None, fields=fields(body,delim=='{'))]
        matches.append(dict(name=name, path=path, kind=kind, variants=variants,
                            start_line=source.count('\n',0,ts[i][1])+1,
                            raw_source=source[ts[i][1]:ts[end-1][2]]))
    if len(matches)!=1: raise ValueError('ambiguous-source-declaration:' + name)
    return matches[0]


def ast(text, context=''):
    ts=tokens(text)
    v=[t[0] for t in ts]
    if not v: raise ValueError('empty-type')
    if v[0] in ('&','*'): return ('borrow',)
    if v[0]=='[':
        chunks=split(ts[1:-1],';')
        if len(chunks)==1: return ('slice',ast(''.join(t[0] for t in chunks[0]),context))
        if len(chunks)!=2: raise ValueError('unbound-array')
        n=int(''.join(t[0] for t in chunks[1]).replace('_',''))
        if n<0 or n>8192: raise ValueError('array-range')
        return ('array',n,ast(''.join(t[0] for t in chunks[0]),context))
    if v[0]=='(':
        return ('tuple',tuple(ast(''.join(t[0] for t in c),context) for c in split(ts[1:-1])))
    left=v.index('<') if '<' in v else len(v)
    path=''.join(v[:left]); name=path.split('::')[-1]
    args=[] if left==len(v) else [ast(''.join(t[0] for t in c),context) for c in split(ts[left+1:-1]) if not c[0][0].startswith("'")]
    if name=='Span': name='MetaSpan' if context=='src/experimental/metadata.rs' else 'WasiSpan'
    if name=='Resource' and context=='src/experimental/account.rs': name='ValidatorResource'
    name={'SwiftMetadata':'Metadata','AError':'SnapshotAdmissionErrorV1','Stop':'SnapshotStopV1'}.get(name,name)
    if path.endswith('SwiftMetadata'): args=[('named','SwiftDeclaration',())]
    return ('named',name,tuple(args))


def spelling(node):
    if node[0]=='named': return node[1]+('<'+','.join(spelling(a) for a in node[2])+'>' if node[2] else '')
    if node[0]=='slice': return '['+spelling(node[1])+']'
    return repr(node)


class Algebra:
    def __init__(self, definitions): self.defs=definitions; self.seen=set()
    def value(self,node,active=(),bind=None):
        if bind:
            def substitute(n):
                if n[0]=='named':
                    if n[1] in bind: return bind[n[1]]
                    return ('named',n[1],tuple(substitute(a) for a in n[2]))
                if n[0]=='array': return ('array',n[1],substitute(n[2]))
                if n[0]=='slice': return ('slice',substitute(n[1]))
                if n[0]=='tuple': return ('tuple',tuple(substitute(a) for a in n[1]))
                return n
            node=substitute(node)
        kind=node[0]
        if kind=='borrow': return (1,collections.Counter())
        def product(values):
            count=1; resources=collections.Counter()
            for n,r in values: count+=n; resources.update(r)
            return count,resources
        def alternative(values):
            count=1; resources=collections.Counter()
            for n,r in values:
                count=max(count,1+n)
                resources |= r
            return count,resources
        if kind=='tuple': return product(self.value(x,active,bind) for x in node[1])
        if kind=='array':
            n,r=self.value(node[2],active,bind)
            return 1+node[1]*n,collections.Counter({k:v*node[1] for k,v in r.items()})
        _,name,args=node
        if bind and name in bind: return self.value(bind[name],active)
        if name in ('File','Error','Box','Vec','Arc'):
            if len(args)!=(1 if name in ('Box','Vec','Arc') else 0): raise ValueError('resource-arity')
            return 1,collections.Counter({spelling(node):1})
        if name in ('Option','Result'):
            if len(args)!=(1 if name=='Option' else 2): raise ValueError('variant-arity')
            arms=[()] + [(args[0],)] if name=='Option' else [(a,) for a in args]
            return alternative(product(self.value(a,active,bind) for a in arm) for arm in arms)
        if name in ('u8','u16','u32','u64','u128','usize','i8','i16','i32','i64','i128','isize','f32','f64','bool','char','!','Instant','Duration'):
            return 1,collections.Counter()
        if name in active: raise ValueError('recursive-ownership')
        d=self.defs[name]; self.seen.add(name)
        binding={}
        if name=='Metadata':
            if args!=(('named','SwiftDeclaration',()),): raise ValueError('specialization')
            binding={'D':args[0]}
        elif name=='Buffer':
            if len(args)!=1: raise ValueError('specialization')
            binding={'T':args[0]}
        elif args: raise ValueError('unexpected-owned-type-argument')
        values=[product(self.value(ast(t,d['path']),active+(name,),binding) for t in arm['fields']) for arm in d['variants']]
        return values[0] if d['kind']=='struct' else alternative(values)


def unpack_counted(data):
    offset=0
    def number():
        nonlocal offset
        n=struct.unpack_from('<Q',data,offset)[0]; offset+=8; return n
    out=[]
    for _ in range(number()):
        n=number(); out.append(data[offset:offset+n].decode()); offset+=n
    require('counted-preimage-no-tail',offset==len(data))
    return out


def layouts(source):
    selection, result=read(L/'selection.json'),read(L/'results.json')
    closure, receipt, binding=read(L/'compiled-manifest.json'),read(L/'compiler-receipt.json'),read(L/'binding.json')
    require('layout-source-tree',result['source_tree_sha256']==binding['source_tree_sha256']==TREE)
    require('layout-manifest-source-tree',closure['source_manifest']['members']==read(C/'source-manifest.json')['members'])
    require('layout-target',result['target']==binding['target']=='aarch64-apple-darwin')
    require('expected-query-exit-not-metadata',receipt['exit_code']==1 and not receipt['timed_out'] and not result['metadata_produced'] and not result['product_executed'])
    require('layout-compiler-reaped',receipt['direct_child_waited'] and receipt['owned_group_absent'])
    args=unpack_counted(raw(L/'argv.bin'))
    require('layout-exact-argv',args==receipt['argv'])
    require('layout-not-test-cfg','--test' not in args and '--cfg' in args and 'mixer_bootstrap_one_fixture_v1' in args)
    env=unpack_counted(raw(L/'environment.bin'))
    envdict=dict(x.split('=',1) for x in env)
    require('layout-environment-preimage',all(receipt['environment'][k]==v for k,v in envdict.items()) and len(envdict)==len(env))
    keys=['MIXER_LOADER_MANIFEST_SHA256','MIXER_LOADER_COMMAND_SHA256','MIXER_LOADER_COMPILE_ENV_SHA256','MIXER_LOADER_COMPILER_SHA256','MIXER_LOADER_COMPILER_VERSION_SHA256']
    digests=[sha(raw(L/'compiled-manifest.json')),sha(raw(L/'argv.bin')),sha(raw(L/'environment.bin')),closure['compiler_sha256'],sha(raw(L/'compiler-version.stdout'))]
    for key,digest in zip(keys,digests): require('layout-key:'+key,binding['compile_identity_keys'][key]==receipt['environment'][key]==digest)
    require('layout-exact-rust-version',raw(L/'compiler-version.stdout').startswith(b'rustc 1.99.0 (b940084d7 2026-09-28)'))
    fragment=raw(L/'layout-queries.inc.rs')
    require('layout-fragment-digest',sha(fragment)==closure['query_fragment_sha256'])
    require('layout-query-source-identity',sha(raw(L/'query.py'))==closure['script_sha256'] and sha(raw(L/'selection.json'))==closure['selection_sha256'])
    expected=[]
    for path,data in source.items(): expected.append(identity(path,data+(fragment if path==selection['append_to'] else b'')))
    expected.sort(key=lambda m:Path(m['path']))
    require('layout-all-compiled-members',expected==closure['compiled_source_members'])
    require('layout-compiled-tree',sha(canonical(expected))==closure['compiled_tree_sha256'])
    require('layout-append-original-identity',identity(selection['append_to'],source[selection['append_to']])==dict(path=selection['append_to'],bytes=selection['append_original_bytes'],sha256=selection['append_original_sha256']))
    for name,ident in receipt['outputs'].items(): require('layout-output:'+name,identity(name,raw(L/('compiler.'+name)))==dict(path=name,**ident))
    # Independent parser obtains value from structured primary label and type
    # from primary source text; rendered diagnostics are not trusted as an index.
    observed={}
    for line in raw(L/'compiler.stderr').decode().splitlines():
        msg=json.loads(line)
        if msg['level']!='error': continue
        if msg.get('code') is None: continue
        require('layout-only-E0308',msg['level']=='error' and msg['code']['code']=='E0308')
        spans=[s for s in msg['spans'] if s['is_primary']]
        require('layout-one-primary',len(spans)==1)
        primary=spans[0]
        require('layout-primary-source',primary['file_name'].endswith('/vm/'+selection['append_to']))
        source_line=''.join(p['text'] for s in msg['spans'] for p in s['text'])
        # The queried const line also occurs as the secondary span.
        tag=re.findall(r'const LP_(SIZE|ALIGN)_(\d+):',source_line)
        require('layout-one-query-tag',len(set(tag))==1)
        kind,index=tag[0]; index=int(index)
        declaration=next(s for s in fragment.decode().splitlines() if s.startswith('const LP_'+kind+'_'+str(index)+':'))
        require('layout-raw-source-line',declaration in source_line)
        label=primary['label']
        prefix='expected an array with a size of '
        require('layout-primary-value-label',label.startswith(prefix) and ', found one with a size of ' in label)
        expected_size,actual=label[len(prefix):].split(', found one with a size of ')
        require('layout-query-expected-max',expected_size=='usize::MAX')
        key=index,kind.lower()
        require('layout-unique-diagnostic',key not in observed)
        observed[key]=int(actual)
    require('layout-complete-55-pairs',set(observed)=={(i,k) for i in range(55) for k in ('size','align')})
    require('layout-roster-count',len(selection['queries'])==len(result['queries'])==55)
    table={}
    for i,row in enumerate(result['queries']):
        require('layout-roster:'+str(i),row['concrete']==selection['queries'][i]['concrete'])
        require('layout-values:'+str(i),row['size']==observed[i,'size'] and row['alignment']==observed[i,'align'])
        require('layout-valid-alignment:'+str(i),row['alignment']>0 and row['alignment']&(row['alignment']-1)==0 and row['size']%row['alignment']==0)
        table[spelling(ast(row['concrete']))]=dict(size=row['size'],alignment=row['alignment'],query_index=i,concrete=row['concrete'])
    cleanup=read(L/'cleanup.json')
    require('layout-cleanup-complete',cleanup['completed'] and cleanup['owned_scratch_removed'] and cleanup['command_children_waited_and_groups_absent'] and cleanup['removed_files']==146 and not (L/'owned-work').exists())
    return table


def oracle(row,cuts,extent):
    def valid(n,positive=False):
        if type(n) is not int or n<0 or n>U64 or (positive and n==0): raise ValueError('bad-number')
        return n
    e=valid(row['inline_bytes'] if row['inline_bytes'] is not None else extent,True)
    total=valid(row['structural_occurrence_allowance'])*(1+e)
    if set(cuts)!=set(row['resource_frontiers']): raise ValueError('cut-domain')
    for name,m in row['resource_frontiers'].items():
        c=cuts[name]; child=row.get('dynamic_resource_elements',{}).get(name)
        wanted={'interface_work','native_resource_backing'} | ({'max_live_elements','element_inline_bytes','element_cuts'} if child else set())
        if type(c) is not dict or set(c)!=wanted: raise ValueError('cut-schema')
        amount=valid(c['interface_work'],True)+valid(c['native_resource_backing'],True)
        if child: amount+=valid(c['max_live_elements'],True)*oracle(child,c['element_cuts'],valid(c['element_inline_bytes'],True))
        total+=valid(m,True)*amount
    return valid(total,True)


def arithmetic(rows,table):
    # Executing only this tiny, inspected arithmetic model is intentional; no
    # candidate scanner, runner, compiler, fixture or product is imported.
    model={}; exec(compile(raw(P/'model.py'),str(P/'model.py'),'exec'),model)
    evaluate=model['evaluate_row']; entry=[r for r in rows if r['type'] in ['File','Option<File>','ReturnedLoaderFilesV1','SetupOutcomeV1','SelectedValidatedProfileV1','LoaderFailureV1','Cancellation']]
    def cuts_for(row,rng=None):
        rng=rng or random.Random(0)
        cuts={name:dict(interface_work=rng.randrange(1,100000),native_resource_backing=rng.randrange(1,100000)) for name in row['resource_frontiers']}
        for name,child in row.get('dynamic_resource_elements',{}).items():
            cuts[name].update(max_live_elements=rng.randrange(1,100),element_inline_bytes=136,element_cuts=cuts_for(child,rng))
        return cuts
    def refuse(label,fn):
        try: fn()
        except (ValueError,TypeError,KeyError): checks.append(label)
        else: raise AssertionError('accepted-negative:'+label)
    rng=random.Random(14620261027)
    for row in rows:
        extent=table[row['type']]['size'] if row['inline_bytes'] is None else row['inline_bytes']
        for i in range(64):
            cut=cuts_for(row,rng)
            require('oracle:'+row['type']+':'+str(i),evaluate(row,cut,extent)==oracle(row,cut,extent))
        cut=cuts_for(row)
        for name in cut:
            changed=copy.deepcopy(cut); del changed[name]
            refuse('missing-frontier:'+row['type']+':'+name,lambda:evaluate(row,changed,extent))
            for field in ['interface_work','native_resource_backing']:
                for bad in [None,0,-1,True,1.5,'1',U64+1]:
                    changed=copy.deepcopy(cut); changed[name][field]=bad
                    refuse('bad-resource:'+row['type']+':'+name+':'+field+':'+repr(bad),lambda:evaluate(row,changed,extent))
            changed=copy.deepcopy(cut);changed[name]['unknown']=1
            refuse('unknown-field:'+row['type']+':'+name,lambda:evaluate(row,changed,extent))
        changed=copy.deepcopy(cut);changed['UnknownFrontier']={'interface_work':1,'native_resource_backing':1}
        refuse('unknown-frontier:'+row['type'],lambda:evaluate(row,changed,extent))
        huge=copy.deepcopy(row);huge['structural_occurrence_allowance']=U64
        refuse('overflow-inline:'+row['type'],lambda:evaluate(huge,cut,extent))
        for name,child in row.get('dynamic_resource_elements',{}).items():
            for field in ['max_live_elements','element_inline_bytes','element_cuts']:
                changed=copy.deepcopy(cut);del changed[name][field]
                refuse('missing-slot-field:'+row['type']+':'+field,lambda:evaluate(row,changed,extent))
            for field in ['max_live_elements','element_inline_bytes']:
                for bad in [None,0,-1,True,1.5,'1',U64+1]:
                    changed=copy.deepcopy(cut);changed[name][field]=bad
                    refuse('bad-slot-field:'+row['type']+':'+field+':'+repr(bad),lambda:evaluate(row,changed,extent))
            for nested in child['resource_frontiers']:
                changed=copy.deepcopy(cut);del changed[name]['element_cuts'][nested]
                refuse('missing-slot-nested:'+row['type']+':'+nested,lambda:evaluate(row,changed,extent))
            changed=copy.deepcopy(cut);changed[name]['max_live_elements']=U64
            refuse('slot-overflow:'+row['type'],lambda:evaluate(row,changed,extent))
            changed=copy.deepcopy(cut);changed[name]['max_live_elements']+=1
            delta=oracle(child,cut[name]['element_cuts'],136)
            require('slot-one-element-delta:'+row['type'],evaluate(row,changed,extent)-evaluate(row,cut,extent)==row['resource_frontiers'][name]*delta)
    union=set().union(*(set(r['resource_frontiers']) for r in entry))
    for i in range(128):
        cuts={k:dict(interface_work=rng.randrange(1,100000),native_resource_backing=rng.randrange(1,100000)) for k in union}
        values=[oracle(r,{k:cuts[k] for k in r['resource_frontiers']},r['inline_bytes']) for r in entry]
        maximum=model['per_visit_maximum'](entry,cuts)
        require('per-visit-maximum:'+str(i),maximum==max(values))
        require('53-applied-once:'+str(i),53*maximum==sum([maximum]*53) and maximum!=53*maximum)
    returned=next(r for r in rows if r['type']=='OwnedFixtureOutcomeV1')
    cuts={k:dict(interface_work=3,native_resource_backing=5) for k in returned['resource_frontiers']}
    require('returned-formula',model['returned_payload']([returned],cuts)==45195489+6*8+8+8)
    for bad in [None,0,-1,True,1.5,'1',U64+1]:
        refuse('P5-carrier:'+repr(bad),lambda:model['compose_p5'](bad,1))
        refuse('P5-payload:'+repr(bad),lambda:model['compose_p5'](1,bad))
    refuse('P5-overflow',lambda:model['compose_p5'](U64,1))
    require('P5-separate-sum',model['compose_p5'](71,83)==154)
    # Max-of-enum components is conservative even if different alternatives
    # maximize different resources. Mutually exclusive arms need not co-occur.
    for _ in range(256):
        arms=[collections.Counter({k:rng.randrange(7) for k in ['File','Error','Arc<AtomicBool>']}) for _ in range(4)]
        maxima=collections.Counter()
        for arm in arms: maxima|=arm
        prices={k:rng.randrange(1,10000) for k in maxima}
        require('enum-maxima-dominates',all(sum(a[k]*prices[k] for k in maxima)<=sum(maxima[k]*prices[k] for k in maxima) for a in arms))


def main():
    packet(P,'8378e706ba0d262b935114fca8cc2d1a995286f8eedce4bfa524ac5c8c6ce72f',75,636514)
    packet(L,'f2021a5fa0be89481bc02bdb811ec6ac2fb5e4112900a9f1e831135070be2952',22,603977)
    for name,digest in [('guarded-snapshot-payload-destruction-cost-independent-release.json','0a13acc9f94adb8d05968c3255d30598f9587f27678b12bba684b9e36eff51fa'),('guarded-snapshot-source146-leaf-payload-layout-release.json','5a66c532917e723285c8d30ce9e40b2fc5d97012c9c8469349ab3cdbc87c6834')]:
        require('root-release:'+name,sha(raw(V/'swift-semantic-adapter-root-review'/name))==digest)
    manifest=read(C/'source-manifest.json')
    require('source146-manifest',len(manifest['members'])==146 and sha(canonical(manifest['members']))==TREE)
    sources={}
    for member in manifest['members']:
        path=member['path']; overlay=C/'overlay/vm'/path
        data=raw(overlay if overlay.is_file() else B/path)
        require('source146:'+path,identity(path,data)==member)
        sources[path]=data
    host=read(C/'host-support-manifest.json')
    require('host11-manifest',len(host['members'])==11 and sha(canonical(host['members']))==HOST)
    for member in host['members']:
        require('host11:'+member['path'],identity(member['path'],raw(V/'swift-real-profile-loader-binding/host'/member['path']))==member)
    inv=read(P/'inventory.json'); definitions={}; declaration_evidence=[]
    for d in inv['declarations']:
        # All accepted scalar diagnostic definitions are re-read from the exact
        # source, in addition to newly introduced payload owners.
        declared_name={'MetaSpan':'Span','WasiSpan':'Span','ValidatorResource':'Resource'}.get(d['name'],d['name'])
        actual=declared_types(sources[d['path']].decode(),declared_name,d['path'])
        actual['name']=d['name']
        expected=[dict(name=None,fields=d['fields'])] if d['kind']=='struct' else d['variants']
        if d['name']=='PrepaidOwnedV1':
            require('P0-source-generic-payload',actual['variants'][0]['fields']==['Option<T>',"Option<ReservationV1<'a>>"])
            require('P0-candidate-specialized-separately','OwnedFixtureOutcomeV1' in expected[0]['fields'][0])
        else:
            require('declaration-kind:'+d['name'],actual['kind']==d['kind'])
            require('declaration-arm-names:'+d['name'],[a['name'] for a in actual['variants']]==[a['name'] for a in expected])
            require('declaration-owned-fields:'+d['name'],[[ast(f,d['path']) for f in a['fields']] for a in actual['variants']]==[[ast(f,d['path']) for f in a['fields']] for a in expected])
        definitions[d['name']]=actual
        declaration_evidence.append(actual)
    algebra=Algebra(definitions)
    row_evidence=[]
    for row in inv['rows']:
        count,resources=algebra.value(ast(row['type']))
        require('source-graph-count:'+row['type'],count==row['structural_occurrence_allowance'])
        require('source-graph-frontiers:'+row['type'],dict(resources)==row['resource_frontiers'])
        row_evidence.append(dict(type=row['type'],count=count,resource_frontiers=dict(resources)))
    require('complete20-roots',len(inv['rows'])==20 and len({r['type'] for r in inv['rows']})==20)
    for name,value in inv['dynamic_element_destructor_schemas'].items():
        count,resources=algebra.value(ast(name))
        require('element-schema:'+name,count==value['nodes'] and dict(resources)==value['resources'])
    require('SwiftSlot-nested-frontiers',algebra.value(ast('SwiftSlot'))==(19,collections.Counter({'Vec<Type>':1,'Vec<DecodedInstruction>':1,'Vec<u32>':1})))
    require('selected8vector-and-box-frontiers',dict(algebra.value(ast('SelectedValidatedProfileV1'))[1])=={'Box<[u8]>':1,'Vec<Signature>':1,'Vec<Type>':1,'Vec<Import>':1,'Vec<Function>':1,'Vec<Global>':1,'Vec<Export>':1,'Vec<Segment>':2})
    returned=algebra.value(ast('OwnedFixtureOutcomeV1'))
    require('returned-resource-maxima',returned==(3321,collections.Counter({'File':6,'Error':1,'Arc<AtomicBool>':1})))
    require('returned-finite-allowance',3321*(13608+1)==45195489)
    table=layouts(sources)
    missing=[r['type'] for r in inv['rows'] if r['inline_bytes'] is None]+['SwiftSlot']
    require('all13-layout-requests',len(missing)==13 and set(missing)==set(read(L/'selection.json')['additional_payload_type_requests']))
    closures=[]
    for typ in missing:
        layout=table[typ]
        count,_=algebra.value(ast(typ))
        closures.append(dict(type=typ,**layout,structural_occurrence_allowance=count,finite_structural_native_allowance=count*(1+layout['size'])))
        require('layout-exact-concrete:'+typ,layout['alignment']==8 and layout['size']>0)
    require('SwiftSlot-exact136',table['SwiftSlot']['size']==136)
    archive=raw(F/'whole-source146.mir.gz')
    require('full-MIR-archive',sha(archive)=='03b5265c5ae85b3a444f847f1b65af8f31e9fee7697845d6f9699ddf2d8e87e7' and len(archive)==3595856)
    mir=gzip.decompress(archive)
    require('full-MIR-raw',sha(mir)=='e54c8b0f2b5a69ad8c34c0b6a1454dcc8b3b04338c14f11048b44e10a24301a2' and len(mir)==76655228)
    chunks=mir.decode().split('\nfn '); functions={}
    drop_headers=[]
    for chunk in chunks:
        chunk=chunk if chunk.startswith('fn ') else 'fn '+chunk
        header=chunk.splitlines()[0]
        if '::drop(' in header: drop_headers.append(header)
        for name in ['setup_files_once_v1','run_prepaid_fixture_v1','run_one_loaded_fixture_v1','invoke_loaded_leaf_once_v1']:
            if chunk.startswith('fn '+name+'('):functions[name]=chunk
    require('only3authored-compiled-Drop',len(drop_headers)==3 and drop_headers==inv['observed_production_authored_drop_headers'])
    require('no-session-Drop-owners',not {'SessionLease','Reservation'} & algebra.seen)
    p0=next(c for c in chunks if 'PrepaidOwnedV1' in c.splitlines()[0] and '::drop(' in c.splitlines()[0])
    require('P0-owned-taken-before-drop',p0.index('Option::<T>::take')<p0.index('std::mem::drop::<T>'))
    drop_evidence=[]
    actual_types=set()
    for name,body in functions.items():
        sites=[line.split('//',1)[0].strip() for line in body.splitlines() if line.strip().startswith('drop(')]
        require('MIR-drop-sites:'+name,sites==inv['during_entry_drop_sites'][name])
        locals={}
        for line in body.splitlines():
            s=line.strip().split('//',1)[0]
            m=re.match(r'let (?:mut )?(_\d+): (.+);$',s)
            if m: locals[m[1]]=m[2]
        for site in sites:
            if name not in ['setup_files_once_v1','run_prepaid_fixture_v1']: continue
            subject=site[5:site.index(') ->')]
            if ': ' in subject: typ=subject.rsplit(': ',1)[1].rstrip(')')
            else:
                key=re.match(r'_\d+',subject)[0];typ=locals[key]
                if '[' in subject:
                    a=ast(typ);require('MIR-indexed-drop-array',a[0]=='array');typ=spelling(a[2])
            normalized=spelling(ast(typ));actual_types.add(normalized)
            drop_evidence.append(dict(function=name,statement=site,concrete_payload=typ,normalized=normalized))
    require('actual7entry-types',actual_types==set(inv['entry_per_visit_types']))
    require('53-source-visits',len(inv['during_entry_drop_sites']['setup_files_once_v1'])*6+len(inv['during_entry_drop_sites']['run_prepaid_fixture_v1'])==53)
    for d in definitions.values():
        if d['name'] in algebra.seen:
            require('no-hidden-Resource-owner:'+d['name'],all('ManuallyDrop' not in f and 'UnsafeCell' not in f and 'dyn' not in f for a in d['variants'] for f in a['fields']))
    # The Error frontier deliberately does not traverse unknown dynamic errors.
    # All Box/Vec/Arc capacities, deallocation requests and actual cleanup stay
    # mandatory cuts. Inline layout substitution cannot establish any of them.
    arithmetic(inv['rows'],table)
    write('source-declarations.json',dict(source_tree_sha256=TREE,declarations=declaration_evidence))
    write('ownership-review.json',dict(source_tree_sha256=TREE,rows=row_evidence,drop_sites=drop_evidence,authored_production_drop_headers=drop_headers,actual_entry_payload_types=sorted(actual_types),P0_separate=True,P5_carrier_separate=True))
    write('layout-substitution.json',dict(source_tree_sha256=TREE,compiler='rustc1.99.0-b940084d7',target='aarch64-apple-darwin',source14613observations=closures,all13_symbolic_extents_closed=True,actual_resource_backing_or_destructor_work_closed=False))
    write('controls.json',dict(checks=len(checks),labels=checks,seed=14620261027,producer_scanner_executed=False,pure_producer_model_executed=True,product_executed=False))
    write('input-custody.json',dict(schema=1,files=inputs,source_tree_sha256=TREE,host_tree_sha256=HOST))
    write('results.json',dict(schema=1,status='bounded-conditional-payload-interface-accepted',checks=len(checks),source_tree_sha256=TREE,host_tree_sha256=HOST,roots=20,frontiers=18,layout_observations_closed=13,returned_finite_allowance=45195489,actual_resource_cuts_selected=False,whole_host_accepted=False,native_runtime='paused',GA_verified=False))
    print(json.dumps(dict(status='passed',checks=len(checks),typed_roots=20,closed_payload_layouts=13,resource_cuts='pending',product_execution=False),sort_keys=True))


if __name__=='__main__': main()
