#!/usr/bin/env python3
"""Join independent actual receipts, close source scope and seal this append lane."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

P=Path(__file__).absolute().parent
ROOT=P.parents[2]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((P/name).read_bytes())
def write(name,data):(P/name).write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')


def verify_seal(directory,expected):
    assert sha(directory/'seal.json')==expected
    data=json.loads((directory/'seal.json').read_bytes())
    for x in data['members']:
        p=directory/x['path'];assert not p.is_symlink()
        assert p.stat().st_size==x['bytes'] and sha(p)==x['sha256'],str(p)
    return {'members':len(data['members']),'bytes':sum(x['bytes'] for x in data['members']),'seal_sha256':expected}


def main():
    assert not (P/'seal.json').exists()
    commands=read('commands.json');layout_commands=read('layout-commands.json')
    assert len(commands['commands'])==86 and len(layout_commands['commands'])==6
    for r in commands['commands']+layout_commands['commands']:
        assert r['exit_code']==0 and not r['timed_out'] and r['owned_child_reaped']
        e=r['environment']['fixed'];assert e['TMPDIR']==e['TMP']==e['TEMP']
        assert str(P/'scratch/tmp') in e['TMPDIR'] and '..' not in Path(e['TMPDIR']).parts
        assert e['RUSTUP_AUTO_INSTALL']=='0' and e['CARGO_NET_OFFLINE']=='true'
        for stream in ['stdout','stderr']:
            f=P/'logs'/f'{r["name"]}.{stream}'
            assert f.stat().st_size==r[stream]['bytes'] and sha(f)==r[stream]['sha256']
    diagnostics={}; measured={}; positives={}
    producer_warning=read('candidate/inherited-warning-inventory.json')
    fixture_manifest=json.loads((P.parent/'fixture-manifest.json').read_bytes())
    for mode in ['debug','optimized']:
        exact=read('qualification-exact-'+mode+'.json');ind=read('qualification-independent-'+mode+'.json')
        assert (exact['passed'],exact['compiler_total'],exact['filtered'],exact['ignored'])==(17,403,386,0)
        assert (ind['passed'],ind['compiler_total'],ind['filtered'],ind['ignored'])==(5,408,403,0)
        bridge=read('bridge-independent-'+mode+'.json')
        assert bridge['count']==len(bridge['cases'])==34 and len({x['name'] for x in bridge['cases']})==34
        assert all(x['all_authority_false'] for x in bridge['cases'])
        stdout=(P/'logs'/f'tests-independent-{mode}.stdout').read_text()
        line=next(x for x in stdout.splitlines() if 'INDEPENDENT_LAYOUT ' in x)
        measured[mode]={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)}
        rows=re.findall(r'INDEPENDENT_ROWS name=([^ ]+) rows=(\d+) bytes=(\d+) attempts=(\d+) imported=(\d+) defined=(\d+) types=(\d+) allocation_attempts=(\d+)',stdout)
        wanted=[c for c in fixture_manifest['cases'] if 'expected_body' in c]
        assert len(rows)==len(wanted)==3
        positives[mode]=[]
        for values,c in zip(rows,wanted):
            name,*numbers=values
            assert name==c['id'] and list(map(int,numbers))==[80000,2560000,625,34,c['defined'],c['types'],0]
            f=P/'artifacts'/('independent-'+mode)/f'independent-{name}.rows'
            assert sha(f)==c['expected_body_sha256']
            positives[mode].append({'name':name,'defined':c['defined'],'types':c['types'],'rows':80000,
                'File_bytes':2560000,'sha256':sha(f),'actual_owner_validated':True,'allocation_attempts_observed':0})
        text=(P/'logs'/f'fixture-library-{mode}.stderr').read_text()
        rows=[{'message':m.group(1),'source':m.group(2),'line':int(m.group(3)),'column':int(m.group(4))}
            for m in re.finditer(r'^warning: ([^\n]+)\n\s*--> ([^\n]+):(\d+):(\d+)',text,re.M)]
        assert len(rows)==producer_warning[mode]['count']==148
        assert [(x['message'],x['line'],x['column']) for x in rows]==[(x['message'],x['line'],x['column']) for x in producer_warning[mode]['entries']]
        assert {Path(x['source']).name for x in rows}=={'cache_state.rs'}
        assert (P/'logs'/f'strict-bridge-{mode}.stderr').read_bytes()==b''
        library=next(r for r in commands['commands'] if r['name']=='fixture-library-'+mode)
        assert '--crate-type=lib' in library['argv'] and '--edition=2021' in library['argv']
        assert not any(x.startswith(('-D','-A','--deny','--allow')) for x in library['argv'])
        strict=next(r for r in commands['commands'] if r['name']=='strict-bridge-'+mode)
        assert '-Dwarnings' in strict['argv']
        diagnostics[mode]={'normal_unsuppressed_library_warnings':rows,'warning_count':148,
            'new_bridge_warnings':0,'new_adapter_warning_policy':'scoped deny(warnings) with documented isolated allow(dead_code)',
            'inherited_VM_test_warnings':'2 dropping_copy_types outside new module; retained'}
    assert measured['debug']==measured['optimized']
    assert measured['debug']['validation_result']==664 and measured['debug']['caller_constructor_and_owner']==1328
    closure=read('complete-result-layouts.json')['measured'];assert closure['debug']==closure['optimized']
    assert closure['debug']['metadata_profile_result']==closure['debug']['metadata_control']==152
    for name in ['scalar_usize_result','scalar_u64_result','descriptor_result','usize_control','u64_control','descriptor_control','row_control','unit_control','unit_result']:
        assert closure['debug'][name]==40
    assert closure['debug']['residual_result']==32 and closure['debug']['writer_control']==72
    write('diagnostic-audit.json',diagnostics)
    write('actual-independent-fixture-observations.json',positives)
    source=P/'candidate/source/vm'
    selected=ROOT/'verification/swift-cache-state-profile-adapter-preparation-independent/additional-validator-inputs'
    validator=[]
    for name in ['src/experimental/swift.rs','src/experimental/policy.rs','src/experimental/metadata.rs',
                 'src/experimental/descriptors.rs','src/experimental/reader.rs','src/experimental/validate.rs',
                 'src/experimental/account.rs','src/experimental/mod.rs','src/experimental_wasi/mod.rs']:
        assert sha(source/name)==sha(selected/name)
        validator.append({'path':name,'sha256':sha(source/name),'selected_snapshot_sha256':sha(selected/name)})
    write('validator-selected-closure.json',{'nine_shared_validator_sources_exact':validator,
        'wasi_descriptor_also_exact':sha(source/'src/experimental_wasi/descriptor.rs'),
        'cache_control_differences_not_inherited_as_runtime_or_construction_acceptance':True,
        'closure_scope':'complete copied Cargo.toml/Cargo.lock/src/tests Rust crate, not byte-complete archived132 distribution',
        'archived_drift_not_qualified':['borrowed.rs','cache.rs','control.rs','cache_tests.rs'],
        'archived_include_headers_outside_this_compilation_closure':True})
    additions=[('observation_return_and_argument_all3',432),('lookup_and_span_source_chain',512),
        ('policy_return_argument_discriminant',32),('both_source_getter_sites',96),
        ('all_progress_and_error_closure_captures',128),('range_and_stepby_construction_returns',40)]
    base=read('candidate/accounting.json')['conservative_whole_union_bytes'];assert base==7504
    assert sum(v for _,v in additions)==1240
    transfer_bank=4*(16*40+152);assert transfer_bank==3168
    adapter_union=base+sum(v for _,v in additions)+transfer_bank;assert adapter_union==11912
    constructor_owner=3*measured['debug']['snapshot'];assert constructor_owner==1992
    combined=adapter_union+constructor_owner;assert combined==13904
    work=[('row_and_nested_source',4096,80000),('LE_encoding',256,80000),('row_induction',128,80000),
        ('block_induction',128,625),('write_classification',512,20000),('one_buffer_zero',4096,1),
        ('fixed_wrapper_admission_finish',8192,1),('requested_IO_byte_extent',4096,20000)]
    assert sum(b*n for _,b,n in work)==450652288
    write('independent-accounting.json',{'adapter_source_sha256':sha(source/'src/experimental_swift_reactor/diagnostic_profile.rs'),
        'measured_layouts':measured,'measured_complete_Result_ControlFlow_residual':closure,
        'producer_per_place_base_bytes':base,'explicit_additional_places':[{'name':n,'bytes':b} for n,b in additions],
        'all17_full_expression_transfer_banks_bytes':transfer_bank,'complete_adapter_caller_callee_union_bytes':adapter_union,
        'constructor_Result_owner_return_and_caller_snapshot_whole_sum':constructor_owner,
        'combined_conservative_fixed_source_place_sum':combined,
        'source_work':[{'item':n,'allowance':b,'multiplicity':count,'bound':b*count} for n,b,count in work],
        'source_action_and_requested_byte_bound':450652288,
        'units_not_VM_credits_or_CPU_instructions':True,'new_engine_reservation_or_cap':False,
        'separate':['snapshot retained source <=64MiB','metadata <=16MiB','validation scratch <=1MiB',
            'caller input visible bytes/allocation capacities','code/static literal image','standard-library/kernel internals',
            'arbitrary test support and unrelated caller allocations','future real caller/reservation/result/ledger join'],
        'lifetime_and_per_function_proof':'SOURCE_REVIEW.md'})
    # Bind predeclared obligations to actual method/case evidence without making
    # unreachable or unchanged upstream paths into runtime passes.
    expected=json.loads((P.parent/'review-roster.json').read_bytes())['obligations'];bindings=[]
    exact_names=read('qualification-exact-debug.json')['selected_names'];ind_names=read('qualification-independent-debug.json')['selected_names']
    def find(suffix):return next(x for x in exact_names+ind_names if x.endswith('::'+suffix))
    for obligation in expected:
        item={'id':obligation['id'],'modes':['debug','optimized']}
        kind=obligation['kind'];short=obligation['id'].split(':',1)[1]
        if kind=='writer':
            item.update({'status':'actual selected private loop, injected callback plus physical File proof',
                'method':find('independent_predeclared_writer_matrix_and_physical_files'),'case':short})
        elif kind=='rows':
            method='independent_invalid_wasm_never_constructs_owner' if short=='invalid-wasm-no-owner' else 'independent_all_rows_real_owners_and_file_bytes'
            item.update({'status':'actual owner and byte comparison; source-only seal/defensive invariant where appropriate','method':find(method)})
        elif kind=='file':
            if short in ('metadata-error-applicability','position-error-applicability'):
                item.update({'status':'source-only; safe actual syscall fault not injected','proof':'SOURCE_REVIEW.md'})
            else:
                method='independent_predeclared_writer_matrix_and_physical_files' if short in ('retained-partial-bytes','error-side-effects-no-rollback') else 'independent_all_rows_real_owners_and_file_bytes' if short=='fresh-empty-regular-full-bytes' else 'independent_actual_file_admission_and_readonly_failure'
                item.update({'status':'actual File; exact fixed error/content assertions','method':find(method)})
        elif kind=='source-proof':
            item.update({'status':'full source/lifetime/accounting proof plus measured compiler layouts','proof':'SOURCE_REVIEW.md',
                'layout_method':find('independent_full_constructor_result_and_source_view_layouts'),
                'complete_generic_layouts':'complete-result-layouts.json'})
        else:
            names=[x['name'] for x in read('bridge-independent-debug.json')['cases']]
            exact='independent-'+short
            if exact in names:item.update({'status':'actual applicable bridge invocation','invocation':exact})
            elif short=='late-footer-drift-output-fault':item.update({'status':'late footer actually run; concurrent drift/report-output failure unchanged upstream and not newly qualified','invocation':'selected-late_footer_invalid'})
            else:item.update({'status':'actual bridge roster/source/provenance and diagnostics join','evidence':['bridge-independent-debug.json','bridge-independent-optimized.json','diagnostic-audit.json','SOURCE_REVIEW.md']})
        bindings.append(item)
    assert len(bindings)==80
    write('review-obligation-dispositions.json',{'count':80,'obligations_not_method_count':True,'bindings':bindings,
        'no_source_only_or_unchanged_upstream_path_credited_as_runtime_pass':True})
    # Final source identity and cleanup checks are independent of HEAD changes.
    from replay import tree
    assert tree(source)['tree_sha256']=='d65ea46493da772cdbf15c3f00da366feb43113c52104079147449c0aa9789cf'
    assert tree(P/'derivative/vm')==read('derivative-source.json')['derivative_tree']
    assert tree(P/'layout-closure/vm')==read('layout-closure-contract.json')['source']
    producer=verify_seal(ROOT/'verification/swift-cache-state-profile-adapter','472dc4fcffbca9718c9b7c47ced3586170ffd9ab1dbf7185b07e3b4cd2ff87a3')
    preaccess=verify_seal(P.parent,'e55e941159b42477e6cae3c615c3f86faf8d7cd397dc90f84934e9a33373b30e')
    assert not (P/'scratch').exists() and not (P/'hostile/INVOKED').exists()
    assert read('cleanup.json')['owned_scratch_removed'] and read('layout-cleanup.json')['scratch_removed']
    assert not any(x.name=='__pycache__' for x in P.rglob('*'))
    write('postflight.json',{'at':datetime.now(timezone.utc).isoformat(),'producer_unchanged':producer,'preaccess_unchanged':preaccess,
        'all_three_source_copies_exact_to_frozen_base_or_declared_test_only_derivative':True,
        'scratch_removed_products_inventoried':True,'hostile_sentinels_unchanged':True,'no_active_host_command_owned':True})
    write('decision.json',{'schema':1,'at':datetime.now(timezone.utc).isoformat(),
        'recommendation':'root may accept the isolated host-only profile row-body prerequisite without a product change, using this complete independent proof',
        'root_acceptance_or_canonical_integration_performed':False,'product_change_required':False,
        'source_tree_sha256':'d65ea46493da772cdbf15c3f00da366feb43113c52104079147449c0aa9789cf',
        'adapter_sha256':sha(source/'src/experimental_swift_reactor/diagnostic_profile.rs'),
        'host':'Rust1.99.0 aarch64-apple-darwin macOS host only',
        'fresh_behavioral_commands':86,'additional_targeted_layout_commands':6,
        'selected_methods_each_mode':17,'independent_behavior_methods_each_mode':5,'additional_layout_methods_each_mode':1,
        'selected_bridge_calls_each_mode':16,'additional_independent_bridge_calls_each_mode':18,
        'actual_independent_positive_owners_each_mode':3,'actual_no_owner_refusals_each_mode':5,
        'writer_schedules_with_actual_physical_File_comparison_each_mode':29,
        'all_authority_getters_false':True,'all_new_runtime_checks_passed':True,
        'adapter_caller_callee_union_bytes':adapter_union,'combined_with_constructor_owner_fixed_places_bytes':combined,
        'source_action_and_requested_byte_bound':450652288,
        'producer_7504_and_97301024_not_accepted_as_complete_independent_totals':True,
        'authoring_failures_retained':['custody-authoring-failure.json','failed-attempt-1/failure.json'],
        'prior_failures_not_counted_as_fresh_success':True,'cleanup_complete':True,
        'limits':['defensive sealed-owner faults and metadata/position syscall failures source-only',
            'write faults use actual private source loop and callbacks; not every fault arose from kernel File.write',
            'synthetic header/configuration/context; collusive import/tail row/event actually synthetically admissible',
            'phase-only stream does not perform body identity join','late footer exercised; concurrent drift/report-output failure not newly qualified',
            'acknowledged bytes do not establish physical rollback, durability, fsync, digest or immutable custody',
            'logical source places/actions exclude code image, library/kernel internals, arbitrary callers; not stack/RSS/CPU or VM debit',
            'actual constructor/source/metadata/validation limits separate; future callers need fresh reservation/lifetime join',
            'documented isolated dead_code allowance; inherited diagnostics retained without global suppression',
            'test supervisor trusted quiescent host support, not adversarial CLI/filesystem custody',
            'copied Rust crate closure is not archived132 distribution equivalence; three include headers outside Rust compilation and disclosed borrowed/cache/control/cache_tests drift remain separate',
            'no new Rust1.98.1/Linux/CI qualification, native/UI/capture/process/Git/full-target/full103pack',
            'real header/cache/layout binding, original typed result/final ledger/custody/runtime/semantic metrics/published FieldLog/GA remain unqualified']})
    members=[{'path':str(f.relative_to(P)),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(P.rglob('*')) if f.is_file() and f.name!='seal.json']
    write('seal.json',{'schema':1,'phase':'independent-actual-source-review','members':members,'member_count':len(members),
        'total_bytes':sum(x['bytes'] for x in members),'tree_sha256':hashlib.sha256(''.join(f"{x['path']}\t{x['bytes']}\t{x['sha256']}\n" for x in members).encode()).hexdigest(),
        'seal_excludes_only_itself':True,'all_listed_members_now_immutable':True})
    print(json.dumps({'seal_sha256':sha(P/'seal.json'),'members':len(members),'bytes':sum(x['bytes'] for x in members),
        'decision_sha256':sha(P/'decision.json'),'adapter_union_bytes':adapter_union,'combined_fixed_bytes':combined,
        'source_action_and_requested_byte_bound':450652288}))


if __name__=='__main__':main()
