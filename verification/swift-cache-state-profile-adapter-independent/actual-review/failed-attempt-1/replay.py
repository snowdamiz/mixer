#!/usr/bin/env python3
"""Replay frozen source and independent controls; no live source or Git access."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import signal
import struct
import sys
import types
import supervisor as S

P=S.P
NAMESPACE='experimental_swift_reactor::diagnostic_profile::diagnostic_profile_tests::'
INDEPENDENT='experimental_swift_reactor::diagnostic_profile::independent_profile_tests::'
INDEPENDENT_NAMES=sorted(INDEPENDENT+x for x in [
    'independent_all_rows_real_owners_and_file_bytes',
    'independent_invalid_wasm_never_constructs_owner',
    'independent_actual_file_admission_and_readonly_failure',
    'independent_predeclared_writer_matrix_and_physical_files',
    'independent_full_constructor_result_and_source_view_layouts'])


def tree(base):
    rows=[{'path':str(p.relative_to(base)),'bytes':p.stat().st_size,'sha256':S.sha(p)}
        for p in sorted(base.rglob('*')) if p.is_file()]
    return {'members':rows,'member_count':len(rows),'bytes':sum(x['bytes'] for x in rows),
        'tree_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()}


def write(name,data):
    (P/name).write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')


def prepare():
    base=P/'candidate/source/vm'
    assert tree(base)['tree_sha256']=='d65ea46493da772cdbf15c3f00da366feb43113c52104079147449c0aa9789cf'
    derivative=P/'derivative/vm'
    shutil.copytree(base,derivative)
    newtest=derivative/'src/experimental_swift_reactor/independent_profile_tests.rs'
    shutil.copy2(P/'independent_profile_tests.rs',newtest)
    adapter=derivative/'src/experimental_swift_reactor/diagnostic_profile.rs'
    suffix=b'\n#[cfg(test)]\n#[path = "independent_profile_tests.rs"]\nmod independent_profile_tests;\n'
    adapter.write_bytes(adapter.read_bytes()+suffix)
    write('derivative-source.json',{'base_tree':tree(base),'derivative_tree':tree(derivative),
        'only_changes':['src/experimental_swift_reactor/diagnostic_profile.rs appended fixed cfg(test) declaration',str(newtest.relative_to(derivative))],
        'suffix_hex':suffix.hex(),'independent_test_sha256':S.sha(P/'independent_profile_tests.rs'),
        'frozen_before_compilation':True,'independent_names':INDEPENDENT_NAMES})
    cases=json.loads((P.parent/'writer-cases.json').read_bytes())['cases']
    lines=[]
    def actions(seq):
        return ','.join({'interrupted':'I','remaining':'R','error':'E','zero':'Z','overreport':'O','forbidden33':'F'}.get(a[0],f'B:{a[1]}' if len(a)>1 else 'INVALID') for a in seq)
    for c in cases:
        e=c['expected']; side=c['scripted_physical_expected']['bytes'] if c['physical_fault'] else 0
        lines += ['\t'.join(map(str,['CASE',c['id'],e['code'],e['output_bytes'],e['output_attempts'],side])),
                  'DEFAULT\t'+actions(c['default_block_actions'])]
        for block,seq in sorted(c['block_overrides'].items(),key=lambda x:int(x[0])):
            lines.append(f'OVERRIDE\t{block}\t'+actions(seq))
    (P/'writer-matrix.tsv').write_text('\n'.join(lines)+'\n')
    write('execution-contract.json',{'at':datetime.now(timezone.utc).isoformat(),'source_authority':'frozen member hashes, no HEAD inference',
        'base_namespace':json.loads((P/'candidate/required-tests.json').read_bytes()),
        'independent_names':INDEPENDENT_NAMES,'bridge_roster':json.loads((P/'candidate/required-bridge.json').read_bytes()),
        'writer_matrix_sha256':S.sha(P/'writer-matrix.tsv'),'per_child_seconds':60,'global_active_seconds':600,'cleanup_seconds':60,
        'environment':'hostile inherited Rust/test/TMP sentinels injected then scrubbed; owned TMPDIR=TMP=TEMP, offline existing Rust1.99',
        'no_new_cap_or_native_or_Git':True})


def compile_vm(mode,derivative=False):
    base=P/('derivative/vm' if derivative else 'candidate/source/vm')
    label=('independent-' if derivative else 'exact-')+mode
    argv=[S.RUST/'cargo','test','--offline','--manifest-path',base/'Cargo.toml','--features','experimental-swift-reactor','--lib','--no-run']
    if mode=='optimized':argv.insert(3,'--release')
    S.run('compile-'+label,argv)
    directory='release' if mode=='optimized' else 'debug'
    # Cargo's fresh artifact must match this selected source, not an old binary.
    files=[p for p in (P/'scratch/cargo-target'/directory/'deps').glob('mixer_vm-*') if p.is_file() and p.suffix=='']
    assert len(files)==1,files
    binary=files[0]
    raw,_=S.run('list-'+label,[binary,'--list'])
    names=[line[:-6] for line in raw.splitlines() if line.endswith(': test')]
    assert names and len(names)==len(set(names))
    expected=json.loads((P/'candidate/required-tests.json').read_bytes())['methods']
    assert sorted(n for n in names if n.startswith(NAMESPACE))==expected
    assert sorted(n for n in names if n.startswith(INDEPENDENT))==(INDEPENDENT_NAMES if derivative else [])
    assert len(names)==403+(len(INDEPENDENT_NAMES) if derivative else 0)
    prefix=INDEPENDENT if derivative else NAMESPACE
    selected=INDEPENDENT_NAMES if derivative else expected
    artifacts=P/'artifacts'/label;artifacts.mkdir(parents=True,exist_ok=False)
    if derivative:shutil.copy2(P/'writer-matrix.tsv',artifacts/'writer-matrix.tsv')
    raw,_=S.run('tests-'+label,[binary,prefix,'--nocapture','--test-threads=1'],
        {'MIXER_PROFILE_EVIDENCE_DIR':artifacts,'MIXER_PROFILE_INDEPENDENT_FIXTURES':P.parent/'fixtures'})
    summary=re.search(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;',raw)
    assert summary and list(map(int,summary.groups()))==[len(selected),0,0,0,len(names)-len(selected)]
    executed=re.findall(r'^test ('+re.escape(prefix)+r'\w+) \.\.\.',raw,re.M)
    assert sorted(executed)==selected
    for n in selected:
        assert n in names
    result={'mode':mode,'derivative':derivative,'source_tree':tree(base)['tree_sha256'],
        'compiler_total':len(names),'selected_names':selected,'passed':len(selected),'failed':0,'ignored':0,
        'filtered':len(names)-len(selected),'binary_sha256':S.sha(binary),'artifact_dir':str(artifacts.relative_to(P))}
    if derivative:
        matrix=re.findall(r'INDEPENDENT_MATRIX name=([^ ]+) code=(\d+) stage=(\d+) offset=(\d+) bytes=(\d+) attempts=(\d+) physical=(\d+)',raw)
        wanted=json.loads((P.parent/'writer-cases.json').read_bytes())['cases']
        assert len(matrix)==len(wanted)==29
        for values,c in zip(matrix,wanted):
            name,*numbers=values; e=c['expected']
            assert name==c['id'] and list(map(int,numbers))==[e['code'],e['stage'],e['offset'],e['output_bytes'],e['output_attempts'],c['scripted_physical_expected']['bytes']]
            assert S.sha(artifacts/f'matrix-{name}.bin')==c['scripted_physical_expected']['sha256']
        for c in json.loads((P.parent/'fixture-manifest.json').read_bytes())['cases']:
            if 'expected_body' in c:
                assert S.sha(artifacts/f'independent-{c["id"]}.rows')==c['expected_body_sha256']
        result['exact_writer_schedules']=29;result['actual_positive_owners']=3;result['no_owner_refusals']=5
        result['physical_output_files_independently_hashed']=29
    write('qualification-'+label+'.json',result)
    return artifacts


def bridge_functions():
    # Import only a frozen copied encoder with a stub supervisor. No child starts.
    stub=types.ModuleType('run_command');stub.P=P;stub.run=lambda *a,**k: (_ for _ in ()).throw(AssertionError('producer supervisor forbidden'))
    sys.modules['run_command']=stub
    spec=importlib.util.spec_from_file_location('frozen_bridge_encoder',P/'candidate/qualify_bridge.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def run_bridge(mode, exact_artifacts, independent_artifacts):
    encoder=bridge_functions()
    library=P/'scratch'/f'libmixer_cache_fixture-{mode}.rlib'
    args=[S.RUST/'rustc','--edition=2021','--crate-name','mixer_cache_fixture','--crate-type=lib',P/'candidate/closed-fixture-source/analyzer.rs','-o',library]
    if mode=='optimized':args.insert(2,'-O')
    S.run('fixture-library-'+mode,args)
    binary=P/'scratch'/f'bridge-{mode}.bin'
    args=[S.RUST/'rustc','--edition=2021','-Dwarnings',P/'candidate/bridge.rs','--extern',f'mixer_cache_fixture={library}','-o',binary]
    if mode=='optimized':args.insert(2,'-O')
    S.run('strict-bridge-'+mode,args)
    calls=[]
    def invoke(name,stream,profile,context,expected,provenance):
        base=P/'artifacts'/('bridge-'+mode);base.mkdir(exist_ok=True)
        paths=[]; identities=[]
        for key,data in [('stream',stream),('profile',profile),('context',context)]:
            path=base/(name+'-'+key+'.bin');path.write_bytes(data);paths.append(path)
            identities.append({'kind':key,'bytes':len(data),'sha256':S.sha(path)})
        report=base/(name+'-report.bin')
        stdout,_=S.run('bridge-'+mode+'-'+name,[binary,*paths,report,*expected,name])
        assert 'authority=false' in stdout and report.stat().st_size==49152
        calls.append({'name':name,'expected':expected,'inputs':identities,'source_provenance':provenance,
            'report_sha256':S.sha(report),'all_authority_false':True})
    meta=json.loads((exact_artifacts/'actual-module.json').read_bytes());body=(exact_artifacts/'actual-rows.bin').read_bytes()
    # Replay the producer's exact 16 distinct invocation definitions in both modes.
    for name in json.loads((P/'candidate/required-bridge.json').read_bytes())['invocations']:
        kinds=[13] if name=='phase_closed' else [1,2,3,4,5,9,10,11,12,13]
        if name=='failure14_unavailable':kinds=[1,14,13]
        stream,profile,context=encoder.encode(meta,body,[encoder.record(k,meta) for k in kinds],name=='cap_unknown_tail')
        expected=('ClosedFixtureObserved','Observed');row=512+35*32
        if name=='row_type_mismatch':struct.pack_into('<I',profile,row+4,128)
        elif name=='row_offset_mismatch':struct.pack_into('<Q',profile,row+8,meta['second_offset']+1)
        elif name=='row_length_mismatch':struct.pack_into('<Q',profile,row+16,1)
        elif name=='row_defined_zero':profile[row:row+32]=struct.pack('<IIQQQ',0,(1<<32)-1,(1<<64)-1,0,0)
        elif name=='row_defined_two':struct.pack_into('<I',profile,row,2)
        elif name=='import_sentinel_type':struct.pack_into('<I',profile,512+4,0)
        elif name=='tail_sentinel_offset':struct.pack_into('<Q',profile,512+79999*32+8,0)
        elif name=='row_reserved_nonzero':struct.pack_into('<Q',profile,row+24,1)
        elif name in ['record_import','record_tail','equal_body_other_offset']:
            if name=='record_import':struct.pack_into('<Q',stream,512+128+48,0)
            elif name=='record_tail':struct.pack_into('<Q',stream,512+128+48,79999)
            else:struct.pack_into('<Q',stream,512+128+56,meta['second_offset']+3)
        elif name=='failure14_unavailable':expected=('ApplicabilityUnavailable','FailureApplicability')
        elif name=='cap_unknown_tail':expected=('CapCutUnknownTail','Observed')
        elif name=='late_footer_invalid':stream[-512]=0
        if name not in ['phase_closed','miss_build_publish_release','failure14_unavailable','cap_unknown_tail']:expected=('Unavailable','FramingInvalid')
        invoke('selected-'+name,stream,profile,context,expected,'actual producer-test validator owner; synthetic context/header')
    # Independent fixture rows, byte patches and declared applicability.
    body=(independent_artifacts/'independent-minimum-abi29.rows').read_bytes()
    expected_body=(P.parent/'fixtures/minimum-abi29.expected-row-body.bin').read_bytes()
    assert body==expected_body
    row34=struct.unpack_from('<IIQQQ',body,34*32)
    meta={'source_extent':(P.parent/'fixtures/minimum-abi29.wasm').stat().st_size,'second_offset':row34[2]}
    def encode_independent(body, function=34, phase=False):
        events=[encoder.record(k,meta,function) for k in ([13] if phase else [1,2,3,4,5,9,10,11,12,13])]
        for r in events:
            if r[7]!=(1<<64)-1:r[9]=34
        stream,profile,context=encoder.encode(meta,body,events)
        struct.pack_into('<Q',profile,6*8,36);struct.pack_into('<Q',context,7*8,36)
        return stream,profile,context
    invoke('independent-owner-body-positive',*encode_independent(body),('ClosedFixtureObserved','Observed'),'independent Wasm actual owner; all80000bytes matched independent oracle; synthetic header/context')
    patches=json.loads((P.parent/'row-patches.json').read_bytes())['cases']
    for c in patches:
        mutation=bytearray(body);off=c['raw_row_body_offset'];after=bytes.fromhex(c['replacement_hex'])
        assert mutation[off:off+len(after)]==bytes.fromhex(c['before_hex'])
        mutation[off:off+len(after)]=after
        assert hashlib.sha256(mutation).hexdigest()==c['mutated_row_body_sha256']
        collusive=c['expected_disposition']=='independent-owner-row-comparison-refusal'
        function=c['row'] if collusive else 34
        expected=('ClosedFixtureObserved','Observed') if collusive else ('Unavailable','FramingInvalid')
        invoke('independent-'+c['id'],*encode_independent(mutation,function),expected,
            'independent row oracle mismatch; '+('collusive synthetic event intentionally may pass; no owner-provenance authority' if collusive else c['applicability']))
    c=next(c for c in patches if c['id']=='different-in-range-type')
    mutation=bytearray(body);off=c['raw_row_body_offset'];mutation[off:off+4]=bytes.fromhex(c['replacement_hex'])
    invoke('independent-phase-only-no-body-join',*encode_independent(mutation,phase=True),('ClosedFixtureObserved','Observed'),'phase-only control: no body join expected; actual-owner byte comparison still refuses mutation')
    assert len(calls)==34 and len({c['name'] for c in calls})==34
    write('bridge-independent-'+mode+'.json',{'mode':mode,'count':len(calls),'selected_count':16,
        'additional_independent_count':18,'cases':calls,'all_authority_false':True,
        'normal_fixture_library_diagnostics_no_suppression':True,'new_bridge_strict_warnings':True})


def main():
    prepare();S.begin()
    try:
        S.run('rustc-identity',[S.RUST/'rustc','-vV'])
        S.run('cargo-identity',[S.RUST/'cargo','--version'])
        for mode in ['debug','optimized']:
            exact=compile_vm(mode)
            independent=compile_vm(mode,True)
            run_bridge(mode,exact,independent)
    finally:
        S.summary()
        # One terminal retention deadline; on expiry preserve recoverable scratch.
        import time
        class TerminalCleanupExpired(BaseException):
            pass
        def expired(_signal,_frame):
            raise TerminalCleanupExpired('terminal independent cleanup deadline')
        signal.signal(signal.SIGALRM,expired)
        signal.setitimer(signal.ITIMER_REAL,min(60,max(0.01,660-(time.monotonic()-S.START))))
        try:
            products=tree(P/'scratch')
            write('products-before-cleanup.json',products)
            shutil.rmtree(P/'scratch')
            write('cleanup.json',{'at':datetime.now(timezone.utc).isoformat(),'owned_scratch_removed':not (P/'scratch').exists(),
                'owned_children_reaped':all(r['owned_child_reaped'] for r in S.RECORDS),
                'retained_physical_Files_and_reports':True,'hostile_sentinel_unchanged':not (P/'hostile/INVOKED').exists(),
                'product_inventory':'products-before-cleanup.json','producer_and_preaccess_sources_not_mutated':True})
        except TerminalCleanupExpired:
            write('cleanup-expired.json',{'recoverable_scratch_retained':True,'further_cleanup_attempted':False})
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':
    main()
