"""Bounded source custody, Python design controls, ordinary-production compile probes."""
import hashlib,json,os,pathlib,re,shutil,subprocess,sys,tempfile,time
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent.parent
PRODUCER=HERE.parent/'swift-guarded-snapshot-export-preparation'
ACCEPTED=PRODUCER/'inputs/accepted-source/vm'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,data): p.write_text(json.dumps(data,indent=2)+'\n')
def command(name,argv,cwd,timeout=60):
    folder=HERE/'commands'/name; folder.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    env={k:v for k,v in os.environ.items() if not k.startswith('MIXER_LOADER_')}
    try:
        p=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,timeout=timeout,check=False)
        out,err,code=p.stdout,p.stderr,p.returncode
    except subprocess.TimeoutExpired as e:
        out,err,code=e.stdout or b'',e.stderr or b'',-999
    (folder/'stdout').write_bytes(out); (folder/'stderr').write_bytes(err)
    receipt=dict(argv=argv,cwd=str(cwd),exit_code=code,elapsed_seconds=time.monotonic()-started,
        timeout_seconds=timeout,child_reaped=True,stdout_sha256=digest(folder/'stdout'),stderr_sha256=digest(folder/'stderr'))
    dump(folder/'receipt.json',receipt)
    return receipt,out.decode(errors='replace'),err.decode(errors='replace')

