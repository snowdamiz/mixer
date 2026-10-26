#!/usr/bin/env python3
"""Finite source-only prerequisite evidence; never changes product/profile bytes or starts Android."""
from pathlib import Path
import datetime, hashlib, json, os, re, shutil, signal, struct, subprocess, sys, tempfile, time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin')
SDK = Path('/opt/homebrew/share/android-commandlinetools')
ANDROID = SDK / 'platforms/android-37.0/android.jar'
APIS = SDK / 'platforms/android-37.0/data/api-versions.xml'
D8 = SDK / 'build-tools/37.0.0/d8'
PROFILE = 'verification/android-environment-platform-profile4/proposed-profile4.json'
JAVA_DIR = 'native/android/app/src/dev/mixer/android/'
JAVA = ('AdapterInstrumentation AppearanceDescriptorV1 AppearanceDescriptorV2 AppearanceGeometryV2 '
        'AppearanceNativePathsV2 AppearanceResolutionV1 AppearanceResolverV2 AuthoredToggleInputV2 '
        'InstalledAppearanceV2 Json MixerActivity NativeAppearanceViewsV2 NativeBridge NativeCoordinatorV2 '
        'NativeEnvironmentPlatformV2 NativeEnvironmentV2 NativeOwnerV2 NativeRenderer OwnerLifecycleV2 UiPacket').split()
CONTEXT = 'fb4c8f074f1a3e5eb2b1b1a45b44f0fa61a7cc62'

def identity(path):
    data = Path(path).read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def write(name, value):
    target = PACKET / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def dex_refs(path):
    """Read DEX IDs, not a text grep over Java. No code is executed by this parser."""
    data = path.read_bytes()
    assert data[:4] == b'dex\n'
    def u4(offset): return struct.unpack_from('<I', data, offset)[0]
    def u2(offset): return struct.unpack_from('<H', data, offset)[0]
    def string(offset):
        while data[offset] & 128: offset += 1
        offset += 1
        end = data.index(0, offset)
        return data[offset:end].decode('utf-8', errors='replace')
    strings = [string(u4(u4(60) + 4*i)) for i in range(u4(56))]
    types = [strings[u4(u4(68) + 4*i)] for i in range(u4(64))]
    prototypes = []
    for i in range(u4(72)):
        offset = u4(76) + 12*i
        args = u4(offset+8)
        parameters = '' if not args else ''.join(types[u2(args+4+2*j)] for j in range(u4(args)))
        prototypes.append('(' + parameters + ')' + types[u4(offset+4)])
    methods = []
    for i in range(u4(88)):
        offset = u4(92) + 8*i
        owner = types[u2(offset)]
        if owner.startswith('Ljava/') or owner.startswith('Ljavax/'):
            methods.append((owner[1:-1], strings[u4(offset+4)] + prototypes[u2(offset+2)]))
    fields = []
    for i in range(u4(80)):
        offset = u4(84) + 8*i
        owner = types[u2(offset)]
        if owner.startswith('Ljava/') or owner.startswith('Ljavax/'):
            fields.append((owner[1:-1], strings[u4(offset+4)]))
    return {'methods': sorted(set(methods)), 'fields': sorted(set(fields)),
            'types': sorted(t[1:-1] for t in types if t.startswith('Ljava/') or t.startswith('Ljavax/'))}

def api_lookup(classes, owner, name, kind, visited=()):
    if owner in visited: return None
    node = classes.get(owner)
    if node is None: return None
    floor = int(node.get('since', '1'))
    for member in node.findall(kind):
        if member.get('name') == name:
            return {'declared_owner': owner, 'api': max(floor,int(member.get('since',str(floor))))}
    if name.startswith('<init>'): return None
    for tag in ('extends','implements'):
        for parent in node.findall(tag):
            found = api_lookup(classes,parent.get('name'),name,kind,visited+(owner,))
            if found: return dict(found, api=max(found['api'],floor,int(parent.get('since','1'))))
    return None

