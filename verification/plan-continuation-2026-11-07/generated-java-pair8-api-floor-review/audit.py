#!/usr/bin/env python3
"""Read-only classfile/DEX/API-table audit. Writes only beside this script; no subprocesses."""
import collections, datetime, hashlib, json, pathlib, re, struct, sys, xml.etree.ElementTree as ET, zipfile, zlib

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[2]
RUN = pathlib.Path('/tmp/mixer-20261107-generated-java-pair8-03')
SDK = pathlib.Path('/opt/homebrew/share/android-commandlinetools/platforms/android-37.0')
def sha(b): return hashlib.sha256(b).hexdigest()
def digest(p):
    b=p.read_bytes(); return {'bytes':len(b),'sha256':sha(b)}
def dump(name,obj): (OUT/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def canonical(obj): return sha(json.dumps(obj,sort_keys=True,separators=(',',':')).encode())

class Reader:
    def __init__(self,b): self.b=b;self.p=0
    def read(self,n):
        v=self.b[self.p:self.p+n];self.p+=n;assert len(v)==n;return v
    def u1(self): return self.read(1)[0]
    def u2(self): return int.from_bytes(self.read(2),'big')
    def u4(self): return int.from_bytes(self.read(4),'big')

def classfile(b):
    r=Reader(b);assert r.u4()==0xcafebabe
    minor,major=r.u2(),r.u2();n=r.u2();cp=[None]*n;i=1
    while i<n:
        t=r.u1()
        if t==1: v=r.read(r.u2()).decode('utf-8',errors='replace')
        elif t in (3,4): v=r.read(4).hex()
        elif t in (5,6): v=r.read(8).hex()
        elif t in (7,8,16,19,20): v=r.u2()
        elif t in (9,10,11,12,17,18): v=(r.u2(),r.u2())
        elif t==15: v=(r.u1(),r.u2())
        else: raise ValueError(('cp',t))
        cp[i]=(t,v);i+=2 if t in (5,6) else 1
    def utf(i): return cp[i][1]
    def cls(i): return utf(cp[i][1]) if i else None
    def ref(i):
        t,(c,nt)=cp[i];name,desc=cp[nt][1]
        return (cls(c),utf(name),utf(desc),'field' if t==9 else 'method')
    access=r.u2();name=cls(r.u2());sup=cls(r.u2());interfaces=[cls(r.u2()) for _ in range(r.u2())]
    def attrs(q): return {utf(q.u2()):q.read(q.u4()) for _ in range(q.u2())}
    fields=[];methods=[];calls=[];instructions=[]
    for kind,items in [('field',fields),('method',methods)]:
        for _ in range(r.u2()):
            flags,nm,ds=r.u2(),utf(r.u2()),utf(r.u2());a=attrs(r)
            items.append((nm,ds))
            if 'Code' not in a: continue
            cr=Reader(a['Code']);cr.u2();cr.u2();code=cr.read(cr.u4());cr.read(cr.u2()*8);ca=attrs(cr);lines=[]
            if 'LineNumberTable' in ca:
                lr=Reader(ca['LineNumberTable']);lines=[(lr.u2(),lr.u2()) for _ in range(lr.u2())]
            pc=0
            while pc<len(code):
                op=code[pc];size=1
                if op in (0x10,0x12,0xa9,0xbc) or 0x15<=op<=0x19 or 0x36<=op<=0x3a:size=2
                if op in (0x11,0x13,0x14,0x84,0xbb,0xbd,0xc0,0xc1,0xc6,0xc7) or 0x99<=op<=0xa8 or 0xb2<=op<=0xb8:size=3
                if op in (0xb9,0xba,0xc8,0xc9):size=5
                if op==0xc5:size=4
                if op==0xc4:size=6 if code[pc+1]==0x84 else 4
                if op in (0xaa,0xab):
                    q=(pc+4)&~3
                    if op==0xaa:
                        low,high=struct.unpack_from('>ii',code,q+4);size=q+12+4*(high-low+1)-pc
                    else: size=q+8+8*struct.unpack_from('>i',code,q+4)[0]-pc
                assert size>0 and pc+size<=len(code),(name,nm,pc,op,size)
                line=next((ln for start,ln in reversed(lines) if start<=pc),None)
                row={'class':name,'method':nm+ds,'pc':pc,'opcode':hex(op),'bytes':code[pc:pc+size].hex(),'line':line}
                if 0xb2<=op<=0xb9:
                    idx=int.from_bytes(code[pc+1:pc+3],'big');row['target']=ref(idx);row['cp_index']=idx;calls.append(row.copy())
                instructions.append(row);pc+=size
            assert pc==len(code)
    attributes=attrs(r);assert r.p==len(b)
    return {'name':name,'super':sup,'interfaces':interfaces,'fields':fields,'methods':methods,'major':major,
            'references':{i:ref(i) for i,c in enumerate(cp) if c and c[0] in (9,10,11)},
            'reference_kinds':{i:{9:'Fieldref',10:'Methodref',11:'InterfaceMethodref'}[c[0]] for i,c in enumerate(cp) if c and c[0] in (9,10,11)},
            'calls':calls,'instructions':instructions,'types':[cls(i) for i,c in enumerate(cp) if c and c[0]==7],
            'handles':[ref(c[1][1]) for c in cp if c and c[0]==15],
            'dynamic_count':sum(bool(c and c[0] in (17,18)) for c in cp)}

def dexfile(b):
    assert b[:4]==b'dex\n';assert int.from_bytes(b[32:36],'little')==len(b)
    assert hashlib.sha1(b[32:]).digest()==b[12:32]
    assert zlib.adler32(b[12:])==int.from_bytes(b[8:12],'little')
    def u2(p):return struct.unpack_from('<H',b,p)[0]
    def u4(p):return struct.unpack_from('<I',b,p)[0]
    def leb(p):
        value=0;shift=0
        while True:
            c=b[p];p+=1;value|=(c&127)<<shift
            if c<128:return value,p
            shift+=7;assert shift<35
    def table(p,size):return range(u4(p+4),u4(p+4)+u4(p)*size,size)
    strings=[]
    for p in table(56,4):
        _,q=leb(u4(p));end=b.index(0,q);strings.append(b[q:end].decode('utf-8',errors='replace'))
    types=[strings[u4(p)] for p in table(64,4)]
    def typename(s):return s[1:-1] if s.startswith('L') else s
    def typelist(p):return [types[u2(p+4+i*2)] for i in range(u4(p))] if p else []
    protos=['('+''.join(typelist(u4(p+8)))+')'+types[u4(p+4)] for p in table(72,12)]
    fields=[(typename(types[u2(p)]),strings[u4(p+4)],types[u2(p+2)],'field') for p in table(80,8)]
    methods=[(typename(types[u2(p)]),strings[u4(p+4)],protos[u2(p+2)],'method') for p in table(88,8)]
    defs={};calls=[];instructions=[]
    widths={i:1 for i in range(256)}
    for lo,hi in [(0x2d,0x3d),(0x44,0x6d),(0x90,0xaf),(0xd0,0xe2)]:
        for i in range(lo,hi+1):widths[i]=2
    for i in [2,5,8,0x13,0x15,0x16,0x19,0x1a,0x1c,0x1f,0x20,0x22,0x23,0x29,0xfe,0xff]:widths[i]=2
    for i in [3,6,9,0x14,0x17,0x1b,0x24,0x25,0x26,0x2a,0x2b,0x2c,0xfc,0xfd]+list(range(0x6e,0x73))+list(range(0x74,0x79)):widths[i]=3
    widths[0x18]=5;widths[0xfa]=4;widths[0xfb]=4
    for p in table(96,32):
        cl=typename(types[u4(p)]);su=u4(p+8);dc=u4(p+24)
        defs[cl]={'super':None if su==0xffffffff else typename(types[su]),'interfaces':[typename(t) for t in typelist(u4(p+12))],'fields':[],'methods':[]}
        if not dc:continue
        sizes=[]
        for _ in range(4):v,dc=leb(dc);sizes.append(v)
        for group,count in enumerate(sizes):
            idx=0
            for _ in range(count):
                diff,dc=leb(dc);idx+=diff;flags,dc=leb(dc)
                if group<2:defs[cl]['fields'].append(fields[idx][1:3]);continue
                codeoff,dc=leb(dc);method=methods[idx];defs[cl]['methods'].append(method[1:3])
                if not codeoff:continue
                n=u4(codeoff+12);units=struct.unpack_from('<'+'H'*n,b,codeoff+16);pc=0
                while pc<n:
                    word=units[pc];op=word&255;size=widths[op]
                    if op==0 and word:
                        if word==0x100:size=4+units[pc+1]*2
                        elif word==0x200:size=2+units[pc+1]*4
                        elif word==0x300:size=4+(units[pc+1]*(units[pc+2]|units[pc+3]<<16)+1)//2
                        else:raise ValueError(('payload',word))
                    assert pc+size<=n,(cl,method,pc,op,size,n)
                    row={'class':cl,'method':method[1]+method[2],'pc':pc,'opcode':hex(op),'units':[hex(x) for x in units[pc:pc+size]]}
                    if 0x52<=op<=0x6d:row['target']=fields[units[pc+1]]
                    if 0x6e<=op<=0x72 or 0x74<=op<=0x78 or op in (0xfa,0xfb):row['target']=methods[units[pc+1]]
                    if 'target' in row:calls.append(row.copy())
                    instructions.append(row);pc+=size
                assert pc==n
    return {'version':b[4:7].decode(),'types':[typename(t) for t in types],'fields':fields,'methods':methods,'definitions':defs,'calls':calls,'instructions':instructions}

api={c.attrib['name']:c for c in ET.parse(SDK/'data/api-versions.xml').getroot().findall('class')}
def api_member(owner,name,desc,kind,local,seen=()):
    if owner in seen:return None
    seen=seen+(owner,)
    if owner.startswith('['):return {'since':1,'declaration':'array','special':True}
    if owner in local:
        c=local[owner]
        if (name,desc) in [tuple(x) for x in c[kind+'s']]:return {'since':0,'declaration':owner,'local':True}
        parents=[c['super']]+c['interfaces'];floor=0
    elif owner in api:
        c=api[owner];floor=float(c.get('since','1'));key=name if kind=='field' else name+desc
        found=[x for x in c.findall(kind) if x.get('name')==key]
        if found:
            x=found[0];return {'since':max(floor,float(x.get('since',str(floor)))),'declaration':owner,'attributes':dict(x.attrib)}
        parents=[x.get('name') for x in list(c) if x.tag in ('extends','implements')]
    else:return None
    if name=='<init>':return None
    options=[api_member(p,name,desc,kind,local,seen) for p in parents if p]
    options=[x for x in options if x]
    if not options:return None
    result=dict(min(options,key=lambda x:x['since']));result['since']=max(floor,result['since']);return result

def classify(rows,local):
    modern=[];unknown=[];all_external=[]
    for row in rows:
        owner,name,desc,kind=row['target'];resolution=api_member(owner,name,desc,kind,local)
        out=dict(row,resolution=resolution)
        if not resolution:unknown.append(out)
        elif resolution['since']>28:modern.append(out)
        if not resolution or not resolution.get('local'):all_external.append(out)
    return modern,unknown,all_external

def main():
    receipt=json.loads((RUN/'receipt.json').read_text());checks=[];baseline=None;parsed_baseline=None;dex_baseline=None
    for label,expected in sorted(receipt['consumers'].items()):
        base=RUN/label;inv=json.loads((base/'member-references.json').read_text());normalized=[];classes={};rawrefs=[]
        assert digest(base/'member-references.json')==expected['member_references']['inventory']
        for rel,identity in sorted(inv['class_inputs'].items()):
            p=base/'classes'/rel;assert digest(p)==identity
            c=classfile(p.read_bytes());classes[c['name']]=c
            for idx,target in c['references'].items():rawrefs.append((rel,idx,c['reference_kinds'][idx],target))
        for row in inv['references']:
            rel=row['class_file'].split('/classes/',1)[1];idx=int(row['constant_pool_index'][1:]);c=classes[rel[:-6]];target=c['references'][idx]
            owner,name,desc,kind=target;assert row['kind']==c['reference_kinds'][idx]
            assert row['member'].replace('"','')==owner+'.'+name+':'+desc or row['member'].replace('"','')==name+':'+desc,(row,target)
            normalized.append((rel,idx,row['kind'],target))
        normalized.sort();rawrefs.sort();assert normalized==rawrefs;assert len(normalized)==4946
        h=canonical(normalized)
        if baseline is None:baseline=h;parsed_baseline=classes;dump('logical-member-references.json',normalized)
        assert h==baseline
        d=dexfile((base/'dex/classes.dex').read_bytes());dh=canonical({'fields':d['fields'],'methods':d['methods'],'defs':d['definitions'],'calls':d['calls'],'instructions':d['instructions']})
        if dex_baseline is None:dex_baseline=dh;firstdex=d
        assert dh==dex_baseline
        checks.append({'consumer':label,'member_count':len(normalized),'class_count':len(classes),'logical_members_sha256':h,'dex_logical_sha256':dh,'dex':digest(base/'dex/classes.dex'),'class_inputs_sha256':canonical(inv['class_inputs']),'dex_definitions':len(d['definitions']),'dex_calls':len(d['calls'])})
    classcalls=[row for c in parsed_baseline.values() for row in c['calls']]
    cm,cu,ce=classify(classcalls,parsed_baseline);dm,du,de=classify(firstdex['calls'],firstdex['definitions'])
    dump('classfile-modern-calls.json',cm);dump('classfile-unresolved-calls.json',cu);dump('dex-modern-calls.json',dm);dump('dex-unresolved-calls.json',du)
    dump('dex-external-calls.json',de)
    dump('dex-types-newer-than28.json',[{'type':t,'since':api[t].get('since','1')} for t in firstdex['types'] if t in api and float(api[t].get('since','1'))>28])
    focus=('NativeEnvironmentPlatformV2','NativeEnvironmentV2$Observer','NativeRenderer','NativeEditorConnectionV2')
    dump('classfile-boundary-instructions.json',[r for c in parsed_baseline.values() for r in c['instructions'] if any(c['name'].endswith(x) for x in focus)])
    dump('dex-boundary-instructions.json',[r for r in firstdex['instructions'] if any(r['class'].endswith(x) for x in focus)])
    dump('dex-class-definitions.json',firstdex['definitions'])
    ids=[{'target':t} for t in firstdex['fields']+firstdex['methods']]
    im,iu,_=classify(ids,firstdex['definitions'])
    dump('dex-member-ids-modern.json',im);dump('dex-member-ids-unresolved.json',iu)
    assert not iu
    android_class=collections.Counter(tuple(r['target']) for r in cm if not r['target'][0].startswith('java/'))
    assert android_class==collections.Counter(tuple(r['target']) for r in dm)
    java_modern=[r for r in cm if r['target'][0].startswith('java/')]
    assert not any(r['target'][0].startswith('java/') for r in dm)
    assert not any(t in firstdex['types'] for t in ['java/lang/Record','java/lang/runtime/ObjectMethods'])
    cpstats=[]
    for c in parsed_baseline.values():
        direct={r['cp_index'] for r in c['calls']};refs=set(c['references'])
        cpstats.append({'class':c['name'],'pool_members':len(refs),'directly_used_pool_members':len(direct),'not_directly_used_pool_members':len(refs-direct),'method_handles':c['handles'],'dynamic_pool_entries':c['dynamic_count']})
    dump('classfile-pool-usage.json',cpstats)
    dynamic=[r for r in firstdex['instructions'] if int(r['opcode'],16)>=0xfa]
    dump('dex-dynamic-instructions.json',dynamic)
    dynamic_calls=[r for r in firstdex['calls'] if 'reflect' in r['target'][0] or r['target'][1] in ('forName','getMethod','getDeclaredMethod','loadLibrary')]
    dump('dex-dynamic-resolution-sites.json',dynamic_calls)
    official={}
    with zipfile.ZipFile(SDK/'android.jar') as jar:
        for owner in sorted({r['resolution']['declaration'] for r in im} | {t for t in firstdex['types'] if t in api and float(api[t].get('since','1'))>28}):
            b=jar.read(owner+'.class');c=classfile(b)
            official[owner]={'sdk_class':{'bytes':len(b),'sha256':sha(b)},'super':c['super'],'interfaces':c['interfaces'],'fields':c['fields'],'methods':c['methods'],'api_xml':ET.tostring(api[owner],encoding='unicode')}
        for r in im:
            o,n,de,k=r['target'];decl=r['resolution']['declaration'];assert (n,de) in official[decl][k+'s'],r
    dump('official-sdk-declarations.json',official)
    sourcefiles=['NativeEnvironmentPlatformV2.java','NativeEnvironmentV2.java','NativeRenderer.java','NativeAppearanceViewsV2.java','NativeEditorConnectionV2.java','MixerActivity.java','NativeBridge.java']
    (OUT/'source-inputs').mkdir(exist_ok=True)
    for name in sourcefiles:
        (OUT/'source-inputs'/name).write_bytes((ROOT/'native/android/app/src/dev/mixer/android'/name).read_bytes())
    for cls,method in [('NativeEnvironmentPlatformV2','motionListener'),('NativeEnvironmentPlatformV2','contrastListener'),('NativeEnvironmentPlatformV2','highContrastListener'),('NativeEnvironmentPlatformV2','snapshot'),('NativeEnvironmentV2$Observer','<init>'),('NativeEnvironmentV2','unsupported'),('NativeRenderer','requireV2Live'),('MixerActivity','onCreate')]:
        rows=[r for r in firstdex['instructions'] if r['class'].endswith('/'+cls) and r['method'].startswith(method+'(')]
        dump('dex-'+cls.replace('$','-')+'-'+method.replace('<','').replace('>','')+'.json',rows)
    motion=[r for r in firstdex['calls'] if 'NativeEnvironmentPlatformV2$Api33' in r['class'] or 'NativeEnvironmentPlatformV2$Api33' in r['target'][0]]
    dump('dex-motion-trace.json',motion)
    examples=['dev/mixer/android/AppearanceDescriptorV2$Bundled','dev/mixer/android/AppearanceDescriptorV2$0','com/android/tools/r8/RecordTag']
    dump('dex-java-backport-examples.json',[r for r in firstdex['instructions'] if r['class'] in examples])
    sources={p:digest(ROOT/p) for p in receipt['source_inputs']}
    changed=[p for p,v in sources.items() if v!=receipt['source_inputs'][p]]
    measured_source_digest=sha(''.join(p+'\0'+v['sha256']+'\n' for p,v in sorted(sources.items())).encode())
    assert measured_source_digest==receipt['source_inputs_sha256']
    dump('source-inputs-recheck.json',{'source_inputs':sources,'mismatches':changed})
    result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'executable':sys.executable,'command':sys.argv,'script':digest(pathlib.Path(__file__)),'run_receipt':digest(RUN/'receipt.json'),'revision':receipt['revision'],'git_tree':receipt['git_tree'],'source_inputs_sha256':receipt['source_inputs_sha256'],'source_mismatches':changed,'official_api_xml':digest(SDK/'data/api-versions.xml'),'official_android_jar':digest(SDK/'android.jar'),'consumers':checks,'classfile_actual_member_instructions':len(classcalls),'classfile_modern_instructions':len(cm),'classfile_unresolved_instructions':len(cu),'dex_modern_instructions':len(dm),'dex_unresolved_instructions':len(du),'dex_version':firstdex['version'],'scope':'Pure static parsing; actual instruction presence is not path reachability or runtime loading proof.'}
    result.update({'pool_members_not_directly_used':sum(x['not_directly_used_pool_members'] for x in cpstats),'classfile_java_modern_instructions':len(java_modern),'dex_newer_java_member_ids':sum(r['target'][0].startswith('java/') for r in im),'dex_modern_unique_member_ids':len(im),'dex_dynamic_instruction_count':len(dynamic),'dex_dynamic_resolution_sites':len(dynamic_calls),'official_declarations_checked':len(official),'android_modern_instruction_multisets_match':True,'source_inputs_count':len(sources)})
    dump('audit-receipt.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('consumers','python','command')},indent=2))
    for title,rows in [('CLASS',cm),('DEX',dm),('DEX_UNKNOWN',du)]:
        groups=collections.Counter(tuple(r['target']) for r in rows)
        print(title,len(rows),'instructions',len(groups),'unique')
        for target,count in sorted(groups.items()):print(count,target)

if __name__=='__main__':main()
