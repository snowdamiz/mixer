#!/usr/bin/env python3
"""Bounded external public checks and exact-base derived counter executable."""
import datetime,difflib,hashlib,json,os,re,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OWNER=ROOT/'experimental-capability-runtime/verification/2026-10-23-enable-deadline-candidate-1'
PIN='9e754a25364c5751e209be1f6f535300d435fee01328e0cbaf87ee097bd4940f'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(value,message):
    if not value:raise RuntimeError(message)
def main():
    out=HERE/'2026-10-23-targeted';out.mkdir(exist_ok=False)
    work=HERE/'.build/targeted';work.mkdir(parents=True,exist_ok=False)
    owner=json.loads((OWNER/'receipt.json').read_text());source=Path(owner['frozenSourceExport']);stage=Path(owner['stageRoot']);snapshot=source.parent
    require(owner['sourceManifestSHA256']==PIN and sha(OWNER/'source-manifest.sha256')==PIN and len(owner['source'])==72,'frozen 72-source candidate1')
    repair_path=ROOT/'verification/capability-enable-deadline/consumer-repair-1/receipt.json';repair=json.loads(repair_path.read_text());fixed=Path(repair['source_export'])
    require(repair['base_sha256']==sha(OWNER/'receipt.json'),'repair exact base receipt')
    require(set(repair['source'])==set(owner['source']) and [name for name,d in owner['source'].items() if repair['source'][name]!=d]==[repair['changed_fixture']],'repair changes one consumer fixture only')
    def unchanged():
        for name,digest in owner['source'].items():require(sha(source/name)==digest,'immutable base '+name)
        for name,digest in repair['source'].items():require(sha(fixed/name)==digest and sha(ROOT/name)==digest,'fixed immutable/live '+name)
    unchanged()
    inputs={name:sha(HERE/name) for name in ['Fixture.swift','PublicProbe.swift','DerivedHooks.swift','DerivedProbe.swift','default-import.swift','run.py']}
    for name in inputs:(work/name).write_bytes((HERE/name).read_bytes())
    native=stage/'host/lib/libmixer_vm_capability_experimental.a'
    require(sha(native)=='a015ff65980422dd0b9c5cad2e28741d1e5ba478e0f657dcaedf75477d553b72','qualified native archive')
    derived=work/'derived';derived.mkdir();base={};patch=[]
    prefix='experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/'
    for name,digest in owner['source'].items():
        if name.startswith(prefix) and name.endswith('.swift'):
            path=derived/Path(name).name;path.write_bytes((source/name).read_bytes());base[Path(name).name]=digest
    edits=[
        ('Native.swift','    func enable() throws {\n        var report','    func enable() throws {\n        EnableReviewHooks.beforeNativeEnable()\n        var report'),
        ('Ownership.swift','            if accepted { signal() }','            if accepted { EnableReviewHooks.commandAdmitted(); signal() }'),
        ('Lifecycle.swift','        Task.detached { [self, host, nativeOwner] in\n            if let host','        Task.detached { [self, host, nativeOwner] in\n            EnableReviewHooks.cleanupEntered()\n            if let host')]
    for name,before,after in edits:
        path=derived/name;old=path.read_text();require(old.count(before)==1,'unique derived anchor '+name);new=old.replace(before,after);path.write_text(new);patch.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='base/'+name,tofile='derived/'+name))
    (out/'test-only.patch').write_text(''.join(patch))
    mapping={str(p.relative_to(work)):sha(p) for p in sorted(work.rglob('*.swift'))}
    receipt=dict(status='running',started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_manifest_sha256=PIN,base_source=owner['source'],base_export=str(source),
        owner_base_receipt=dict(path=str((OWNER/'receipt.json').relative_to(ROOT)),sha256=sha(OWNER/'receipt.json')),repaired_consumer_receipt=dict(path=str(repair_path.relative_to(ROOT)),sha256=sha(repair_path)),
        original_inputs=inputs,derived_module_originals=base,test_only_edits=edits,test_only_patch_sha256=sha(out/'test-only.patch'),derived_source=mapping,source_export=str(work),
        native_archive=dict(path=str(native),sha256=sha(native)),commands=[],libraries={},binaries={},driver_sha256=sha(Path(__file__)),
        scope='Original external public SPI tests plus labelled derived executable module from exact seven frozen runtime files with C-enable-entry/command-admission/cleanup-entry counters, real native/KV work, no package/Rust rebuild.',
        limitations=['Counter is immediately before C enable; no C enable/result/exit is fabricated','Derived private stale-handle faults intentionally violate public ownership and run in isolated subprocesses','Normal-close versus deadline race remains sampled cooperative; no atomic normal-close priority or hard real-time guarantee','Retained Swift/SDK/native products are reused; broader35x3 and cross evidence remain owner qualification','No devices, authority, durable updater, actual health, production or publication'])
    def save():(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'}
    def run(name,argv,expected=0,fragment=None,timeout=60):
        unchanged();began=time.monotonic()
        try:r=subprocess.run(argv,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);raw,code=r.stdout,r.returncode
        except subprocess.TimeoutExpired as error:raw,code=(error.stdout or b'')+b'\ntargeted timeout\n',124
        log=out/(name+'.log');log.write_bytes(raw);row=dict(name=name,argv=argv,cwd=str(source),environment={'DEVELOPER_DIR':env['DEVELOPER_DIR']},exit_code=code,expected_exit=expected,seconds=time.monotonic()-began,timeout_seconds=timeout,log=str(log.relative_to(ROOT)),sha256=sha(log))
        receipt['commands'].append(row);save();require(code==expected,name+' unexpected exit '+str(code))
        if fragment:require(fragment.encode() in raw,name+' expected output')
        count=re.search(rb'passed (\d+) checks',raw)
        if count:row['passed_checks']=int(count[1]);save()
        unchanged();print(name+': '+str(code),flush=True)
    save()
    try:
        run('swift-version',['swift','--version'])
        for mode,configuration in [('debug','Debug'),('release','Release')]:
            products=snapshot/mode/('out/Products/'+configuration);maps=snapshot/mode/'out/Intermediates.noindex/GeneratedModuleMaps'
            library=products/'libMixerExperimentalCapabilityRuntime.a';require(library.exists(),'retained '+mode+' library')
            receipt['libraries'][mode]=dict(path=str(library),sha256=sha(library));save()
            common=['swiftc','-parse-as-library','-swift-version','6','-warnings-as-errors','-I',str(products)]
            for name in ['MixerCapabilityIO','CMixerVMCapability']:common+=['-Xcc','-fmodule-map-file='+str(maps/(name+'.modulemap'))]
            common+=['-Xcc','-I'+str(stage/'host/include')]
            if mode=='release':common+=['-O']
            link=['-L',str(products),'-lMixerExperimentalCapabilityRuntime','-L',str(stage/'host/lib'),'-lmixer_vm_capability_experimental']
            binary=work/('public-'+mode)
            run(mode+'-public-link',common+link+[str(work/'Fixture.swift'),str(work/'PublicProbe.swift'),'-o',str(binary)])
            run(mode+'-public-run',[str(binary)],fragment='public owned-enable review passed 14 checks',timeout=30)
            receipt['binaries']['public-'+mode]=dict(path=str(binary),sha256=sha(binary));save()
            if mode=='debug':run('ordinary-import-opacity',common+['-typecheck',str(work/'default-import.swift')],expected=1,fragment='inaccessible')
            binary=work/('derived-'+mode)
            run(mode+'-derived-link',common+['-module-name','MixerEnableDeadlineReview']+link+[str(p) for p in sorted(derived.glob('*.swift'))]+[str(work/name) for name in ['Fixture.swift','DerivedHooks.swift','DerivedProbe.swift']]+['-o',str(binary)])
            for case in ['queued-expiry','future-and-legacy','checked-failure-first','deadline-first']:
                run(mode+'-'+case,[str(binary),case],fragment='derived owned-enable review '+case+' passed',timeout=30)
            receipt['binaries']['derived-'+mode]=dict(path=str(binary),sha256=sha(binary));save()
            require(sha(library)==receipt['libraries'][mode]['sha256'],'retained library unchanged after link')
        for name,digest in mapping.items():require(sha(work/name)==digest,'derived capture unchanged')
        for name,digest in inputs.items():require(sha(HERE/name)==digest,'original input unchanged')
        require(sha(native)==receipt['native_archive']['sha256'],'native archive unchanged')
        receipt.update(status='targeted public and derived Debug/Release checks passed',source_and_artifacts_unchanged=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    except Exception as error:receipt.update(status='failed targeted review check preserved',problem=str(error));save();raise
    save();print('receipt_sha256 '+sha(out/'receipt.json'))
if __name__=='__main__':main()