def main():
    attempt = PACKET / 'attempt-1'
    if attempt.exists(): raise SystemExit('attempt-1 already exists; retain it and choose a new explicit attempt')
    attempt.mkdir()
    scratch = Path(tempfile.mkdtemp(prefix='mixer-api28-collections-'))
    commands = []
    env = dict(os.environ)
    for name in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','CLASSPATH'):
        env.pop(name,None)
    env['JAVA_HOME'] = str(JDK.parent)
    env['PATH'] = str(JDK) + os.pathsep + env.get('PATH','')
    def run(label, argv, timeout=60):
        started = time.monotonic()
        proc = subprocess.Popen([str(x) for x in argv], cwd=ROOT, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed_out = False
        try: stdout,stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True; os.killpg(proc.pid,signal.SIGKILL); stdout,stderr = proc.communicate()
        (attempt / (label+'.stdout')).write_bytes(stdout)
        (attempt / (label+'.stderr')).write_bytes(stderr)
        commands.append({'label':label,'argv':[str(x) for x in argv],'exit_code':proc.returncode,
                         'timeout':timed_out,'seconds':round(time.monotonic()-started,6), 'owned_child_reaped':True})
        if timed_out or proc.returncode: raise RuntimeError('failed command: '+label)
        return stdout.decode(errors='replace')
    status = 'failed'
    try:
        profile = json.loads((ROOT / PROFILE).read_text())
        assert len(profile['adapter_files']) == 23
        profile_java = {k:v for k,v in profile['adapter_files'].items() if k.endswith('.java')}
        assert len(profile_java) == 17
        source_map = {}
        for name in JAVA:
            relative = JAVA_DIR + name + '.java'
            source = ROOT / relative
            original = identity(source)
            profile_name = 'app/src/dev/mixer/android/' + name + '.java'
            if profile_name in profile_java: assert original == profile_java[profile_name], relative
            target = PACKET / 'inputs' / relative
            target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,target)
            source_map[relative] = dict(original, snapshot=str(target.relative_to(ROOT)),
                role='adapter23 Java member' if profile_name in profile_java else 'additional Java compiler companion')
        references = [PROFILE, 'verification/android-environment-platform-root-review/selection.json',
                      'verification/android-environment-platform-root-review/native-acceptance.json',
                      'docs/android-api28-v2-support-prerequisite.md',
                      'docs/android-api28-v2-support-prerequisite-review.md',
                      'docs/android-environment-platform-implementation.md']
        for relative in references:
            target = PACKET / 'inputs' / relative
            target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/relative,target)
            source_map[relative] = dict(identity(target),snapshot=str(target.relative_to(ROOT)),role='frozen context only')
        assert source_map['verification/android-environment-platform-root-review/native-acceptance.json']['sha256'] == '0c15ca808c2f5684d768125674cdfc0bf48bff672193f79fcaaee47726bf2478'
        write('source-map.json',source_map)
        write('profile-projection.json',{'profile_file':PROFILE,'identity':identity(ROOT/PROFILE),
            'adapter_total':23,'adapter_Java':17,'additional_Java_companions':3,
            'adapter_nonJava':{k:v for k,v in profile['adapter_files'].items() if not k.endswith('.java')},
            'nonJava_scope':'Frozen profile data only; not compiled or a Swift/JNI compatibility proof',
            'new_profile_or_canonical_bytes_selected':False})
        tools = [JDK/'java',JDK/'javac',JDK/'javap',D8,ANDROID,APIS,
                 SDK/'platforms/android-37.0/source.properties',SDK/'build-tools/37.0.0/source.properties']
        write('tool-provenance.json',{str(p.resolve()):identity(p) for p in tools})
        run('java-version',[JDK/'java','-version']);run('javac-version',[JDK/'javac','-version'])
        run('javap-version',[JDK/'javap','-version']);run('d8-version',[D8,'--version'])
        run('python-version',[sys.executable,'--version'])
        classes = scratch/'classes'; classes.mkdir()
        sources = [PACKET/'inputs'/JAVA_DIR/(name+'.java') for name in JAVA]
        run('compile-actual20',[JDK/'javac','--release','17','-g','-cp',ANDROID,'-d',classes,*sources])
        emitted = sorted(classes.rglob('*.class'))
        write('attempt-1/class-identities.json',{str(p.relative_to(classes)):identity(p) for p in emitted})
        names = [str(p.relative_to(classes).with_suffix('')).replace('/','.') for p in emitted]
        run('javap-actual20',[JDK/'javap','-classpath',classes,'-v','-c','-p',*names])
        dex = scratch/'dex'; dex.mkdir()
        run('d8-actual20',[D8,'--min-api','28','--lib',ANDROID,'--output',dex,*emitted])
        assert len(list(dex.glob('*.dex'))) == 1
        dexfile = dex/'classes.dex'
        shutil.copyfile(dexfile,attempt/'actual20.classes.dex')
        refs = dex_refs(dexfile)
        write('attempt-1/dex-java-reference-ids.json',refs)
        api_root = ET.parse(APIS).getroot()
        api_classes = {c.get('name'):c for c in api_root.findall('class')}
        findings = []
        for kind in ('methods','fields'):
            for owner,name in refs[kind]:
                found = api_lookup(api_classes,owner,name,kind[:-1])
                findings.append({'kind':kind[:-1],'owner':owner,'name':name,'official_sdk':found,
                                 'above28':None if found is None else found['api'] > 28})
        write('attempt-1/dex-java-api-audit.json',findings)
        unknown = [f for f in findings if f['official_sdk'] is None]
        newer = [f for f in findings if f['above28']]
        write('attempt-1/dex-java-api-summary.json',{'unique_Java_members':len(findings),
            'above28':newer,'unresolved':unknown,'scope':'All emitted20 class references; not runtime reachability or execution',
            'record_java_type_in_dex':'java/lang/Record' in refs['types'],
            'streams_in_dex':[t for t in refs['types'] if t.startswith('java/util/stream/')],
            'source_stability':all(identity(ROOT/p)=={k:v for k,v in row.items() if k in ('bytes','sha256')}
                                   for p,row in source_map.items() if p.endswith('.java'))})
        # Preserve an exact finite official metadata excerpt; full SDK file identity is above.
        selected = ET.Element('api-excerpt',{'source':str(APIS),'source-sha256':identity(APIS)['sha256']})
        wanted = set(refs['types']) | {'java/util/Set','java/util/Collection','java/util/List','java/util/Map',
            'java/util/Collections','java/util/Arrays','java/util/stream/Stream','java/util/Map$Entry',
            'java/lang/Record','java/lang/Iterable'}
        def ancestors(name):
            node=api_classes.get(name)
            if node is None: return
            for tag in ('extends','implements'):
                for parent in node.findall(tag):
                    value=parent.get('name')
                    if value not in wanted: wanted.add(value); ancestors(value)
        for name in list(wanted): ancestors(name)
        for name in sorted(wanted):
            if name in api_classes: selected.append(api_classes[name])
        ET.indent(selected)
        (PACKET/'official-sdk-api-excerpt.xml').write_text(ET.tostring(selected,encoding='unicode')+'\n')
        host = scratch/'host';host.mkdir()
        run('compile-host-oracle',[JDK/'javac','--release','17','-g','-d',host,
            PACKET/'prototype/CollectionSnapshotsPrototype.java',PACKET/'prototype/CollectionContractOracle.java',
            PACKET/'inputs'/JAVA_DIR/'UiPacket.java',PACKET/'inputs'/JAVA_DIR/'Json.java',
            PACKET/'inputs'/JAVA_DIR/'OwnerLifecycleV2.java'])
        run('host-oracle',[JDK/'java','-ea','-cp',host,'dev.mixer.android.CollectionContractOracle'])
        # The prototype's library surface is audited separately from oracle calls to modern JDK factories.
        run('javap-prototype',[JDK/'javap','-classpath',host,'-v','-c','-p','dev.mixer.android.CollectionSnapshotsPrototype'])
        status = 'passed-source-prerequisite-evidence-only'
    finally:
        shutil.rmtree(scratch)
        write('attempt-1/commands.json',commands)
        write('attempt-1/receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'argv':sys.argv,'python':sys.version,'context_revision':CONTEXT,'context_revision_is_inherited_not_live_git':True,
            'status':status,'scope':'UNSELECTED source-only collections prerequisite, actual-source SDK/D8 audit and host oracle',
            'product_implementation_selected':False,'Android_API28_runtime_proved':False,'new_rendering_contexts_admitted':False,
            'cleanup':{'owned_children_reaped':all(row['owned_child_reaped'] for row in commands),
                'owned_scratch_removed':not scratch.exists(),'native_UI_capture_or_process_inventory':False},
            'new_dependencies':[],'pending':['root contract selection','independent review','product implementation and source-profile decision',
                'API28 native verifier/class loading/library runtime','old SDK editor/inset/accessibility behavior',
                'public V2 routing','TalkBack/design parity/final phones','separate-repository immutable FieldLog release','OTA/signing/store/operations/GA']})
    print(json.dumps({'status':status,'commands':len(commands),'packet':str(PACKET)},sort_keys=True))

if __name__ == '__main__': main()
