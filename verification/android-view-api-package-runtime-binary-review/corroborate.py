"""Independent data-only archive, classfile and DEX report corroboration."""
import sys
import types
import hashlib
import json
import struct
import zipfile
import io
import zlib
import unicodedata
import encodings.cp437
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
EXPECTED_ZIP={'bytes':1530579,'sha256':'8e3665a6acb472f1ccbbb06eae0a582d5970fa17efdddecb28be405ed7e2c8eb'}
EXPECTED_INSPECTOR={'bytes':52483,'sha256':'7e15cfa979f19a72443436dc3f64bba2a6b88c2ed652e8956e96dd454380d83b'}
EXPECTED_SDK={'bytes':43044472,'sha256':'bf1b4387cc7ca94fc6ef684f040d9d16fbf16248e181819f020736ea2053f177'}
P='dev/mixer/android/'
V=P+'NativeAppearanceViewsV2'
R=P+'NativeRenderer'
SETTERS=('setTextCursorDrawable','setTextSelectHandle','setTextSelectHandleLeft','setTextSelectHandleRight')
LATER=set(SETTERS+('setStateDescription',))
HELPERS={V+'$Api29',V+'$Api30',R+'$Api30'}
SOURCES={s+'.java' for s in ('AppearanceDescriptorV2','AppearanceGeometryV2','AppearanceNativePathsV2','AppearanceResolverV2','AuthoredToggleInputV2','InstalledAppearanceV2','Json','NativeAppearanceViewsV2','NativeCoordinatorV2','NativeEditorConnectionV2','NativeEnvironmentPlatformV2','NativeEnvironmentV2','NativeOwnerV2','NativeRenderer','OwnerLifecycleV2','UiPacket')}

def require(v,m):
    if not v: raise ValueError(m)

def identity(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}

def read_bounded(p,n):
    require(p.is_file() and not p.is_symlink() and p.stat().st_size<=n,'bounded ordinary input '+str(p))
    b=p.read_bytes();require(len(b)<=n,'input grew');return b

def jread(b):
    require(len(b)<=67108864,'JSON bytes')
    def pairs(rows):
        out={}
        for k,v in rows:
            require(k not in out,'duplicate JSON key');out[k]=v
        return out
    out=json.loads(b,object_pairs_hook=pairs,parse_constant=lambda x:require(False,'nonfinite JSON'))
    count=0;stack=[(out,0)]
    while stack:
        v,d=stack.pop();count+=1;require(count<=200000 and d<=64,'JSON structural bound')
        if isinstance(v,dict):stack.extend((x,d+1) for x in v.values())
        elif isinstance(v,list):stack.extend((x,d+1) for x in v)
    return out

