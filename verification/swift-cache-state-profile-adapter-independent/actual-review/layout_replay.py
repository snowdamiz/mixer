#!/usr/bin/env python3
"""One bounded, test-only layout closure; not another behavioral suite."""
import hashlib,json,re,shutil,signal,time
from pathlib import Path
import supervisor as S
from replay import tree,write
P=S.P
PREFIX='experimental_swift_reactor::diagnostic_profile::independent_result_layout_tests::'
NAME=PREFIX+'complete_scalar_descriptor_metadata_results_and_try_places'


def main():
    base=P/'layout-closure/vm';shutil.copytree(P/'candidate/source/vm',base)
    shutil.copy2(P/'independent_result_layout_tests.rs',base/'src/experimental_swift_reactor/independent_result_layout_tests.rs')
    f=base/'src/experimental_swift_reactor/diagnostic_profile.rs'
    suffix=b'\n#[cfg(test)]\n#[path = "independent_result_layout_tests.rs"]\nmod independent_result_layout_tests;\n'
    f.write_bytes(f.read_bytes()+suffix)
    before=tree(base)
    write('layout-closure-contract.json',{'source':before,'only_cfg_test_append':suffix.hex(),'method':NAME,
        'compiler_total_each_mode':404,'selected':1,'filtered':403,'per_child_seconds':60,
        'global_active_seconds':600,'cleanup_seconds':60,'role':'close previously unmeasured complete source-expression layouts only'})
    S.begin();results={}
    try:
        for mode in ['debug','optimized']:
            argv=[S.RUST/'cargo','test','--offline','--manifest-path',base/'Cargo.toml','--features','experimental-swift-reactor','--lib','--no-run']
            if mode=='optimized':argv.insert(3,'--release')
            S.run('compile-layout-'+mode,argv)
            directory='release' if mode=='optimized' else 'debug'
            binaries=[p for p in (P/'scratch/cargo-target-exact'/directory/'deps').glob('mixer_vm-*') if p.is_file() and p.suffix=='']
            assert len(binaries)==1
            binary=binaries[0]
            raw,_=S.run('list-layout-'+mode,[binary,'--list'])
            names=[line[:-6] for line in raw.splitlines() if line.endswith(': test')]
            assert len(names)==len(set(names))==404 and [x for x in names if x.startswith(PREFIX)]==[NAME]
            raw,_=S.run('test-layout-'+mode,[binary,NAME,'--exact','--nocapture','--test-threads=1'])
            assert '1 passed; 0 failed; 0 ignored; 0 measured; 403 filtered out;' in raw
            line=next(x for x in raw.splitlines() if 'RESULT_CLOSURE ' in x)
            results[mode]={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)}
        assert results['debug']==results['optimized']
        assert tree(base)==before
        write('complete-result-layouts.json',{'measured':results,'methods_each_mode':1,'compiler_total':404,'filtered':403,
            'base_producer_source_unchanged':True,'derivative_tree':before['tree_sha256']})
    finally:
        write('layout-commands.json',{'commands':S.RECORDS,'elapsed_seconds':time.monotonic()-S.START,
            'per_child_seconds':60,'global_active_seconds':600,'cleanup_seconds':60})
        class TerminalCleanupExpired(BaseException):pass
        def expired(_signal,_frame):raise TerminalCleanupExpired()
        signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,min(60,max(0.01,660-(time.monotonic()-S.START))))
        try:
            write('layout-products-before-cleanup.json',tree(P/'scratch'))
            shutil.rmtree(P/'scratch')
            write('layout-cleanup.json',{'scratch_removed':not (P/'scratch').exists(),
                'all_owned_children_reaped':all(r['owned_child_reaped'] for r in S.RECORDS),
                'hostile_sentinel_unchanged':not (P/'hostile/INVOKED').exists(),'products_hashed_before_remove':True})
        except TerminalCleanupExpired:
            write('layout-cleanup-expired.json',{'recoverable_scratch_retained':True});raise
        finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':main()
