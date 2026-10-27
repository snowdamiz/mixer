"""One-shot independent packet finalization. Not a product/compiler runner."""
from pathlib import Path
import datetime, hashlib, json, os, sys, time
sys.dont_write_bytecode=True
import independent as I
import check_packet as C
HERE=Path(__file__).resolve().parent
def write(name,value):(HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def main():
    assert not (HERE/'seal.json').exists(),'one-shot: already sealed'
    started=datetime.datetime.now(datetime.timezone.utc).isoformat();start=time.monotonic()
    controls=I.load(HERE/'controls.json');assertions=I.load(HERE/'assertion-counts.json');report=I.load(HERE/'reconstruction.json')
    latest=HERE/'commands/host-005/receipt.json';receipt=I.load(latest);assert receipt['success']
    historical=[]
    for p in sorted((HERE/'commands').glob('host-*/receipt.json')):
        r=I.load(p)
        for name,record in r['scripts'].items():
            data=(p.parent/('snapshot-'+name)).read_bytes();assert len(data)==record['bytes'] and I.digest(data)==record['sha256']
        historical.append({'path':str(p.relative_to(HERE)),'sha256':I.digest(p.read_bytes()),'success':r['success'],'all_children_reaped':all(c['child_reaped'] for c in r['commands']),'all_owned_groups_observed_absent_at_completion':all(c['owned_group_absent'] for c in r['commands'])})
    review={'schema':1,'status':'independent-conditional-interface-acceptance-recommended-to-root','accepted_scope':'conditional source-work and logical typed-slot interface only','producer_packet':{'path':str(I.P.relative_to(I.ROOT)),'seal_sha256':I.EXPECTED_SEAL,'members':56,'bytes':13734810},'root_frozen_release_sha256':I.EXPECTED_RELEASE,'source_tree_sha256':I.TREE,'source_members':146,'base_correspondence':{'old_MIR_constructs':6006,'standalone_constants_included':1785,'mandatory_conditional_source_work_storage_rebind':True,'source_and_protocol_acceptance_only':True},'independent_reconstruction':{'constructs':11,'main_roles':171,'closure_roles':11,'promoted_roles':4,'standalone_constant_roles':7,'roles':193,'operations':565,'positive_assertions':sum(assertions.values()),'operation_component_equalities':assertions['independent operation price'],'body_values_used_for_affine_checks':[0,1,1947,65537],'finite_unrolled_identity_body_cap':12,'finite_unrolled_path_body_cap':5,'identity_header_cap':13,'path_header_cap':6,'authored_callback_cap':5},'native_observations':{'named_pairs':18,'named_dimensions':36,'anonymous_actual_closure_size':16,'anonymous_actual_closure_alignment':8,'MIR_fields':['native_path_bodies: &[&[u8]; 5]','position: &usize'],'compiler_padding_presentation':'end padding: 16 bytes, opaque; not interpreted as fields','LLVM_forced_actual_HRTB_production_function_and_callback':True,'raw_metadata_not_retained':'query.rmeta was removed by the producer; only its bound receipt digest is available, not a new raw metadata rehash'},'arithmetic':{'provider_source_fixed':276580,'actual_max22_body_coefficient':1324,'prior_conditional_whole_fixed':895084428325956794,'conditional_whole_fixed':895084428326233374,'typed_inline_slots':8344,'distinct_external_caller_Result':1352,'P0_addition':9696,'prior_fixed_P0':292037,'conditional_fixed_P0':301733,'external_result_end':4134},'strict_positive_external_std_terms':I.EXPECTED_CALLS,'strict_positive_upstream_work_terms':['actual_prepaid_acquisition_work','future_provider_caller_and_launcher_work'],'old_residual_terms':I.load(I.P/'candidate.json')['inherited_residual_work_terms'],'all_written_slots_retained_all15_phases':True,'logical_slot_bound_not_physical_stack_or_heap':True,'zero_alias_move_refund_credit':True,'original_1168_binding_and_12_full_preimages_plus5native_plus5retained_bodies_preserved':True,'logical_input_backing_bytes_is_descriptive_only':True,'unknown_future_caller_inline_and_backing_positive_external':True,'six_child_storage_components_unchanged':True,'normal_release_only_after_actual_original_payload_carrier_destructors_return_Some':True,'None_refusal_unwind_credit':False,'forged_content_accepted_by_shape_claim_only_model':True,'stronger_conditional_storage_source_hash_checks_are_not_admitted_owner_authority':True,'host_methods':controls['methods'],'adverse_cases':controls['adverse_cases'],'reconstruction_and_control_assertions_in_test_process':controls['independent_reconstruction_assertions'],'final_host_receipt':{'path':str(latest.relative_to(HERE)),'sha256':I.digest(latest.read_bytes())},'historical_host_receipts':historical,'producer_failures_preserved':['attempts/derive-001/failure.json','attempts/derive-002/failure.json'],'reviewer_failure_preserved':{'path':'commands/host-003/1-stderr','reason':'Independent strict-namespace refinement initially omitted actual fully qualified promoted-constant identity. It failed closed; corrected exact production namespace and foreign-namespace refusal controls now pass. Producer was unchanged.'},'findings_requiring_producer_correction':[],'all_six_upstream_requirements':'Pending','all_three_selectors':'Pending','L_str_selected':False,'external_callee_prices_or_root_funding_selected':False,'actual_acquisition_authenticated_owner_execution_qualified':False,'operational_grant_or_OTA_or_GA':False,'new_compiler_invocations':0,'new_Rust_product_or_native_runtime_invocations':0,'native_simulator_emulator_UI_capture_checks':'Paused; newly unrun; no instances/processes started or inventoried','physical_phone_checks':'Pending; disconnected; no reconnection requested','separate_published_package_FieldLog_qualification':False}
    write('review.json',review)
    text='''# Independent provider work/storage review

Bounded acceptance is recommended for the exact frozen conditional source-work
and logical typed-slot interface. No producer correction is required by this
review. This is not a complete operational cost, quote, grant, identity witness,
acquisition implementation, or runtime qualification.

The producer seal is `28ba8099ce8b57f91cd46baac21f130986000ecbbf7df07b16e6bf061fc342d1`
(56 members, 13,734,810 bytes). The 146-file source tree is
`acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d`.
Both the candidate's exact membership and all 262 frozen input rows were
rehashed before and after reconstruction, together with root's frozen release
and the separately retained 1,947-byte test preimage. No candidate file changed.

## Independent reconstruction

`independent.py` reads retained MIR and LLVM directly. It implements a separate
top-level partitioner, parameter/local parser, source declaration parser,
aggregate recursion, type extent substitution, literal frontier and arithmetic
checker. It never imports the producer derivation or shape helper. A finite
counter unroll of the actual CFG derives each block's maximum visits; it does
not copy the producer SCC member sets. Every normal, refusal, unreachable,
unwind and cut-backedge route is reconstructed. Prior costs transport only
through the exact root-accepted complete 6,006-construct correspondence,
including all 1,785 standalone constants and the mandatory conditional rebind.

| Construct | Roles | Operations | Logical slots | Work per request |
| --- | ---: | ---: | ---: | --- |
| Main | 171 | 533 | 8,126 | 263551 + 1204 B |
| Actual callback, up to five invocations | 11 | 19 | 113 | 7675 + 120 B |
| Two promoted constants | 4 | 6 | 49 | 926 |
| Seven standalone constants | 7 | 7 | 56 | 294 |
| Distinct external caller Result end | — | — | 1,352 | 4134 |
| Total | 193 written roles | 565 | 9,696 including caller Result | 276580 + 1324 B |

Each of 565 operations is checked at B = 0, 1, 1947, 65537 in separate source,
native-byte and combined components: 6,780 equalities. B = 0 and 1 are symbolic
affine checks, not admitted selected-source inputs. The actual interface uses
the maximum of all twenty-two actual declared body lengths: twelve identity,
five native path, five separately retained path bodies. No maximum is selected.
Every parameter, result, repeated operand, move/copy, constructor, return and
finite role end remains charged. The source-derived ranges permit twelve and
five body iterations, thirteen and six final-inclusive header visits, and five
sequential authored callbacks. Individually maximal incompatible refusal arms
are summed conservatively.

The inherited unit counts source/typed aggregate occurrences and native logical
typed bytes. It makes no CPU/time/private compiler, allocator, kernel or panic
cost claim. Fourteen full standard-library callee interface prices remain
strict positive external requirements; their exact counts are in `review.json`.
The authored callback is priced separately from Option::and_then. Both actual
prepaid acquisition and future provider caller/launcher work remain positive
external terms. All ten old residuals, including unselected `67424 * L_str`,
survive. The conditional fixed sum is 895084428326233374; this is not a whole
quote because B and all external terms remain required.

## Storage and ownership

The 8,344 written logical bytes plus a distinct 1,352-byte external caller Result
add 9,696 to the previous 292,037 P0 fixed inventory, giving 301,733. Every
written slot stays reserved through all fifteen inherited phases and final
outer-result consumption. These are logical place reservations; they do not
describe physical stack overlap or allocator footprint. Moving or aliasing
cannot reduce them, and repeated callback work does not invent five simultaneous
closure allocations.

The original 1,168-byte binding is already in the inherited base. Twelve complete
identity preimage allocations, five native Path allocations, five separately
retained byte bodies, original diagnostics, future root inline/backing, all
native operands, original Error owners, payload/carrier/destructor temporary
backing and all six child components remain mandatory. The logical length-sum
descriptor is neither another allocation nor a capacity bound. Unknown future
caller/input staging remains a positive external obligation; no guessed moved
container is introduced.

Normal release still requires the actual original payload and carrier
destructors to return the existing Some token. None, refusal and unwind provide
no refund. The independent controls exercise only the frozen finite retirement
model, not actual destruction or account execution.

## Retained compiler evidence

The exact root-authorized 55-second / 16-MiB plan ran once, historically, with
production opt0 metadata/MIR/LLVM emission and no linking or product execution.
Its 4.348-second successful receipt, exact rustc 1.99.0 executable/version hashes,
source/query insertion, complete query manifest, raw/compressed MIR and LLVM,
and output streams were checked. The original 4-MiB proposal and runner remain
preserved and unexecuted. No compiler was invoked by this review.

Eighteen named size/alignment pairs give 36 observations. The actual production
closure at source 1185:27 is independently observed at 16 bytes, alignment eight.
MIR identifies `native_path_bodies: &[&[u8]; 5]` and `position: &usize`; LLVM binds
the inert exact HRTB function pointer to the unchanged production function and
its real callback ABI. The compiler's exact `end padding: 16 bytes` line stays
opaque and is not substituted for capture fields. All eleven production MIR
constructs match the prior accepted MIR after exact scratch identities/comments
normalize. Removed query.rmeta bytes cannot be rehashed; its producer digest and
successful compiler receipt are historical metadata evidence only.

## Controls, retained failures and limits

Twenty fresh host methods and 1,013 adverse cases pass. Controls cover missing
typed roles, phase/storage omissions, loop edges/headers, unknown generic calls
and constants, all call counts and residuals, alias and move credits, original
full input/backing obligations, source/unit/evidence mutation, forged digest
claims, no-NUL/path equality, checked arithmetic overflow and no-refund routes.
43,435 positive reconstruction assertions and the full repeated-control count
are recorded separately rather than implying distinct product executions.

The shape-only model deliberately accepts forged content carrying the selected
source claim. Stronger conditional storage/work checks reject the forged
preimage and enforce inherited loader geometry, but still construct no admitted
or authenticated owner. Positive synthetic evidence labels/prices qualify only
the arithmetic tests; they do not select real evidence or operational prices.
The 64-MiB executable cap is reviewed in byte-bound source; this suite avoids a
giant boundary allocation. Smaller build/session geometry boundaries are tested.

Both original producer parser failures remain untouched. Reviewer host-003 also
preserves a fail-closed strict-namespace parser error: its first refinement
omitted the actual fully qualified promoted-constant namespace. The corrected
exact identity passes, while foreign same-basename constants are refused. The
final host-005 receipt passes all three bounded commands with exact script
snapshots, version/hash, argv/environment, output hashes and owned cleanup.

All six upstream requirements and all three selectors stay Pending. Actual
acquisition, immutable ownership/authenticated correspondence, diagnostic and
identity/path proof, positive external prices, root policy/quote/funding,
execution/build/session closure, genuine loader/writer/destructor execution and
healthy runtime cleanup remain required. Native/phone, separate published-package
FieldLog, OTA and GA qualification remain pending. No compiler, product/native
runtime, UI/capture, simulator/emulator, global process inventory, Git operation,
publication or other-project process manipulation occurred.

After sealing, use only the read-only checker:

```
python3 -B verification/swift-guarded-snapshot-owned-provider-work-storage-independent/check_packet.py
```
'''
    (HERE/'README.md').write_text(text)
    cleanup={'schema':1,'all_bounded_host_children_reaped':all(r['all_children_reaped'] for r in historical),'owned_groups_observed_absent_at_each_completion':all(r['all_owned_groups_observed_absent_at_completion'] for r in historical),'scratch_created':False,'new_compiler_or_product_or_native_runtime':False,'simulator_emulator_UI_capture_started':False,'global_process_inventory_performed':False,'other_project_processes_inspected_or_touched':False,'Git_mutations':False,'native_and_phone_checks':'Paused/Pending','source_or_producer_packet_writes':False,'owned_scope':str(HERE.relative_to(I.ROOT))}
    write('cleanup.json',cleanup)
    check=C.check(sealed=False)
    finalization={'schema':1,'argv':[sys.executable,'-B',str(Path(__file__).resolve())],'python':sys.version,'python_executable_sha256':I.digest(Path(sys.executable).read_bytes()),'script_sha256':I.digest(Path(__file__).read_bytes()),'source_tree_sha256':I.TREE,'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-start,'check':check,'scope':'one-shot own packet assembly and read-only integrity reconstruction; no spawned compiler/product/runtime children','success':True}
    write('finalization.json',finalization)
    rows=C.rows();seal={'schema':1,'status':'frozen-independent-conditional-interface-review','member_count':len(rows),'total_bytes':sum(r['bytes'] for r in rows),'member_table_sha256':I.digest(I.canon(rows)),'members':rows,'producer_seal_sha256':I.EXPECTED_SEAL,'source_tree_sha256':I.TREE,'operational_grant_or_OTA_or_GA':False}
    write('seal.json',seal)
    for path in HERE.rglob('*'):
        if path.is_file():path.chmod(0o444)
    print(json.dumps({'seal_sha256':I.digest((HERE/'seal.json').read_bytes()),'members':len(rows),'bytes':seal['total_bytes'],'methods':controls['methods'],'adverse_cases':controls['adverse_cases'],'accepted_scope':review['accepted_scope']},sort_keys=True))
if __name__=='__main__':main()