def archive_data(raw):
    require(identity(raw)==EXPECTED_ZIP,'root pinned ZIP identity')
    require(raw[:4]==b'PK\x03\x04','ZIP local start')
    z=zipfile.ZipFile(io.BytesIO(raw)); infos=z.infolist()
    require(0<len(infos)<=4096,'ZIP member count');require(not z.comment,'ZIP comment')
    names=set();aliases=set();total=0;out={};rows=[];ranges=[]
    for i in infos:
        name=i.filename;require(name==i.orig_filename and name and len(name.encode('utf-8'))<=512,'ZIP original/path bytes')
        require(not any(ord(c)<32 or ord(c)==127 for c in name) and '\\' not in name and ':' not in name,'ZIP unsafe character')
        pure=name[:-1] if name.endswith('/') else name
        parts=pure.split('/');require(len(parts)<=16 and all(p not in ('','.','..') for p in parts),'ZIP path depth/components')
        require(unicodedata.normalize('NFC',name)==name,'ZIP NFC');require(name not in names and pure.casefold() not in aliases,'ZIP duplicate/alias')
        names.add(name);aliases.add(pure.casefold())
        require(not i.flag_bits&1 and i.compress_type in (0,8),'ZIP encryption/compression')
        mode=(i.external_attr>>16)&0xffff;typ=mode&0o170000
        require(typ in (0,0o100000,0o040000) and (not name.endswith('/') or i.file_size==0),'ZIP special member')
        require((typ!=0o040000 or name.endswith('/')) and (typ!=0o100000 or not name.endswith('/')),'ZIP type/path')
        require(i.file_size<=67108864 and i.compress_size>=0 and i.file_size<=max(1,i.compress_size)*2000,'ZIP size/ratio')
        total+=i.file_size;require(total<=268435456,'ZIP expansion')
        at=i.header_offset;require(0<=at and at+30<=len(raw) and raw[at:at+4]==b'PK\x03\x04','ZIP local header')
        local=struct.unpack_from('<HHHHHIIIHH',raw,at+4);fl,method=local[1:3];nl,xl=local[-2:]
        require((fl,method)==(i.flag_bits,i.compress_type),'ZIP local flags/method')
        expected=name.encode('utf-8' if fl&0x800 else 'cp437')
        require(raw[at+30:at+30+nl]==expected,'ZIP local filename')
        start=at+30+nl+xl;end=start+i.compress_size;require(end<=z.start_dir,'ZIP member/central overlap');ranges.append((at,end))
        b=z.read(i);require(len(b)==i.file_size,'ZIP decoded size')
        if not i.is_dir():out[name]=b
        rows.append({'path':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    for a,b in zip(sorted(ranges),sorted(ranges)[1:]):require(a[1]<=b[0],'ZIP local overlap')
    z.close();return out,rows,total

class Cursor:
    def __init__(self,b):self.b=b;self.p=0
    def take(self,n):
        require(0<=n<=len(self.b)-self.p,'binary truncated');b=self.b[self.p:self.p+n];self.p+=n;return b
    def num(self,n):return int.from_bytes(self.take(n),'big')

def class_data(b):
    r=Cursor(b);require(r.take(4)==b'\xca\xfe\xba\xbe','class magic');minor,major=r.num(2),r.num(2)
    require(minor==0 and 45<=major<=69,'class version');cp=[None]*r.num(2);i=1
    while i<len(cp):
        t=r.num(1)
        if t==1:v=r.take(r.num(2)).replace(b'\xc0\x80',b'\0').decode('utf-8','surrogatepass')
        elif t in (7,8,16,19,20):v=r.num(2)
        elif t in (9,10,11,12,17,18):v=(r.num(2),r.num(2))
        elif t in (3,4):v=r.take(4)
        elif t in (5,6):v=r.take(8)
        elif t==15:v=(r.num(1),r.num(2))
        else:raise ValueError('unknown CP tag')
        cp[i]=(t,v);i+=2 if t in (5,6) else 1
    def utf(i):require(cp[i][0]==1,'CP utf');return cp[i][1]
    def cls(i):require(cp[i][0]==7,'CP class');return utf(cp[i][1])
    def ref(i):
        t,(owner,nt)=cp[i];require(t in (9,10,11),'CP member');name,desc=cp[nt][1];return [cls(owner),utf(name),utf(desc)]
    def attrs(c):
        d={}
        for _ in range(c.num(2)):
            name=utf(c.num(2));require(name not in d,'duplicate attr');d[name]=c.take(c.num(4))
        return d
    access=r.num(2);owner=cls(r.num(2));parent=r.num(2);parent=cls(parent) if parent else None
    interfaces=[cls(r.num(2)) for _ in range(r.num(2))];fields=[];methods=[]
    for table in (fields,methods):
        for _ in range(r.num(2)):
            flags,name,desc=r.num(2),utf(r.num(2)),utf(r.num(2));a=attrs(r);row={'name':name,'descriptor':desc,'access':flags}
            if 'Code' in a:
                c=Cursor(a['Code']);stack,locals_=c.num(2),c.num(2);code=c.take(c.num(4));handlers=[tuple(c.num(2) for _ in range(4)) for _ in range(c.num(2))];attrs(c)
                require(c.p==len(c.b),'Code trailing');row.update(code=code,handlers=handlers,max_stack=stack,max_locals=locals_)
            table.append(row)
    a=attrs(r);require(r.p==len(b),'class trailing');source=utf(int.from_bytes(a['SourceFile'],'big')) if 'SourceFile' in a else None
    return {'owner':owner,'parent':parent,'source':source,'access':access,'interfaces':interfaces,'fields':fields,'methods':methods,'cp':cp,'ref':ref,'major':major}

def jvm_instructions(code,resolve):
    # JVM formats are grouped by operand encoding, independently of subject objects.
    width=[1]*202
    for op in [16,18,*range(21,26),*range(54,59),169,188]:width[op]=2
    for op in [17,19,20,132,*range(153,169),*range(178,185),187,189,192,193,198,199]:width[op]=3
    for op in [185,186,200,201]:width[op]=5
    width[197]=4;pc=0;out=[]
    while pc<len(code):
        op=code[pc];require(op<202,'JVM opcode');n=width[op]
        if op in (170,171):
            at=(pc+4)&~3
            if op==170:
                lo,hi=struct.unpack_from('>ii',code,at+4);count=hi-lo+1;require(0<=count<=65536,'tableswitch');n=at+12+count*4-pc
            else:
                count=struct.unpack_from('>i',code,at+4)[0];require(0<=count<=65535,'lookupswitch');n=at+8+count*8-pc
        if op==196:n=6 if code[pc+1]==132 else 4
        require(pc+n<=len(code),'JVM width');row={'pc':pc,'op':op}
        if 178<=op<=185:row['ref']=resolve(int.from_bytes(code[pc+1:pc+3],'big'))
        out.append(row);pc+=n
    require(pc==len(code),'JVM exact end');return out

def independent_classes(files,prefix,report,map_report):
    raw={n[len(prefix):]:b for n,b in files.items() if n.startswith(prefix)}
    require(raw and all(n.endswith('.class') for n in raw),'closed class files')
    rows=[];maps=[];classes={};later=[];calls=[];methods=fields=code_methods=instructions=0
    for path,b in sorted(raw.items()):
        c=class_data(b);require(path==c['owner']+'.class','class path');classes[c['owner']]=c;methods+=len(c['methods']);fields+=len(c['fields'])
        rows.append({'path':path,'owner':c['owner'],'source_file':c['source'],'superclass':c['parent'],'identity':identity(b)})
        maps.append({'path':path,**identity(b)})
        product=c['owner'].startswith(P) and c['source'] in SOURCES
        for i,item in enumerate(c['cp']):
            if product and item and item[0] in (9,10,11):
                ref=c['ref'](i)
                if ref[1] in LATER:later.append({'class':c['owner'],'reference':ref})
        for m in c['methods']:
            if 'code' not in m:continue
            code_methods+=1;ins=jvm_instructions(m['code'],c['ref']);instructions+=len(ins)
            for x in ins:
                if product and x.get('ref',[None])[0] in HELPERS:calls.append({'caller':[c['owner'],m['name'],m['descriptor']],'instruction':x})
    require(rows==report['artifacts'],'independent class artifact rows');require(maps==map_report,'independent emitted class map')
    require(later==report['later_api_constant_pool_references'],'independent later CP refs')
    projection=lambda x:{'caller':x['caller'],'instruction':{k:x['instruction'][k] for k in ('pc','op','ref')}}
    require(calls==[projection(x) for x in report['helper_invocations']],'independent helper invocation rows')
    product=[c for c in classes.values() if c['owner'].startswith(P) and c['source'] in SOURCES]
    require(len(product)==report['product_class_count'],'independent product count')
    return {'class_count':len(classes),'class_bytes':sum(len(b) for b in raw.values()),'product_classes':len(product),'excluded_classes':report['excluded_classes'],'method_definitions':methods,'field_definitions':fields,'code_bodies':code_methods,'decoded_instructions':instructions,'versions':sorted({c['major'] for c in classes.values()}),'later_api_CP_references':later,'helper_invocations':calls,'helper_method_bodies':[{'owner':c['owner'],'name':m['name'],'descriptor':m['descriptor'],'access':m['access'],'handlers':len(m.get('handlers',[])),'code':identity(m['code'])} for c in product if c['owner'] in HELPERS for m in c['methods'] if 'code' in m]},classes

def independent_dex(b,report):
    require(b[:8]==b'dex\n039\0','DEX039');u16=lambda a:struct.unpack_from('<H',b,a)[0];u32=lambda a:struct.unpack_from('<I',b,a)[0]
    require(u32(32)==len(b) and hashlib.sha1(b[32:]).digest()==b[12:32] and zlib.adler32(b[12:])&0xffffffff==u32(8),'DEX header/hash')
    def leb(p):
        v=0
        for shift in range(0,35,7):
            x=b[p];p+=1;v|=(x&127)<<shift
            if x<128:return v,p
        raise ValueError('ULEB overflow')
    strings=[]
    for i in range(u32(56)):
        p=u32(u32(60)+4*i);n,p=leb(p);end=b.index(0,p);s=b[p:end].replace(b'\xc0\x80',b'\0').decode('utf-8','surrogatepass');require(len(s.encode('utf-16-le','surrogatepass'))//2==n,'DEX string length');strings.append(s)
    types_=[strings[u32(u32(68)+4*i)] for i in range(u32(64))]
    def typelist(p):return [types_[u16(p+4+2*i)] for i in range(u32(p))] if p else []
    protos=['('+''.join(typelist(u32(u32(76)+12*i+8)))+')'+types_[u32(u32(76)+12*i+4)] for i in range(u32(72))]
    owner=lambda i:types_[i][1:-1] if types_[i].startswith('L') else types_[i]
    methods=[]
    for i in range(u32(88)):
        c,p,n=struct.unpack_from('<HHI',b,u32(92)+8*i);methods.append([owner(c),strings[n],protos[p]])
    fields=[]
    for i in range(u32(80)):
        c,t,n=struct.unpack_from('<HHI',b,u32(84)+8*i);fields.append([owner(c),strings[n],types_[t]])
    classes={};definitions={};code={};encoded_fields=0
    for i in range(u32(96)):
        a=u32(100)+32*i;c,flags,parent,interfaces,source,annotations,data,static=struct.unpack_from('<8I',b,a)
        name=owner(c);classes[name]={'access':flags,'parent':None if parent==0xffffffff else owner(parent),'source_file':None if source==0xffffffff else strings[source],'interfaces':typelist(interfaces)}
        if not data:continue
        counts=[];p=data
        for j in range(4):n,p=leb(p);counts.append(n)
        encoded_fields+=sum(counts[:2])
        for n in counts[:2]:
            index=0
            for j in range(n):delta,p=leb(p);index+=delta;f,p=leb(p)
        for n in counts[2:]:
            index=0
            for j in range(n):
                delta,p=leb(p);index+=delta;f,p=leb(p);off,p=leb(p);definitions[index]=f
                if off:code[index]=off
    require(classes==report['classes'],'independent DEX class table');require(len(code)==report['structure']['code_bodies'] and len(methods)==report['structure']['method_ids'],'independent DEX counts')
    later=[{'method_id':i,'reference':m} for i,m in enumerate(methods) if m[1] in LATER];require(later==report['later_api_method_ids'],'independent DEX later method IDs')
    widths={}
    for ops,n in [([0,1,4,7,*range(10,19),29,30,33,39,40,*range(123,144),*range(176,208)],1),([2,5,8,19,21,22,25,26,28,31,32,34,35,41,*range(45,62),*range(68,110),*range(144,176),*range(208,227)],2),([3,6,9,20,23,27,36,37,38,42,43,44,*range(110,115),*range(116,121)],3),([24],5)]:widths.update(dict.fromkeys(ops,n))
    calls=[];helper_calls=[];instruction_count=code_units=0;helper_code=[]
    for index,at in code.items():
        registers,ins,outs,tries=struct.unpack_from('<4H',b,at);size=u32(at+12);words=struct.unpack_from('<'+'H'*size,b,at+16);pc=0;code_units+=size
        while pc<size:
            word=words[pc];op=word&255
            if op==0 and word:
                if word==0x100:n=4+2*words[pc+1]
                elif word==0x200:n=2+4*words[pc+1]
                elif word==0x300:n=4+(words[pc+1]*(words[pc+2]|words[pc+3]<<16)+1)//2
                else:raise ValueError('DEX payload')
            else:n=widths[op]
            require(pc+n<=size,'DEX instruction end');instruction_count+=1
            if op in (*range(0x6e,0x73),*range(0x74,0x79)):
                ref=methods[words[pc+1]];row={'caller':methods[index],'pc':pc,'op':op,'reference':ref}
                if ref[1] in LATER:calls.append(row)
                if ref[0] in HELPERS:helper_calls.append(row)
            pc+=n
        if methods[index][0] in HELPERS:helper_code.append({'method_id':index,'method':methods[index],'access':definitions[index],'registers':registers,'input_words':ins,'output_words':outs,'tries':tries,'code_units':size,'code':identity(b[at+16:at+16+size*2])})
    project=lambda x:{'caller':x['caller'],'pc':x['instruction']['pc'],'op':x['instruction']['op'],'reference':x['instruction']['ref']}
    require(calls==[project(x) for x in report['later_api_invocations']],'independent DEX later call sites')
    require(len(helper_calls)==3,'independent DEX helper call count')
    return {'artifact':identity(b),'magic':'039','string_ids':len(strings),'type_ids':len(types_),'proto_ids':len(protos),'field_ids':len(fields),'method_ids':len(methods),'class_definitions':len(classes),'encoded_fields':encoded_fields,'defined_methods':len(definitions),'code_bodies':len(code),'code_units':code_units,'decoded_instructions_and_payloads':instruction_count,'later_api_method_ids':later,'later_api_invocations':calls,'helper_invocations':helper_calls,'helper_code_bodies':helper_code,'synthetic_classes':[n for n in classes if 'ExternalSynthetic' in n or '$$' in n]}

def main():
    guard_path=HERE/'guarded_inspector.py';gb=read_bounded(guard_path,8192);require(identity(gb)=={'bytes':5958,'sha256':'7c4cb8714869601dc2d7747f1c6c06a476b840a37c4cd71c151a0bc16361ab9b'},'guard pin')
    g=types.ModuleType('_binary_review_guard');exec(compile(gb,str(guard_path),'exec',dont_inherit=True),g.__dict__);guard=g.install_guards()
    denied=[]
    for name,fn in [('os.fork',g.os.fork),('os.waitpid',g.os.waitpid),('os.getpgid',g.os.getpgid),('os.kill',g.os.kill),('signal.setitimer',g.signal.setitimer),('time.monotonic',g.time.monotonic),('subprocess.run',g.subprocess.run),('socket.socket',g.socket.socket),('ctypes.CDLL',g.ctypes.CDLL),('threading.Thread.start',g.threading.Thread.start)]:
        try:fn()
        except g.ActiveAPIDenied:denied.append(name)
        else:raise ValueError('guard did not deny '+name)
    inspector_path=ROOT/'verification/android-view-api-boundary-bytecode-inspection/inspect_artifacts.py';ib=read_bounded(inspector_path,65536);require(identity(ib)==EXPECTED_INSPECTOR,'inspector pin')
    inspector=g.load_data_module(inspector_path,'_pinned_binary_inspector')
    archive=ROOT/'verification/android-view-api-package-runtime-actual-review/local/recovery-001/artifact.zip';raw=read_bounded(archive,201326592);files,inventory,expanded=archive_data(raw)
    matches=[n for n in files if n.endswith('/host-class-inspection.json')];require(len(matches)==1,'unique host report');prefix=matches[0].removesuffix('host-class-inspection.json')
    reports={k:jread(files[prefix+n]) for k,n in [('host','host-class-inspection.json'),('sdk','sdk-class-inspection.json'),('dex','dex-inspection.json')]};require(all(r.get('accepted') is True for r in reports.values()),'three accepted emitted reports')
    sdk=Path('/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar');sdk_raw=read_bounded(sdk,67108864);require(identity(sdk_raw)==EXPECTED_SDK,'exact SDK37 bytes')
    attempt=sys.argv[1] if len(sys.argv)==2 else '001';require(attempt in ('001','002'),'bounded data attempt');local=HERE/'local'/('emitted-'+attempt);require(not local.exists(),'do not overwrite prior data result');local.mkdir()
    selected={n[len(prefix+'scratch/'):]:b for n,b in files.items() if n.startswith(prefix+'scratch/') and (n.startswith(prefix+'scratch/host-classes/') or n.startswith(prefix+'scratch/sdk-classes/') or n.startswith(prefix+'scratch/dex/'))}
    require(selected and [n for n in selected if n.startswith('dex/')]==['dex/classes.dex'],'exact one DEX namespace')
    for n,b in selected.items():p=local/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    reruns={};independent={};class_sets={}
    for kind in ('host','sdk'):
        rerun=inspector.inspect_classes(local/(kind+'-classes'),platform_jar=sdk);require(jread(json.dumps(rerun).encode())==reports[kind],kind+' report exact correspondence');reruns[kind]={'exact_emitted_report_correspondence':True,'report':identity(files[prefix+kind+'-class-inspection.json'])}
        independent[kind],class_sets[kind]=independent_classes(files,prefix+'scratch/'+kind+'-classes/',reports[kind],jread(files[prefix+kind+'-classes.json']))
    dex=selected['dex/classes.dex'];rerun=inspector.inspect_dex(local/'dex/classes.dex');require(jread(json.dumps(rerun).encode())==reports['dex'],'DEX report exact correspondence');reruns['dex']={'exact_emitted_report_correspondence':True,'report':identity(files[prefix+'dex-inspection.json'])};independent['dex']=independent_dex(dex,reports['dex'])
    require(jread(files[prefix+'receipt.json'])['dex']==identity(dex),'receipt exact DEX identity')
    sdk_members=[]
    with zipfile.ZipFile(io.BytesIO(sdk_raw)) as jar:
        require(len(jar.infolist())<=20000,'SDK member count')
        for name in ('android/widget/EditText','android/widget/TextView','android/view/View'):
            info=jar.getinfo(name+'.class');require(info.file_size<=1048576,'SDK hierarchy bound');b=jar.read(info);c=class_data(b);require(c['owner']==name,'SDK owner');sdk_members.append({'owner':name,'superclass':c['parent'],'artifact':identity(b),'setters':[{'name':m['name'],'descriptor':m['descriptor'],'access':m['access']} for m in c['methods'] if m['name'] in LATER]})
    view=sdk_members[2];text=sdk_members[1];edit=sdk_members[0]
    require(edit['superclass']=='android/widget/TextView','EditText superclass');require({x['name'] for x in text['setters'] if x['name'] in SETTERS}==set(SETTERS),'TextView exact later setter declarations')
    require(all(sum(x['name']==n and x['descriptor']=='(Landroid/graphics/drawable/Drawable;)V' for x in text['setters'])==1 for n in SETTERS),'SDK exact drawable overload declarations');require(any(x['name']=='setStateDescription' and x['descriptor']=='(Ljava/lang/CharSequence;)V' for x in view['setters']),'View stateDescription declaration')
    result={'schema':1,'status':'scoped-pass','scope':'DATA ONLY: exact emitted report reruns and independent classfile/DEX member and invocation corroboration','binding':{'repository':'snowdamiz/mixer','head':'c89b4d1657fc46581d8788169f9c961a2413c4f4','run_id':40895131023,'run_attempt':1,'job_id':123522047495,'artifact_id':12907091274},'archive':{**identity(raw),'members':len(inventory),'expanded_bytes':expanded,'output_prefix':prefix,'strict_path_metadata_CRC_and_local_overlap_checks':True},'data_command':{'argv':['/opt/homebrew/bin/python3','-I','-B','-S',str(HERE/'corroborate.py'),attempt],'attempt':attempt,'source':identity((HERE/'corroborate.py').read_bytes()),'guard_source':identity(gb),'frozen_product_tree':'d767f19554c88bd24f58663de268d7a80119522380cfeb4043c37d35b432a21e','delivered_revision_from_root':'c89b4d1657fc46581d8788169f9c961a2413c4f4'},'python':{'executable':sys.executable,'version':sys.version,'flags':{'isolated':sys.flags.isolated,'no_site':sys.flags.no_site,'dont_write_bytecode':sys.dont_write_bytecode}},'guard':{**guard,'denial_controls':denied,'subject_import_performed':True,'subject_execution_performed':True},'inspector':EXPECTED_INSPECTOR,'platform_jar':{**EXPECTED_SDK,'path':str(sdk),'hierarchy_members':sdk_members},'three_reports':reruns,'independent':independent,'observed_report_helpers':{k:reports[k]['helpers'] for k in reports},'observed_report_guards':{k:reports[k]['guards'] for k in reports},'observed_classfile_api36_comparisons':{k:reports[k]['independent_api36_comparisons'] for k in ('host','sdk')},'active_execution':{'compiler_JVM_ART_product_native_UI_capture_network_Git_gh':0,'subprocesses_signals_timers_job_probes':0},'limitations':['Artifact/source/tool/run custody and hosted command execution remain the separate root/outer review obligation.','No compiler, JVM, ART, native, OEM, UI, IME, TalkBack, simulator/emulator, or physical-device execution occurred in this lane.','Finite binary data checks do not prove general JVM/DEX verifier semantics, annotation/debug/encoded-value semantics, ART linkage, independent DEX API36 denial, full matrix/BCI equivalence, public/lower-API V2 admission, source-pair promotion, OTA/release, or GA.','Raw extracted class/DEX bytes and raw ZIP remain ignored local evidence; no scratch cleanup or provider disposal is inferred.']}
    output=HERE/'binary-review.json';output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    (HERE/'local'/'archive-inventory.json').write_text(json.dumps(inventory,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':result['status'],'archive':result['archive'],'counts':{k:{n:v for n,v in d.items() if isinstance(v,int)} for k,d in independent.items()},'reports_exact':3,'guard_denials':len(denied),'review':str(output)}))

if __name__=='__main__':main()
