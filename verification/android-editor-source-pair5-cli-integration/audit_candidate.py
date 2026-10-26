"""Offline source/consumer/ELF audit; no native execution or process inventory."""
import hashlib,json,os,pathlib,re,shutil
HERE=pathlib.Path(__file__).resolve().parent;PROFILE=json.loads((HERE/'inputs/profile5.json').read_text());SOURCE=HERE/'source';ROWS=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def row(p):return {'path':str(p.relative_to(HERE)),'bytes':p.stat().st_size,'sha256':sha(p)}
def files(root):
    out=[]
    for base,dirs,names in os.walk(root):
        dirs[:]=sorted(d for d in dirs if not d.startswith('.build') and d not in ['.mixer','.swiftpm','__pycache__','.git'])
        for name in sorted(names):
            p=pathlib.Path(base)/name
            assert not p.is_symlink(),p
            out.append(p)
    return sorted(out)
def projection(mapping):return hashlib.sha256(''.join(p+'\0'+mapping[p]['sha256']+'\n' for p in sorted(mapping)).encode()).hexdigest()
assert len(PROFILE['sdk_files'])==22 and len(PROFILE['adapter_files'])==24
assert len([p for p in PROFILE['adapter_files'] if p.endswith('.java')])==18
for kind,root in [('sdk',SOURCE/'sdk'),('adapter',SOURCE/'native/android')]:
    for relative,identity in PROFILE[kind+'_files'].items():
        path=root/('engine/'+relative if kind=='adapter' and relative.startswith('Sources/') else relative)
        assert path.stat().st_size==identity['bytes'] and sha(path)==identity['sha256'],path
    assert projection(PROFILE[kind+'_files'])==PROFILE[kind+'_compatibility_sha256']
consumers={}
for root in sorted((HERE/'consumers').iterdir()):
    if not root.is_dir():continue
    for kind in ['sdk','adapter']:
        directory=root/('Generated/MixerSDK' if kind=='sdk' else 'Generated/MixerAndroid')
        for relative,identity in PROFILE[kind+'_files'].items():
            path=directory/relative
            assert path.stat().st_size==identity['bytes'] and sha(path)==identity['sha256'],path
    java=list((root/'Generated/MixerAndroid/app/src').rglob('*.java'))
    assert len(java)==18
    assert not any(p.name in ['AppearanceDescriptorV1.java','AppearanceResolutionV1.java','AdapterInstrumentation.java'] for p in java)
    descriptor=root/'Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json'
    assert descriptor.stat().st_size==9587 and sha(descriptor)==PROFILE['default_descriptor']['sha256']
    consumers[root.name]=[row(p) for p in files(root)]
# Relocation and two ordinary CLI exports preserve every application/source byte.
a={str(p.relative_to(HERE/'consumers/PairFiveConsumer')):sha(p) for p in files(HERE/'consumers/PairFiveConsumer')}
for name in ['RelocatedConsumer','RoundTripConsumer']:
    b={str(p.relative_to(HERE/'consumers'/name)):sha(p) for p in files(HERE/'consumers'/name)}
    assert a==b,name
ART=pathlib.Path.home()/'.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android'
RUNTIME=ART/'swift-resources/usr/lib/swift-aarch64/android';NDK=ART/'android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64'
elf=[]
for context in ["generated", "relocated"]:
    for config in ['debug','release']:
        for kind in ['','jni-']:
            log=(HERE/'evidence'/f'{"relocated-" if context=="relocated" else ""}generated-app-{config}-{kind}readelf.log').read_text()
            assert 'ELF64' in log and 'AArch64' in log
            symbols=(HERE/'evidence'/f'{"relocated-" if context=="relocated" else ""}generated-app-{config}-{kind}symbols.log').read_text()
            expected=['Java_dev_mixer_android_NativeBridge_'+s for s in ['create','exchange','destroy','prepareV2','commitV2','abortV2']] if kind else ['mixer_android_'+s for s in ['create','exchange','destroy','prepare_v2','commit_v2','abort_v2']]+['AppFeatures','AppModels']
            assert all(symbol in symbols for symbol in expected)
            needed=re.findall(r'\(NEEDED\).*\[([^\]]+)\]',log)
            resolved=[]
            for name in needed:
                if name in ['libc.so','libdl.so','libm.so','liblog.so','libandroid.so']:
                    resolved.append({'name':name,'kind':'Android-system-contract'});continue
                candidate=HERE/f'scratch/{"relocated-" if context=="relocated" else ""}app-{config}/aarch64-unknown-linux-android28/{config}'/name
                if not candidate.is_file(): candidate=RUNTIME/name
                if not candidate.is_file(): candidate=NDK/'sysroot/usr/lib/aarch64-linux-android'/name
                assert candidate.is_file(),name
                resolved.append({'name':name,'path':str(candidate),'bytes':candidate.stat().st_size,'sha256':sha(candidate)})
            elf.append({'context':context,'configuration':config,'kind':'JNI' if kind else 'app-owned-Swift','needed':needed,'resolved':resolved,'architecture':'ELF64 AArch64','required_symbols':expected})
classes=sorted((HERE/'scratch/java-classes').rglob('*.class'))
assert classes and not any(p.name.startswith(('AppearanceDescriptorV1','AppearanceResolutionV1','AdapterInstrumentation')) for p in classes)
(HERE/'source-manifest.json').write_text(json.dumps({'schema':1,'members':[row(p) for p in files(SOURCE)]},indent=2)+'\n')
(HERE/'consumer-and-elf-audit.json').write_text(json.dumps({'schema':1,'sdk_projection':projection(PROFILE['sdk_files']),'adapter_projection':projection(PROFILE['adapter_files']),'sdk_members':22,'adapter_members':24,'java_subjects':18,'consumers':consumers,'exact_relocated_exports':True,'elf':elf,'emitted_classes':[row(p) for p in classes]},indent=2)+'\n')
print(json.dumps({'source_members':len(files(SOURCE)),'consumer_roots':list(consumers),'java_subjects':18,'emitted_classes':len(classes),'ELF_audits':len(elf)}))
