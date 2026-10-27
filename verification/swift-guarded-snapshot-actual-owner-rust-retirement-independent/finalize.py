"""Finalize receipts, explicit vector binding, owned cleanup and immutable seal."""
from pathlib import Path
import collections,datetime,hashlib,json,os,struct,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(x):return hashlib.sha256(x).hexdigest()
def digest(x):return sha(json.dumps(x,sort_keys=True,separators=(',',':')).encode())
def row(p,base=HERE):
    b=p.read_bytes();return dict(path=str(p.relative_to(base)),bytes=len(b),sha256=sha(b))
def rows(p):return [row(f,p) for f in sorted(p.rglob('*')) if f.is_file()]
def write(p,x):p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def verify(base,expected):
    assert sha((base/'seal.json').read_bytes())==expected
    d=json.loads((base/'seal.json').read_text());assert len(d['members'])==d['member_count'];assert digest(d['members'])==d['tree_sha256']
    for m in d['members']:assert row(base/m['path'],base)==m
    return dict(seal=row(base/'seal.json',ROOT),members=d['member_count'],bytes=d['member_bytes'],all_unchanged=True)
def decode_baseline(raw):
    limits=list(struct.unpack_from('<5Q',raw));extent=struct.unpack_from('<Q',raw,40)[0];d=dict(validation_budget=limits,source_extent=extent)
    for i,name in enumerate(['source','manifest','build','session','executable','nonce']):d[name]=raw[48+i*32:80+i*32].hex()
    d['identities']=[list(struct.unpack_from('<QQQQqqqq',raw,240+i*64)) for i in range(4)]
    return d
