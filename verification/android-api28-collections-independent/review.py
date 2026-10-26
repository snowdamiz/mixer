#!/usr/bin/env python3
"""Independent finite binary/library review. Never imports or executes producer code."""
from pathlib import Path
import ast, datetime, hashlib, json, os, re, shutil, signal, struct, subprocess, sys, tempfile, time, traceback, zipfile, zlib
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/android-api28-collections-prerequisite'
PROFILE = ROOT / 'verification/android-environment-platform-profile4'
SDK = Path('/opt/homebrew/share/android-commandlinetools')
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
JAR = SDK / 'platforms/android-37.0/android.jar'
APIS = JAR.parent / 'data/api-versions.xml'
BT = SDK / 'build-tools/37.0.0'

def identity(path):
    value = path.read_bytes()
    return {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}

def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def require(value, message):
    if not value: raise AssertionError(message)

def java_name(descriptor):
    descriptor = descriptor.lstrip('[')
    if descriptor.startswith(('Ljava/', 'Ljavax/')) and descriptor.endswith(';'):
        return descriptor[1:-1]
    return None

class Dex:
    """DEX039 table/class-data/code decoder, with fail-closed unknown opcodes.

    All external symbolic references belong to the global type/field/method ID
    tables, including references in annotation, encoded-value and catch data.
    No call-site or method-handle sections are admitted by this finite decoder.
    Instruction parsing is additional ownership evidence, not the reference census.
    """
    def __init__(self, data):
        self.data = data
        require(data[:8] == b'dex\n039\0', 'unsupported DEX magic')
        require(len(data) >= 112 and self.u32(32) == len(data) and self.u32(36) == 112, 'DEX bounds/header')
        require(self.u32(40) == 0x12345678, 'DEX endianness')
        require(hashlib.sha1(data[32:]).digest() == data[12:32], 'DEX SHA1')
        require(zlib.adler32(data[12:]) & 0xffffffff == self.u32(8), 'DEX checksum')
        self.map = {}
        off = self.u32(52)
        for i in range(self.u32(off)):
            kind, unused, count, start = struct.unpack_from('<HHII', data, off + 4 + i * 12)
            require(kind not in self.map and unused == 0 and start < len(data), 'DEX map entry')
            self.map[kind] = {'count': count, 'offset': start}
        require(not ({7, 8} & self.map.keys()), 'call-site or method-handle section requires expanded review')
        for kind, count_at, size in [(1,56,4),(2,64,4),(3,72,12),(4,80,8),(5,88,8),(6,96,32)]:
            count, start = self.u32(count_at), self.u32(count_at + 4)
            require(self.map[kind] == {'count': count, 'offset': start}, 'header/map disagreement')
            require(start + count * size <= len(data), 'ID section bounds')
        self.strings = [self.string(self.u32(self.u32(60) + 4*i)) for i in range(self.u32(56))]
        self.types = [self.strings[self.u32(self.u32(68)+4*i)] for i in range(self.u32(64))]
        self.protos = []
        for i in range(self.u32(72)):
            at = self.u32(76)+12*i
            self.protos.append('(' + ''.join(self.typelist(self.u32(at+8))) + ')' + self.types[self.u32(at+4)])
        self.fields = []
        for i in range(self.u32(80)):
            owner, typ, name = struct.unpack_from('<HHI',data,self.u32(84)+8*i)
            self.fields.append((self.types[owner][1:-1], self.strings[name], self.types[typ]))
        self.methods = []
        for i in range(self.u32(88)):
            owner, proto, name = struct.unpack_from('<HHI',data,self.u32(92)+8*i)
            self.methods.append((self.types[owner][1:-1], self.strings[name], self.protos[proto]))
        self.definitions, self.code, self.edges = [], {}, []
        for i in range(self.u32(96)):
            at = self.u32(100)+32*i
            owner = self.types[self.u32(at)]
            self.definitions.append(owner)
            data_at = self.u32(at+24)
            if not data_at: continue
            counts = []
            for _ in range(4): v,data_at=self.leb(data_at); counts.append(v)
            for count in counts[:2]:
                index=0
                for _ in range(count):
                    delta,data_at=self.leb(data_at); flags,data_at=self.leb(data_at); index += delta
                    require(index < len(self.fields), 'encoded field index')
            for count in counts[2:]:
                index=0
                for _ in range(count):
                    delta,data_at=self.leb(data_at); flags,data_at=self.leb(data_at); code_at,data_at=self.leb(data_at); index += delta
                    require(index < len(self.methods), 'encoded method index')
                    if code_at:
                        require(index not in self.code, 'duplicate method body')
                        self.code[index] = self.decode_code(index,code_at)
        require(len(self.code) == self.map[0x2001]['count'], 'all code items consumed')

    def u16(self, at): return struct.unpack_from('<H',self.data,at)[0]
    def u32(self, at): return struct.unpack_from('<I',self.data,at)[0]
    def leb(self, at):
        value=0
        for shift in range(0,35,7):
            byte=self.data[at]; at+=1; value |= (byte&127)<<shift
            if not byte&128: return value,at
        raise AssertionError('invalid uleb128')
    def string(self, at):
        length,at = self.leb(at)
        raw=self.data[at:self.data.index(0,at)]
        value=raw.replace(b'\xc0\x80',b'\x00').decode('utf-8','surrogatepass')
        require(len(value.encode('utf-16-le','surrogatepass'))//2 == length, 'MUTF8 length')
        return value
    def typelist(self, at):
        return [] if at == 0 else [self.types[self.u16(at+4+2*i)] for i in range(self.u32(at))]
    def method_name(self, index):
        owner,name,desc=self.methods[index]
        return owner.replace('/','.')+'.'+name+':'+desc
    def decode_code(self, index, at):
        size = self.u32(at+12)
        words=list(struct.unpack_from('<'+'H'*size,self.data,at+16))
        widths={}
        for ops,width in [([0,1,4,7]+list(range(10,19))+[29,30,33,39,40]+list(range(123,144))+list(range(176,208)),1),
                          ([2,5,8,19,21,22,25,26,28,31,32,34,35,41]+list(range(45,62))+list(range(68,110))+list(range(144,176))+list(range(208,227)),2),
                          ([3,6,9,20,23,27,36,37,38,42,43,44]+list(range(110,115))+list(range(116,121)),3),([24],5)]:
            widths.update(dict.fromkeys(ops,width))
        out=[]; pc=0
        while pc<size:
            op=words[pc]&255; word=words[pc]
            if op==0 and word:
                require(pc%2==0,'unaligned payload')
                if word==0x100: width=4+2*words[pc+1]
                elif word==0x200: width=2+4*words[pc+1]
                elif word==0x300: width=4+(words[pc+1]*(words[pc+2]|words[pc+3]<<16)+1)//2
                else: raise AssertionError('unknown payload')
            else:
                require(op in widths,'unknown/reserved opcode '+hex(op));width=widths[op]
            require(pc+width<=size,'instruction width bounds')
            row={'pc':pc,'opcode':hex(op),'words':words[pc:pc+width]}
            if op in list(range(110,115))+list(range(116,121)):
                target=words[pc+1];require(target<len(self.methods),'invoke method index')
                row['target']=self.method_name(target)
                self.edges.append({'caller':self.method_name(index),'pc':pc,'target':row['target'],'kind':'invoke'})
            if 82<=op<=109:
                target=words[pc+1];require(target<len(self.fields),'field index')
                owner,name,desc=self.fields[target];row['field']=[owner,name,desc]
                self.edges.append({'caller':self.method_name(index),'pc':pc,'target':owner+'.'+name,'descriptor':desc,'kind':'field','opcode':hex(op)})
            out.append(row);pc+=width
        return {'registers':self.u16(at),'instructions':out,'code_units':size}
    def refs(self):
        return {'types':sorted({n for t in self.types if (n:=java_name(t))}),
                'methods':sorted([list(x) for x in self.methods if x[0].startswith(('java/','javax/'))]),
                'fields':sorted([list(x) for x in self.fields if x[0].startswith(('java/','javax/'))])}

class ClassFile:
    def __init__(self,data):
        require(data[:4]==b'\xca\xfe\xba\xbe','class magic');at=8
        def u2():
            nonlocal at
            value=struct.unpack_from('>H',data,at)[0];at+=2;return value
        def u4():
            nonlocal at
            value=struct.unpack_from('>I',data,at)[0];at+=4;return value
        count=u2();cp=[None]*count;i=1
        while i<count:
            tag=data[at];at+=1
            if tag==1:
                length=u2();cp[i]=data[at:at+length].decode('utf-8','surrogatepass');at+=length
            elif tag in (7,8,16,19,20): cp[i]=u2()
            elif tag in (3,4,9,10,11,12,17,18): at+=4
            elif tag in (5,6): at+=8;i+=1
            elif tag==15: at+=3
            else: raise AssertionError('class CP tag '+str(tag))
            i+=1
        self.flags=u2();self.name=cp[cp[u2()]]; parent=u2();self.parents=[] if not parent else [cp[cp[parent]]]
        self.parents.extend(cp[cp[u2()]] for _ in range(u2()))
        self.fields,self.methods={},{}
        for table in (self.fields,self.methods):
            for _ in range(u2()):
                flags=u2();name=cp[u2()];desc=cp[u2()];table[(name,desc)]=flags
                for _ in range(u2()): u2();length=u4();at+=length

def metadata_resolution(classes,owner,name,kind,seen=()):
    if owner in seen or owner not in classes: return []
    node=classes[owner];floor=int(node.get('since','1'));found=[]
    for m in node.findall(kind):
        if m.get('name')==name:
            found.append({'declared_owner':owner,'api':max(floor,int(m.get('since','1'))),
                          'removed':min(int(m.get('removed','9999')),int(node.get('removed','9999'))),'path':[owner]})
    if name.startswith('<init>'): return found
    for edge in list(node.findall('extends'))+list(node.findall('implements')):
        for result in metadata_resolution(classes,edge.get('name'),name,kind,seen+(owner,)):
            result=dict(result,api=max(result['api'],floor,int(edge.get('since','1'))),
                        removed=min(result['removed'],int(edge.get('removed','9999')),int(node.get('removed','9999'))),path=[owner]+result['path'])
            found.append(result)
    return found

def main():
    command=[];checks=[];scratch=None
    def check(ok,label): require(ok,label);checks.append(label)
    def run(label,argv):
        env=dict(os.environ)
        for key in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','CLASSPATH'): env.pop(key,None)
        env['JAVA_HOME']=str(JDK);env['PATH']=str(JDK/'bin')+os.pathsep+env.get('PATH','')
        started=time.monotonic();proc=subprocess.Popen(list(map(str,argv)),cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timeout=False
        try: stdout,stderr=proc.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            timeout=True;os.killpg(proc.pid,signal.SIGKILL);stdout,stderr=proc.communicate()
        (HERE/(label+'.stdout')).write_bytes(stdout);(HERE/(label+'.stderr')).write_bytes(stderr)
        command.append({'label':label,'argv':list(map(str,argv)),'exit_code':proc.returncode,'timed_out':timeout,'seconds':round(time.monotonic()-started,6),'owned_child_reaped':True})
        require(not timeout and proc.returncode==0,'failed host command '+label)
        return stdout.decode(errors='replace')
    try:
        check(identity(PRODUCER/'manifest.json')['sha256']=='168ade73aa770bf1d3c6c595b3c24b55f3ed99dcba400d4422694b60c6749c0c','producer manifest identity')
        manifest=json.loads((PRODUCER/'manifest.json').read_text())
        for name,expected in manifest['files'].items(): check(identity(ROOT/name)==expected,'producer member '+name)
        check(len(manifest['files'])==95 and sum(x['bytes'] for x in manifest['files'].values())==15196628,'producer 95-member exact census')
        check(identity(PROFILE/'manifest.json')['sha256']=='046f1a5a4f69dae7dafb529d55caf7fcd475a54614c40103f90be1d7fd6d39b4','profile4 manifest identity')
        profile=json.loads((PROFILE/'proposed-profile4.json').read_text());source_map=json.loads((PRODUCER/'source-map.json').read_text())
        profile_map=json.loads((PROFILE/'source-map.json').read_text())
        profile_manifest=json.loads((PROFILE/'manifest.json').read_text())
        profile_manifest_map={m['path']:{k:m[k] for k in ('bytes','sha256')} for m in profile_manifest['members']}
        check(identity(PROFILE/'source-map.json')==profile_manifest_map['verification/android-environment-platform-profile4/source-map.json'],'profile4 source map custody')
        check(identity(PROFILE/'proposed-profile4.json')=={k:source_map['verification/android-environment-platform-profile4/proposed-profile4.json'][k] for k in ('bytes','sha256')},'profile4 source identity matches frozen producer')
        check(len(profile['adapter_files'])==23,'adapter23 count')
        java={p:r for p,r in source_map.items() if p.endswith('.java')}
        check(len(java)==20,'Java20 count')
        projection={p:r for p,r in profile['adapter_files'].items() if p.endswith('.java')}
        check(len(projection)==17,'adapter17 Java count')
        for name,row in projection.items(): check(java['native/android/'+name]['sha256']==row['sha256'],'Java projection '+name)
        for name,row in java.items():
            expected={k:row[k] for k in ('bytes','sha256')}
            check(identity(ROOT/row['snapshot'])==expected,'Java snapshot '+name)
            check(identity(ROOT/name)==expected,'current canonical Java matches frozen source '+name)
        for name,row in profile['adapter_files'].items():
            relative='native/android/'+('engine/' if name.startswith('Sources/') else '')+name
            check(profile_map[relative]==row and identity(PROFILE/'source'/relative)==row,'all23 profile4 snapshot custody '+name)
        factory_index=[]
        for name,row in sorted(java.items()):
            for line,text in enumerate((ROOT/row['snapshot']).read_text().splitlines(),1):
                for match in re.finditer(r'\b(List|Set|Map)\.(of|copyOf|ofEntries|entry)\s*\(',text):
                    factory_index.append({'path':name,'line':line,'symbol':match.group(1)+'.'+match.group(2),'snippet':text.strip()})
        check(len(factory_index)==43 and sum('V1.java' not in x['path'] for x in factory_index)==41,'43 source sites, 41 private V2 and two V1; navigation only')
        write('source-factory-navigation.json',factory_index)
        write('inputs.json',{'producer_manifest':identity(PRODUCER/'manifest.json'),'profile4_manifest':identity(PROFILE/'manifest.json'),
            'frozen_Java20':java,'source_projection_sha256':hashlib.sha256(''.join(p+'\0'+java[p]['sha256']+'\n' for p in sorted(java)).encode()).hexdigest(),
            'inherited_context_revision':'fb4c8f074f1a3e5eb2b1b1a45b44f0fa61a7cc62','context_revision_is_not_live_Git_custody':True,
            'official_tool_inputs':json.loads((PRODUCER/'tool-provenance.json').read_text()),'D8_implementation':identity(BT/'lib/d8.jar')})
        tools=json.loads((PRODUCER/'tool-provenance.json').read_text())
        for name,row in tools.items(): check(identity(Path(name))==row,'official tool/database '+name)
        check(identity(BT/'lib/d8.jar')==json.loads((PRODUCER/'attempt-1/d8-implementation-identity.json').read_text())['identity'],'D8 implementation jar')
        db={c.get('name'):c for c in ET.parse(APIS).getroot().findall('class')}
        excerpt=ET.parse(PRODUCER/'official-sdk-api-excerpt.xml').getroot()
        def element_shape(c): return (c.tag,dict(c.attrib),[element_shape(child) for child in c])
        for c in excerpt.findall('class'): check(element_shape(c)==element_shape(db[c.get('name')]),'official excerpt exact class '+c.get('name'))
        dex=Dex((PRODUCER/'attempt-1/actual20.classes.dex').read_bytes());refs=dex.refs();write('binary-references.json',refs)
        original=json.loads((PRODUCER/'attempt-1/dex-java-reference-ids.json').read_text())
        check(refs['types']==original['types'],'all Java array/component types included')
        check([[o,n+d] for o,n,d in refs['methods']]==original['methods'],'all 163 Java method IDs match')
        check([[o,n] for o,n,d in refs['fields']]==original['fields'],'all seven Java field IDs match')
        check(len(refs['types'])==60 and len(refs['methods'])+len(refs['fields'])==170,'170-member 60-type census')
        check(not any('/stream/' in x for x in refs['types']) and 'java/lang/Record' not in refs['types'],'no emitted Java Record or stream type')
        audit=[]
        with zipfile.ZipFile(JAR) as archive:
            cache={}
            def classfile(name):
                if name not in cache: cache[name]=ClassFile(archive.read(name+'.class'))
                return cache[name]
            def signature_owner(owner,name,desc,kind,seen=()):
                if owner in seen:return []
                c=classfile(owner);table=c.methods if kind=='method' else c.fields
                out=[{'owner':owner,'flags':table[(name,desc)]}] if (name,desc) in table else []
                if name=='<init>':return out
                for parent in c.parents: out+=signature_owner(parent,name,desc,kind,seen+(owner,))
                return out
            for name in refs['types']:
                node=db.get(name);check(node is not None and int(node.get('since','1'))<=28 and int(node.get('removed','9999'))>28,'Java component type floor '+name)
            for kind,rows in [('method',refs['methods']),('field',refs['fields'])]:
                for owner,name,desc in rows:
                    all_paths=metadata_resolution(db,owner,name+desc if kind=='method' else name,kind)
                    eligible=[x for x in all_paths if x['api']<=28 and x['removed']>28]
                    check(bool(eligible),'API28 metadata resolution '+owner+'.'+name+desc)
                    signatures=signature_owner(owner,name,desc,kind)
                    check(bool(signatures),'SDK37 exact signature '+owner+'.'+name+desc)
                    if kind=='field': check(any(x['declared_owner'] in {s['owner'] for s in signatures} for x in eligible),'field descriptor bound to API declaration '+owner+'.'+name)
                    audit.append({'kind':kind,'owner':owner,'name':name,'descriptor':desc,'API28_resolution_paths':eligible,'SDK37_signature_declarations':signatures})
        write('independent-api-audit.json',audit)
        helpers=json.loads((PRODUCER/'attempt-1/collection-lowering.json').read_text())
        selected=set(helpers['helpers_and_boundary_bodies'])
        relevant=[e for e in dex.edges if (e['kind']=='invoke' and e['target'] in selected) or (e['kind']=='field' and e['target'] in ('java/util/Collections.EMPTY_LIST','java/util/Collections.EMPTY_MAP') and e['opcode'] in ('0x60','0x61','0x62','0x63','0x64','0x65','0x66'))]
        projected=sorted((e['caller'],e['target']) for e in relevant)
        expected=sorted((e['caller'],e['target']) for e in helpers['call_edges'])
        check(projected==expected and len(relevant)==57,'all 57 lowering edges independently decoded')
        check(sum('EMPTY_' in e['target'] for e in relevant)==15,'all 15 empty edges independently decoded')
        write('binary-lowering-edges.json',relevant)
        write('binary-helper-bodies.json',{dex.method_name(i):body for i,body in dex.code.items() if dex.method_name(i) in selected})
        # Cross-check each retained disassembly code unit against the independent binary body.
        for name,row in helpers['helpers_and_boundary_bodies'].items():
            body=next(v for i,v in dex.code.items() if dex.method_name(i)==name)
            check(len(body['instructions'])==len(row['code']),'complete helper disassembly '+name)
            for ins,line in zip(body['instructions'],row['code']):
                encoded=line.split('|',1)[0].split(':',1)[1].strip().replace(' ','')
                raw=bytes.fromhex(encoded)
                check(list(struct.unpack('<'+'H'*(len(raw)//2),raw))==ins['words'],'helper binary/disassembly code unit '+name+'@'+str(ins['pc']))
        external_core=[e for e in dex.edges if e['kind']=='invoke' and e['target'].startswith('dev.mixer.android.OwnerLifecycleV2.') and e['target'].endswith(')Ljava/util/List;') and not e['caller'].startswith('dev.mixer.android.OwnerLifecycleV2.')]
        def native_owner_class(caller):
            owner=caller.split(':',1)[0].rsplit('.',1)[0]
            return owner=='dev.mixer.android.NativeOwnerV2' or owner.startswith('dev.mixer.android.NativeOwnerV2$')
        check(bool(external_core) and all(native_owner_class(e['caller']) for e in external_core),'only NativeOwnerV2 and nested Work externally call core list methods in Java20')
        group_field=[e for e in dex.edges if e['kind']=='field' and e['target']=='dev/mixer/android/NativeAppearanceViewsV2$Group.records']
        group_writes=[e for e in group_field if e['opcode']=='0x5b']
        check(len(group_writes)==3 and any('.<init>:' in e['caller'] for e in group_writes) and any('.installChildren:' in e['caller'] for e in group_writes) and any('.restoreV2:' in e['caller'] for e in group_writes),'Group.records exactly constructor placeholder, installation replacement, rollback replacement writes')
        write('consumer-binary-ownership.json',{'external_core_list_calls':external_core,'Group_records_field_accesses':group_field})
        # Actual metadata controls distinguish overloads, unknown members, and post28 ancestry edges.
        controls=[]
        for owner,name,kind in [('java/util/List','copyOf(Ljava/util/Collection;)Ljava/util/List;','method'),('java/util/Collection','toArray(Ljava/util/function/IntFunction;)[Ljava/lang/Object;','method'),('java/util/List','notARealMethod()V','method'),('java/util/Collections','NOT_A_REAL_FIELD','field')]:
            paths=metadata_resolution(db,owner,name,kind);check(not any(x['api']<=28 and x['removed']>28 for x in paths),'negative metadata '+name);controls.append(name)
        synthetic=ET.fromstring('<api><class name="child"><extends name="parent" since="29"/></class><class name="parent"><method name="m()V"/></class></api>')
        check(not any(x['api']<=28 for x in metadata_resolution({c.get('name'):c for c in synthetic},'child','m()V','method')),'negative inherited edge floor');controls.append('inherited API29 edge')
        for label,data in [('truncated DEX',dex.data[:-1]),('checksum mismatch',dex.data[:200]+bytes([dex.data[200]^1])+dex.data[201:])]:
            try: Dex(data)
            except (AssertionError,struct.error,IndexError): controls.append(label)
            else: raise AssertionError('accepted negative '+label)
        write('negative-controls.json',controls)
        # Read frozen consumer source as data. Never import/execute its top-level functions.
        frozen=PRODUCER/'inputs/frozen-profile4-android-build.py'
        check(identity(frozen)==profile_map['cli/Sources/MixerBuild/Resources/android-build.py'],'exact frozen profile4 driver source')
        ast.parse(frozen.read_text())
        driver=frozen.read_text()
        for text in ["BT = SDK / 'build-tools/37.0.0'","JAR = SDK / 'platforms/android-37.0/android.jar'","'android_build_tools': {'path': str(BT), 'sha256': tree(BT)}","'jdk': {'path': str(JDK), 'sha256': tree(JDK)}","if identity != android['toolchain']:","run([JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror', '-classpath', JAR, '-d', classes, *sources])","run([BT / 'd8', '--min-api', '28', '--lib', JAR, '--output', dex, *sorted(classes.rglob('*.class'))])"]:
            check(text in driver,'frozen driver binding '+text)
        check(driver.index("if identity != android['toolchain']:")<driver.index("run([JDK / 'bin/javac'"),'lock comparison precedes compilation')
        scratch=Path(tempfile.mkdtemp(prefix='mixer-independent-api28-collections-'))
        # Execute only two reviewed pure hashing functions extracted from the frozen
        # driver; never its top level, inspect(), build(), or any generated app.
        syntax=ast.parse(driver);functions=[n for n in syntax.body if isinstance(n,ast.FunctionDef) and n.name in ('digest','tree')]
        check(len(functions)==2,'bounded pure hashing extraction')
        namespace={'hashlib':hashlib,'os':os,'pathlib':__import__('pathlib')}
        exec(compile(ast.Module(body=functions,type_ignores=[]),str(frozen)+'#digest-tree-only','exec'),namespace)
        fake=scratch/'fake-build-tools';(fake/'lib').mkdir(parents=True);(fake/'d8').write_text('unchanged launcher');(fake/'lib/d8.jar').write_bytes(b'compiler-A')
        before=namespace['tree'](fake);(fake/'lib/d8.jar').write_bytes(b'compiler-B');after=namespace['tree'](fake)
        check(before!=after,'fresh fake distribution lib/d8.jar mutation changes driver tree hash')
        (fake/'alias').symlink_to('lib/d8.jar');alias_before=namespace['tree'](fake);(fake/'lib/d8.jar').write_bytes(b'compiler-C')
        check(alias_before!=namespace['tree'](fake),'fresh fake symlink target bytes participate in driver tree hash')
        outside=scratch/'outside';outside.mkdir();(fake/'escape').symlink_to(outside,target_is_directory=True)
        try: namespace['tree'](fake)
        except RuntimeError: checks.append('fresh fake distribution rejects escaping directory symlink')
        else: raise AssertionError('driver tree accepted escaping directory symlink')
        classes=scratch/'classes';classes.mkdir();output=scratch/'dex';output.mkdir()
        run('python-version',[sys.executable,'--version']);run('java-version',[JDK/'bin/java','-version']);run('javac-version',[JDK/'bin/javac','-version']);run('d8-version',[BT/'d8','--version'])
        sources=[ROOT/row['snapshot'] for name,row in sorted(java.items())]
        run('compile-exact20',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-classpath',JAR,'-d',classes,*sources])
        run('d8-exact20',[BT/'d8','--min-api','28','--lib',JAR,'--output',output,*sorted(classes.rglob('*.class'))])
        fresh=Dex((output/'classes.dex').read_bytes())
        check(fresh.refs()==refs,'fresh exact-flags DEX full Java closure')
        check((output/'classes.dex').read_bytes()==(PRODUCER/'consumer-flags/classes.dex').read_bytes(),'fresh DEX equals frozen exact-consumer-flags DEX bytes')
        shutil.copyfile(output/'classes.dex',HERE/'fresh-exact-flags.dex')
        host=scratch/'host';host.mkdir()
        pure=['Json','UiPacket','OwnerLifecycleV2','AppearanceGeometryV2']
        pure_sources=[PRODUCER/'inputs/native/android/app/src/dev/mixer/android'/(n+'.java') for n in pure]
        run('compile-independent-host',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-d',host,*pure_sources,HERE/'IndependentHost.java'])
        run('independent-host',[JDK/'bin/java','-ea','-cp',host,'dev.mixer.android.IndependentHost'])
        for name,row in java.items(): check(identity(ROOT/name)=={k:row[k] for k in ('bytes','sha256')},'current Java end-of-run stability '+name)
        check(identity(PRODUCER/'manifest.json')['sha256']=='168ade73aa770bf1d3c6c595b3c24b55f3ed99dcba400d4422694b60c6749c0c','producer manifest stable through review')
        write('receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'status':'passed-independent-finite-host-and-binary-review','checks':checks,'checks_count':len(checks),'commands':command,'negative_controls':len(controls),'DEX_tables':{str(k):v for k,v in dex.map.items()},'decoded_code_bodies':len(dex.code),'Java_types':len(refs['types']),'Java_members':len(audit),'lowering_edges':len(relevant),'empty_edges':15,'fresh_D8_exact_consumer_byte_match':True,'producer_or_profile_or_product_mutation':False,'native_runtime_UI_capture_emulator_simulator_phone_or_process_inventory':False,'scope':'Exact frozen Java20 emitted Java-library API floor and observed private read-only consumers only; no universal factory exception equivalence or native execution.'})
        print(json.dumps({'status':'passed','checks':len(checks),'Java_members':len(audit),'code_bodies':len(dex.code)}))
    except Exception:
        write('failure-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json',{'traceback':traceback.format_exc(),'checks_passed':checks,'commands':command})
        raise
    finally:
        if scratch is not None: shutil.rmtree(scratch)
        write('cleanup.json',{'owned_scratch_removed':scratch is None or not scratch.exists(),'owned_host_children_reaped':len(command),'all_recorded_children_reaped':all(c['owned_child_reaped'] for c in command),'commands':command,'native_or_capture_processes_started':False,'other_projects_processes_inspected_or_changed':False})

if __name__=='__main__': main()
