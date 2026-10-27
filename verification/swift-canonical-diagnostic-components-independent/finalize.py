#!/usr/bin/env python3
"""Close the independent review after commands terminate and evidence agrees."""
import json
from pathlib import Path
import re
import shutil
import review as r

def main():
    records=[]
    for path in sorted((r.OUT/'commands').glob('*/receipt.json')):
        row=json.loads(path.read_text())
        assert row['expected_exit_observed'] and row['owned_group_absent'] and row['direct_child_reaped'],path
        assert not row['TMPDIR_final_entries'],path
        records.append(row)
    expected={'rustc-version','cargo-version','python-version','host-uname','host-sw-vers',
              'debug-full-reactor-library','release-full-reactor-library','private-probe-library-build',
              'public-validator-positive','codec-private-negative','row-private-negative'}
    expected.update(f'{name}-{mode}-{step}' for name in ['scalar-boundaries','fixture-ownership']
                    for mode in ['debug','release'] for step in ['compile','execute'])
    assert {row['name'] for row in records}==expected
    assert len(records)==19
    test_results=[]
    library_method_sets=[]
    allowed_privacy={'positive','private_cache','private_parts','private_control','proof_forge','proof_clone',
                     'legacy_conversion','mutable_source','proof_reuse','view_mutation','view_release','pin_clone','pin_forge'}
    fixture_cleanups=[]
    for mode in ['debug','release']:
        name=f'{mode}-full-reactor-library'
        row=next(row for row in records if row['name']==name)
        text=(r.OUT/'commands'/name/'stdout').read_text()
        summary=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;',text)
        assert summary==[('430','0','0','0','0')],summary
        methods=[s[5:-7] for s in text.splitlines() if s.startswith('test ') and s.endswith(' ... ok')]
        assert len(methods)==430
        codec=[s for s in methods if '::diagnostic_result_v1::tests::' in s]
        rows=[s for s in methods if '::diagnostic_profile::diagnostic_profile_tests::' in s]
        assert len(codec)==27 and len(rows)==17
        library_method_sets.append(set(methods))
        test_results.append({'mode':mode,'command':name,'passed':430,'failed':0,'ignored':0,'filtered':0,
                             'codec_methods':len(codec),'row_methods':len(rows),
                             'elapsed_seconds':row['elapsed_seconds']})
        leftovers=row['TMPDIR_entries_before_supervisor_cleanup']
        assert len(leftovers)==1 and re.fullmatch(fr'mixer-cache-privacy-\d+-{mode}',leftovers[0]),leftovers
        files=row['TMPDIR_file_manifest']
        observed={Path(f['path']).name for f in files}
        assert observed=={name+'.rs' for name in allowed_privacy}|{'libpositive.rmeta'},observed
        assert all(Path(f['path']).parts[0]==leftovers[0] and len(Path(f['path']).parts)==2 for f in files)
        assert len(row['known_inherited_privacy_fixture_removed'])==1
        fixture_cleanups.append({'mode':mode,'known_inherited_privacy_directory':leftovers[0],
                                 'expected_fixture_files_verified':len(files),
                                 'row_RAII_directories_remaining':0,'TMPDIR_final_entries':[]})
    assert library_method_sets[0]==library_method_sets[1]
    for mode in ['debug','release']:
        scalar=(r.OUT/'commands'/f'scalar-boundaries-{mode}-execute'/'stdout').read_text()
        assert 'cases=68256 checked_bytes=11221632 unaligned_cases=59724 tail_cases=58320 fewer_words_cases=24544 excess_words_cases=41280' in scalar
        fixture=(r.OUT/'commands'/f'fixture-ownership-{mode}-execute'/'stdout').read_text()
        assert 'collision_skip=pass create_new_preservation=pass normal_cleanup=pass unwind_cleanup=pass unowned_sentinel_preserved=pass' in fixture
    for name in ['codec-private-negative','row-private-negative']:
        stderr=(r.OUT/'commands'/name/'stderr').read_text()
        assert 'E0603' in stderr and 'is private' in stderr
    before=json.loads((r.OUT/'canonical-preimage.json').read_text())
    after=r.manifest(r.ROOT,before['members'])
    frozen=r.manifest(r.SOURCE,before['members'])
    assert before==after==frozen
    r.write(r.OUT/'canonical-postimage.json',after)
    # Source inspection is descriptive scope evidence, never release admission.
    lib=(r.SOURCE/'vm/src/lib.rs').read_text()
    module=(r.SOURCE/'vm/src/experimental_swift_reactor/mod.rs').read_text()
    assert '#[cfg(feature = "experimental-swift-reactor")]\npub mod experimental_swift_reactor;' in lib
    assert '\nmod diagnostic_profile;' in module and '\nmod diagnostic_result_v1;' in module
    for name in ['diagnostic_profile','diagnostic_result_v1']:
        assert f'pub mod {name};' not in module
    r.write(r.OUT/'source-review.json',{
        'schema':1,'five_file_scope':'private codec, original row helper, their tests and private module declarations',
        'codec_delta':'Only the documented Rust1.99 chunks_exact_mut-to-as_chunks_mut iterator lint repair',
        'row_implementation_and_codec_tests':'byte-identical to directly hashed accepted sources',
        'row_tests':'same 17 methods; fresh guard declared before File in all five file tests; path substitutions only outside the guard implementation',
        'fixture_review':{'atomic_create_dir':'already-existing paths are skipped without removal',
                          'fresh_file':'create_new(true) refuses collisions',
                          'drop_order':'File locals are declared after directory guard and close first on ordinary and unwinding scope exit',
                          'allocation_measurements':'guard construction and file creation remain outside measured write intervals',
                          'observed_new_fixture_cleanup':'zero row directories after full suites and direct normal/unwind checks'},
        'feature_scope':'existing nondefault experimental-swift-reactor gate; no Cargo or dependency changes',
        'private_visibility':'two fresh external E0603 refusals plus public validator positive control',
        'production_references':'new modules are declared privately; implementations referenced only inside the modules and their tests',
        'semantic_scope':'unverified codec data and acknowledged finite File writes; no source reference is operational admission',
        'release_admission_from_syntax':False,'selected_loader_or_adoption_added':False,
        'snapshot_writer_added_or_executed':False,'public_route_added':False,
        'production_publication_or_credentials_or_git_mutation':False})
    scratch_files=[p for p in r.SCRATCH.rglob('*') if p.is_file()]
    scratch_bytes=sum(p.stat().st_size for p in scratch_files)
    assert r.SCRATCH.parent==r.OUT and not r.SCRATCH.is_symlink()
    shutil.rmtree(r.SCRATCH)
    assert not r.SCRATCH.exists()
    r.write(r.OUT/'cleanup.json',{'schema':1,'at':r.now(),
        'all_19_direct_children_reaped':True,'all_19_owned_process_groups_absent':True,
        'signal_actions':[{'name':row['name'],'actions':row['owned_group_cleanup_actions']} for row in records if row['owned_group_cleanup_actions']],
        'full_library_fixture_cleanup':fixture_cleanups,
        'all_command_TMPDIRs_final_empty':True,
        'owned_scratch_removed':str(r.SCRATCH),'scratch_files_removed':len(scratch_files),'scratch_bytes_removed':scratch_bytes,
        'scratch_absent_after_cleanup':True,'cleanup_scope':'Only this packet owned scratch and Python bytecode cache',
        'global_process_inventory':False,'unrelated_processes_or_project_data_touched':False,
        'mobile_native_UI_capture_simulator_emulator_started':False})
    result={'schema':1,'at':r.now(),'status':'independent-bounded-host-review-pass',
        'reviewer':'/root/swift_canonical_diagnostic_independent',
        'producer_seal_sha256':r.EXPECTED_SEAL,'root_release_sha256':r.EXPECTED_RELEASE,
        'canonical_source_members':136,'canonical_pre_post_and_copy_tree_sha256':r.EXPECTED_TREE,
        'source_bytes_unchanged':True,'canonical_source_or_git_mutations':False,
        'library_tests':test_results,'distinct_library_methods':430,'library_method_executions':860,
        'extra_scalar_boundaries':{'modes':['debug','optimized'],'cases_per_mode':68256,'compared_bytes_per_mode':11221632,
                                   'actual_exact_function_sha256':'8563b9e51a4cc4fe7f98fbe75c1341d071aabe75ef6ad80c40f2e95f3e711abb',
                                   'oracle':'independent scalar word index and shifts; validates whole backing slice and unchanged tails'},
        'extra_fixture_checks':{'modes':['debug','optimized'],'collision_skip':True,'create_new_preservation':True,
                                'normal_cleanup':True,'unwind_cleanup':True,'preexisting_collision_sentinel_preserved':True,
                                'caught_panics':'intentional fixture create_new collision and explicit unwind; both caught and asserted'},
        'privacy':{'positive_external_control':1,'negative_external_E0603_controls':2,'library_features':'experimental-swift-reactor'},
        'commands':[{'name':row['name'],'exit_code':row['exit_code'],'expected_exit':row['expected_exit'],
                     'elapsed_seconds':row['elapsed_seconds'],'receipt':f"commands/{row['name']}/receipt.json"} for row in records],
        'tools':{name:(r.OUT/'commands'/name/'stdout').read_text().strip() for name in ['rustc-version','cargo-version','python-version','host-uname','host-sw-vers']},
        'unexpected_command_failures':0,'expected_negative_compiler_controls':2,
        'inherited_compiler_warnings':'two dropping_copy_types warnings in unchanged control_operations_tests.rs:1619,1643 in both library builds',
        'producer_runner_replayed':False,
        'not_verified':['integration targets','all feature combinations','Linux','canonical CI after delivery',
                        'native simulator/emulator or physical devices (paused)','UI or capture (paused)',
                        'selected loader/adoption or snapshot writer integration','operational storage/work admission',
                        'published separate-repository FieldLog packages','OTA/store/customer acceptance','GA'],
        'operational_admission':False,'canonical_acceptance_decision':'root-owned','GA_accepted':False}
    r.write(r.OUT/'result.json',result)
    (r.OUT/'README.md').write_text(f'''# Independent canonical diagnostic component review

Bounded host review passes for the private codec, original finite row helper, their tests and private module declarations. Root retains canonical acceptance and delivery ownership.

The root release hash is `{r.EXPECTED_RELEASE}`. The producer seal `{r.EXPECTED_SEAL}` independently matches all 92 members and 300,960 bytes. All 136 canonical compilation inputs match `{r.EXPECTED_TREE}` before and after the review and match the read-only source copy used by every command. Source custody and directly generated accepted-source diffs are retained. No producer runner was executed.

Direct source comparison finds the disclosed one-line Rust1.99 chunk-iterator repair in the codec, byte-identical row implementation and codec tests, and the per-test RAII fixture/path adaptation in the row suite. Removing the two new private module blocks reconstructs the attributed 639-byte module preimage exactly. New modules remain under the existing nondefault reactor feature, with no public route, dependency, selected loader/adoption or snapshot writer addition.

Fresh Rust/Cargo1.99.0 aarch64-apple-darwin library tests pass in debug and release: **430 methods per mode, 860 executions, zero failures, ignores or filters**, including all 27 codec and 17 row methods. Commands use `cargo test --lib --offline --locked --features experimental-swift-reactor -- --test-threads=1` with the release flag added for the optimized run. This covers all library methods enabled by that feature; integration targets and additional feature combinations remain for canonical CI. Both builds report only the two inherited `dropping_copy_types` warnings in unchanged `control_operations_tests.rs`.

The exact extracted `write_words` helper independently passes 68,256 cases and 11,221,632 byte comparisons per mode against scalar indexing and bit shifts. Cases cover 59,724 unaligned slices, 58,320 incomplete tails, 24,544 fewer-word inputs, 41,280 excess-word inputs, empty inputs, fixed wire-size boundaries and full prefix/suffix preservation. The probe does not substitute a model implementation for the candidate helper.

The exact extracted `OwnedDirectory` implementation independently passes collision skipping, create_new preservation, normal reverse-drop cleanup and unwind cleanup in both modes while preserving an existing collision sentinel. The two intentional panic paths are caught and asserted. All five canonical File tests create their guard before File locals and keep fixture allocation outside measured writer intervals. Both complete library runs leave no row RAII directories. The inherited cache privacy test retains one known owned probe directory with exactly 13 Rust probe sources and one positive metadata artifact per mode; its captured manifest and supervisor removal are recorded separately. All command TMPDIRs are empty afterward.

Fresh external compilation confirms the public validator is accessible and each new diagnostic module refuses import with E0603. Source and result references establish data shape and observed writes only; they establish no operational admission or artifact authority.

Every command retains argv, explicit toolchain/PATH/RUSTC/CARGO environment, source preimage, output hashes, bounded deadline and known owned process-group/direct-child cleanup observations. All 19 commands terminate with their expected status; the two privacy refusals are intentional negative controls. The owned Cargo target/home, probe executables and temporary directories are removed after evidence collection. No global process inventory, mobile runtime, simulator/emulator, UI automation, capture, Git operation or canonical write occurred.

`result.json` and `cleanup.json` index execution and limitations. Native/device/UI/capture checks remain paused. Integration targets, feature combinations, Linux, canonical CI, selected loader/adoption/snapshot integration, operational storage/work qualification, published FieldLog/package, OTA/store/customer and GA evidence remain pending. Host tests are not physical-device receipts or GA promotion.
''')
    pycache=r.OUT/'__pycache__'
    if pycache.exists():
        shutil.rmtree(pycache)
    members=[r.member(r.OUT,str(p.relative_to(r.OUT))) for p in sorted(r.OUT.rglob('*')) if p.is_file() and p!=r.OUT/'seal.json']
    seal={'schema':1,'member_count':len(members),'member_bytes':sum(row['bytes'] for row in members),
          'members':members,'tree_sha256':r.sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode()),
          'scope':'Independent frozen source136 host library, exact scalar/fixture extraction and privacy review only; root acceptance separate'}
    r.write(r.OUT/'seal.json',seal)
    print(json.dumps({'status':result['status'],'library_tests':test_results,'member_count':len(members),
                      'member_bytes':seal['member_bytes'],'seal_sha256':r.sha((r.OUT/'seal.json').read_bytes()),
                      'tree_sha256':seal['tree_sha256']}),flush=True)

if __name__=='__main__':
    main()