def main():
    refs=[('swift-guarded-snapshot-export-preparation','7787c8bbd9164ebdd360186f79c5d696739e89d6b08cd2f7cfbc71e9c156a1fe'),
        ('swift-guarded-snapshot-export-contract-independent','be091218c0c8c47f66c83ac39cded51012c942e7e91d9660b1b25985243401e1'),
        ('swift-guarded-snapshot-export-accounting-review','c638a996d2fa1f54c62f739758c5219f23439541b249e480b0084d1038112068'),
        ('swift-guarded-snapshot-export-binding-review','7d3faabd2f930d2daac9865f27dbbb3bc9a661097e6a7834584a93d0527b1cf0')]
    custody=[]
    for name,expected in refs:
        base=HERE.parent/name; seal=base/'seal.json'
        assert digest(seal)==expected,(name,digest(seal))
        s=json.loads(seal.read_text()); total=0
        for member in s['members']:
            p=base/member['path']; assert p.is_file() and p.stat().st_size==member['bytes'] and digest(p)==member['sha256']
            total+=p.stat().st_size
        assert len(s['members'])==s['member_count'] and total==s['bytes']
        custody.append(dict(path=str(base.relative_to(ROOT)),seal_sha256=expected,members=len(s['members']),bytes=total))
    source=json.loads((PRODUCER/'inputs/source-manifest.json').read_text())
    dump(HERE/'input-custody.json',dict(refs=custody,accepted_source_manifest_sha256=digest(PRODUCER/'inputs/source-manifest.json'),
        accepted_tree='9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb',
        revision_context='606c42876855897c315ee279dcd38fabaeb561ad',producer_or_peer_commands_replayed=False))
    rustc=shutil.which('rustc') or '/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc'
    assert pathlib.Path(rustc).is_file()
    versions={}
    for name,argv in [('python-version',[sys.executable,'--version']),('rustc-version',[rustc,'--version','--verbose'])]:
        receipt,out,err=command(name,argv,HERE); assert receipt['exit_code']==0
        versions[name]=out+err
    receipt,out,err=command('python-controls',[sys.executable,'-B',str(HERE/'controls.py')],HERE)
    assert receipt['exit_code']==0,err
    model=json.loads(out); dump(HERE/'controls-result.json',model)
    scratch=pathlib.Path(tempfile.mkdtemp(prefix='bounded-compile-',dir=HERE))
    results=[]
    try:
        tree=scratch/'source'; shutil.copytree(ACCEPTED,tree)
        additions=[('control_append.rs','src/experimental_swift_reactor/control.rs'),
            ('initial_append.rs','src/experimental_swift_reactor/cache/initial_profile_v1.rs'),
            ('wasi_append.rs','src/experimental_wasi/accounted.rs')]
        original_hashes=[]
        for added,member in additions:
            p=tree/member; original_hashes.append(dict(path=member,sha256=digest(p)))
            p.write_bytes(p.read_bytes()+b'\n'+(HERE/'prototype'/added).read_bytes())
        compiled=[dict(path=str(p.relative_to(tree)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(tree.rglob('*')) if p.is_file()]
        dump(HERE/'compile-source-manifest.json',dict(members=compiled,original_changed_member_hashes=original_hashes,prototype_only=True))
        for name,opt in [('debug','0'),('optimized','3')]:
            ll=scratch/(name+'.ll'); rmeta=scratch/(name+'.rmeta')
            argv=[rustc,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','--crate-type','lib',
                '--emit',f'metadata={rmeta},llvm-ir={ll}','-C','overflow-checks=yes','-C',f'opt-level={opt}']
            for feature in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:
                argv+=['--cfg',f'feature="{feature}"']
            argv+=[str(tree/'src/lib.rs')]
            receipt,out,err=command('compile-'+name,argv,HERE)
            assert receipt['exit_code']==0,err
            definition=next(line for line in ll.read_text().splitlines() if line.startswith('@MIXER_ADMISSION_DESIGN_LAYOUT_PROBE'))
            (HERE/'commands'/('compile-'+name)/'layout-llvm.txt').write_text(definition+'\n')
            # LLVM uses a byte-string constant; decode the exact little-endian target words.
            encoded=re.search(r'c"(.*?)"',definition)
            assert encoded,definition
            raw=bytearray(); value=encoded.group(1); i=0
            while i<len(value):
                if value[i]=='\\': raw.append(int(value[i+1:i+3],16)); i+=3
                else: raw.append(ord(value[i])); i+=1
            assert len(raw)==18*8
            words=[int.from_bytes(raw[i:i+8],'little') for i in range(0,len(raw),8)]
            results.append(dict(mode=name,layout_words=words,ordinary_production_cfg=True,
                rustc_llvm_probe_only=True,no_test_or_host_cfg=True))
        assert results[0]['layout_words']==results[1]['layout_words']
        # Actual guard control type is immutable: verify the only attempted ledger mutation refuses.
        p=tree/'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
        p.write_text(p.read_text()+'''\nfn proposal_forbidden_guard_funding(initial:&InitialProfileBorrowV1<'_>) {\n let _=initial.control.proposal_debit_snapshot_work_v1(1);\n}\n''')
        argv=argv[:-1]+[str(tree/'src/lib.rs'),'--error-format=json']
        receipt,out,err=command('negative-guard-ledger-mutation',argv,HERE)
        errors=[]
        for line in err.splitlines():
            try: d=json.loads(line)
            except json.JSONDecodeError: continue
            if d.get('level')=='error' and d.get('code'): errors.append(d['code']['code'])
        assert receipt['exit_code']!=0 and errors==['E0596'],(errors,err)
        dump(HERE/'compile-result.json',dict(status='passed bounded proposal compile probes',layouts=results,negative_errors=errors,
            limitations='Native compiler constants for proposed types; not actual exporter source places, full foundation admission, all-8 wrapper behavior or runtime tests.'))
    finally:
        shutil.rmtree(scratch)
        dump(HERE/'cleanup.json',dict(scratch_removed=not scratch.exists(),compiler_children_reaped=True,
            native_ui_capture_simulator_emulator_started=False,process_inventory_performed=False,
            unrelated_processes_changed=False,canonical_or_git_changes=False))
    dump(HERE/'receipt.json',dict(python=sys.version,versions=versions,runner_sha256=digest(pathlib.Path(__file__)),
        controls_sha256=digest(HERE/'controls.py'),input_custody_sha256=digest(HERE/'input-custody.json'),
        scope='fresh bounded host Python controls + ordinary-production compiler proposal probes; no full exporter',status='passed'))
    print(json.dumps(dict(status='passed',groups=len(model['groups']),layouts=results),indent=2))

if __name__=='__main__': main()