def main():
    roster=json.loads((HERE/'proposed-command-roster.json').read_text());commands=[];groups=[]
    for name in ['build-debug','build-debug-corrected','run-debug','build-opt2','run-opt2']:
        p=HERE/'commands'/name;r=json.loads((p/'receipt.json').read_text());plan=json.loads((p/'plan.json').read_text())
        assert r['exit']==(1 if name=='build-debug' else 0)
        assert r['reason'] is None and r['seconds']<=55
        assert all(r[k] for k in ['child_reaped','exact_owned_group_absent','source_unchanged','frozen_inputs_unchanged','review_inputs_unchanged','tool_unchanged'])
        assert row(p/'stdout')==r['stdout']|{'path':'commands/'+name+'/stdout'}
        assert row(p/'stderr')==r['stderr']|{'path':'commands/'+name+'/stderr'}
        try:os.killpg(r['owned_pgid'],0);raise AssertionError(('owned group still present',name))
        except ProcessLookupError:pass
        groups.append(dict(id=name,pid=r['owned_pid'],pgid=r['owned_pgid'],reaped=True,absent_now=True))
        commands.append(dict(id=name,receipt=row(p/'receipt.json'),plan=row(p/'plan.json'),exit=r['exit'],seconds=r['seconds'],kind=r['kind']))
    final_manifest=json.loads((HERE/'tested-source-manifest.json').read_text())
    assert rows(HERE/'source/vm')==final_manifest['members'];assert digest(rows(HERE/'source/vm'))==roster['source146_tree']
    prefix='INDEPENDENT_ACTUAL_PROVENANCE_BASELINE496 '
    baselines=[]
    for mode in ['debug','opt2']:
        output=(HERE/'commands'/('run-'+mode)/'stdout').read_text();stderr=(HERE/'commands'/('run-'+mode)/'stderr').read_text()
        assert 'running 31 tests' in output and '31 passed; 0 failed; 0 ignored;' in output
        assert output.count(' ... ok')==31
        assert 'independent_result_live_acquisition_retirement_v1 ... ok' in output
        assert 'INDEPENDENT_BINARY51 exact_frozen_bytes=51 strict_owner_mapped=7' in stderr
        assert 'INDEPENDENT_PROVENANCE230 vectors=230 optional_shapes=2 actual_cases=460' in stderr
        assert 'INDEPENDENT_READ12 exact_response_queues=12 no33rd_read=true' in stderr
        assert 'carrier_accessible_after_ledger_end=true' in stderr
        encoded=next(line[len(prefix):] for line in stderr.splitlines() if line.startswith(prefix));raw=bytes.fromhex(encoded);assert len(raw)==496;baselines.append(raw)
    assert baselines[0]==baselines[1]
    actual=decode_baseline(baselines[0]);frozen=json.loads((HERE/'frozen-oracles.json').read_text());mapping=json.loads((HERE/'provenance-vector-mapping.json').read_text())
    explicit=[]
    for m in mapping['mapping']:
        path=m['path'];v=actual[path[0]];delta=m['xor_delta_u64'];before=v
        if path[0] in ['source','manifest','build','session','executable','nonce']:
            frozen_before=bytes.fromhex(frozen['correlation_baseline'][path[0]]);frozen_after=bytes.fromhex(m['frozen_replacement'])
            after=bytes(x^(a^b) for x,a,b in zip(bytes.fromhex(v),frozen_before,frozen_after)).hex()
        elif len(path)==1:after=v^delta
        elif len(path)==2:before=v[path[1]];after=before^delta
        else:
            before=v[path[1]][path[2]];bits=(before&((1<<64)-1))^delta
            after=bits-(1<<64) if path[2]>=4 and bits>=(1<<63) else bits
        assert before!=after
        explicit.append(dict(id=m['id'],path=path,actual_before=before,actual_after=after,frozen_xor_delta_u64=delta))
    assert len(explicit)==230
    write(HERE/'executed-provenance-binding.json',dict(schema=1,actual_baseline_encoding496_hex=baselines[0].hex(),actual_baseline_encoding_sha256=sha(baselines[0]),
        actual_baseline=actual,frozen_baseline=frozen['correlation_baseline'],binding='Exact frozen changed bits XOR into privately derived actual baseline. All original absolute vectors retained. No proof minted from the parser-only frozen source.',
        same_in_Debug_opt2=True,count=230,executed_optional_shapes=[None,'Some original executable guard23'],cases_per_mode=460,mapping=explicit))
    custody=[]
    for name,expected in [
        ('swift-guarded-snapshot-actual-owner-rust-retirement-correction','46d811b1264770604106b061386e6eba01ea07e55590240eff722c36af4bcaa0'),
        ('swift-guarded-snapshot-actual-owner-rust-preaccess','050d4920ee51014748d0c62aec832c13a65bef09673fff41bbc62310635e4a66'),
        ('swift-guarded-snapshot-actual-owner-rust-independent','e9d55089795d317048040be973e518ff9ce841d7f39cb1449b930d7ae066990c'),
        ('swift-guarded-snapshot-actual-owner-rust-implementation','3592011c00794c12dcb76cecc41d4d2913e01a3d6e97612f3ce90f10cb4e5e23')]:
        custody.append(verify(ROOT/'verification'/name,expected))
    products=[]
    for name in ['tests-debug','tests-opt2']:
        p=HERE/'build'/name;products.append(row(p));p.unlink()
    assert not list((HERE/'build').iterdir());(HERE/'build').rmdir()
    write(HERE/'cleanup.json',dict(schema=1,command=sys.argv,python=sys.version,owned_pid_pgid_checks=groups,all_reaped_and_exact_groups_absent=True,
        removed_owned_generated=products,build_directory_absent=not (HERE/'build').exists(),no_global_inventory=True,no_unrelated_process_or_file_changes=True,
        native_fixture_UI_capture_processes_started=0,source_and_failure_and_command_outputs_retained=True))
    write(HERE/'final-custody.json',dict(schema=1,command=sys.argv,python=sys.version,frozen_packets=custody,final_tested_source146_tree=roster['source146_tree'],
        frozen_source146_tree=roster['frozen_source146_tree'],host11_tree=roster['host11_tree'],all_product_bytes_preserved_by_additive_test_patch=True,
        one_owned_source_tree=True,failed_harness_only_changed_source_and_exact_harness_retained='failed-harness-001',source_revision_attribution='Immutable released sources and exact patches/manifests; no contemporaneous Git HEAD claim.'))
    write(HERE/'command-summary.json',dict(schema=1,commands=commands,compiler_invocations=3,first_harness_failure=1,final_passing_builds=2,host_runs=2,
        production_MIR_recompiles=0,negative_recompiles=0,version_queries=0,toolchain=roster['toolchain'],version_attribution='Frozen producer -vV, exact rustc binary hash rechecked for every new build; no new version query.',
        methods_each=31,unchanged_producer_each=25,independent_each=6,all_owned_groups_absent=True))
    write(HERE/'disposition.json',dict(schema=1,status='frozen-independent-scoped-IR01-token-refund-repair-established-with-separate-root-result-lifetime-gap',
        candidate_seal_sha256=roster['frozen_seal_sha256'],frozen_source146_tree=roster['frozen_source146_tree'],tested_source146_tree=roster['source146_tree'],host11_tree=roster['host11_tree'],
        IR01='No Complete or whole-storage refund after any issued scope, including every matched/refused/extracted/forgotten/destroyed/unused outcome. Original witness unchanged and passes Retained. Scoped private core result on original live ledger.',
        IR02='Owned results may outlive acquisition owner and original ledger; actual facade signature compiled, actual generic-core escape executed. Full root/result charge lifetime remains open; current concrete outer returns only scalars after child destruction.',
        current_native_reachability='Pending startup/custody and always-refusing native healthy-retirement bridge; no reachable native escape or refund established.',
        evidence=dict(Debug='31/31',opt_level2='31/31',binary_exact=51,strict_owner_mapped_binary=7,provenance_exact_deltas=230,provenance_optional_shapes=2,actual_provenance_cases_each=460,read_schedules=12,
            full_MIR_items_verified=6207,selected_complete_MIR_bodies_reviewed=6,producer_negative_commands_reviewed=6),
        root_lifetime_full_ownership_accepted=False,useful_joint_retirement_accepted=False,old_or_new_prices_layouts_accepted=False,native_or_GA_accepted=False,
        production_policy_native_funding_layouts_prices_FieldLog_OTA_GA='Pending',scope='Only this verification packet written; no product/other-packet/metadata/Git changes.'))
    members=[row(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='seal.json']
    seal=dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='frozen-independent-review',members=members,member_count=len(members),member_bytes=sum(x['bytes'] for x in members),tree_sha256=digest(members),
        source146_tree=roster['frozen_source146_tree'],tested_source146_tree=roster['source146_tree'],IR01_scoped_token_refund_repair=True,IR02_root_result_lifetime_open=True,GA_native_funding_or_full_ownership_accepted=False)
    write(HERE/'seal.json',seal)
    print(json.dumps(dict(seal=row(HERE/'seal.json'),members=len(members),member_bytes=seal['member_bytes'],source146=roster['frozen_source146_tree'],tested_source146=roster['source146_tree'],IR01='scoped repair verified',IR02='root-result lifetime open',all_commands_terminal_and_clean=True)))
if __name__=='__main__':main()
