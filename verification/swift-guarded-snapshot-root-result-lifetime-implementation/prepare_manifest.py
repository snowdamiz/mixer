#!/usr/bin/env python3
"""Hash the exact two-member delta and unchanged146/host11 closure; source only."""
from pathlib import Path
import datetime,difflib,hashlib,json
P=Path(__file__).resolve().parent
R=P.parents[1]
B=R/'verification/swift-guarded-snapshot-actual-owner-rust-retirement-correction'
def sha(v):return hashlib.sha256(v).hexdigest()
def digest(v):return sha(json.dumps(v,sort_keys=True,separators=(',',':')).encode())
def row(path,base):
    data=path.read_bytes();return {'path':str(path.relative_to(base)),'bytes':len(data),'sha256':sha(data)}
def rows(base):return [row(p,base) for p in sorted(base.rglob('*')) if p.is_file()]
def write(name,v):(P/name).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
source=rows(P/'source/vm');host=rows(P/'source/host')
base_source=json.loads((B/'source-manifest.json').read_text())
base_host=json.loads((B/'host-manifest.json').read_text())
assert rows(B/'source/vm')==base_source['members']
assert rows(B/'source/host')==base_host['members']
assert len(source)==146 and len(host)==11
assert [m['path'] for m in source]==[m['path'] for m in base_source['members']]
changed=[new['path'] for old,new in zip(base_source['members'],source) if old!=new]
assert changed==['src/experimental_swift_reactor/cache/initial_profile_v1.rs','src/experimental_swift_reactor/retained_profile_loader_v1.rs']
assert host==base_host['members']
write('source-manifest.json',{'schema':1,'member_count':146,'members':source,'tree_sha256':digest(source),'changed':changed,'new_distribution_members':0})
write('host-manifest.json',{'schema':1,'member_count':11,'members':host,'tree_sha256':digest(host),'unchanged':True})
patch=[]
for member in changed:
    old=(B/'source/vm'/member).read_text();new=(P/'source/vm'/member).read_text()
    patch.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozen-correction/'+member,tofile='root-result-lifetime/'+member))
(P/'source-delta.patch').write_text(''.join(patch))
# Exact occurrence inventory assists, but never replaces, semantic/source/MIR
# review. No syntax check is authorization for an OTA or runtime release.
terms=['RootBoundV1','RawSelectedBundleV1','CorrelatedSelectedProfileV1','RootBoundSelectedProfileV1','RawCorrelationOutcomeV1','OwnedCorrelationOutcomeV1','FixtureLeafArgumentsV1','RawFixturePrimaryV1','RawFixtureResultV1','RootBoundFixtureOutcomeV1','RootBoundPrimaryBorrowV1','AdmittedFixtureOutcomeV1','AdmittedFixturePayloadV1','correlate_core_v1','into_result_v1','split_pair_v1','into_selected_v1','run_fixture_once_v1','primary_v1','original_root_v1','run_one_admitted_fixture_v1','run_prepaid_admitted_fixture_v1','destroy_returned_admitted_fixture_v1','observe_admitted_originals_v1']
occurrences=[]
for member in changed:
    for n,line in enumerate((P/'source/vm'/member).read_text().splitlines(),1):
        matched=[t for t in terms if t in line]
        if matched:occurrences.append({'path':member,'line':n,'terms':matched,'source':line})
write('private-transition-inventory.json',{
    'schema':1,'status':'source-inventory-awaiting-complete-MIR-and-independent-review','source146_tree':digest(source),
    'all_named_occurrences':occurrences,
    'finite_production_transitions':[
      {'site':'correlation_scope_core_v1','review':'Only root producer is exact self.owned.reservation.root. Both borrowed association inputs share it. Sticky IR01 barrier precedes either input publication.'},
      {'site':'PrepaidCorrelationAttemptV1::original_root_v1','review':'Returns only the same shared original reference; cache obtains it before setup. No grant or owner is returned.'},
      {'site':'correlate_core_v1','review':'Three root-bearing return literals: live/association/root refusal, provenance refusal, success. Root is copied exclusively from consumed attempt, never expected.'},
      {'site':'RootBoundV1::into_result_v1','review':'Single private destructure; either branch moves the entire payload and exact root to a complete bound return. No callback or raw result accessor.'},
      {'site':'correlate_admitted_loader_v1','review':'Receives whole LoaderOutcome first. Two bound input destructures; reconstructs all four File slots, usage, selected or full original error. Provenance refusal retains original selected/error. Every output is opaque and bound.'},
      {'site':'CorrelatedSelectedProfileV1::into_selected_v1','review':'Private complete envelope-to-envelope move only; one production callsite in fixed run. No bare selected reexport or extractor.'},
      {'site':'OwnedCorrelationOutcomeV1::run_fixture_once_v1','review':'Only facade consuming operation. Takes all args by value, destructures bound raw family in one synchronous frame, refuses without leaf, moves complete selected through private bound selection transition, holds original root while existing raw adoption/scope/run/finish sequence executes, immediately captures both typed leaf arms and all resources in bound final result. No sibling cache helper or visibility widening.'},
      {'site':'RootBoundFixtureOutcomeV1::primary_v1/usage_v1','review':'Only short shared references to originals and existing Copy scalar LoaderUsage. No owned/mutable/generic/Deref projection.'},
      {'site':'run_prepaid_admitted_fixture_v1','review':'Gets exact attempt reference before File setup. Both setup refusal paths own complete original SetupOutcome and root. Loaded path passes rows/snapshot/cancellation/claims by value to fixed operation and holds complete bound final result.'},
      {'site':'run_one_admitted_fixture_v1','review':'Child quote/refusal before dispatch; closure captures one attempt and fixture. Returns PrepaidOwned<child,AdmittedFixtureOutcome<root>> with separate account lifetimes.'},
      {'site':'observe_admitted_originals_v1','review':'Shared child inspection and scalar observations only. Setup originals borrowed; loaded branch uses short primary/scalar view. No raw owner moves.'},
      {'site':'destroy_returned_admitted_fixture_v1','review':'Consumes whole child through existing destroy_owned. Destruction token contains no original payload and carries only child account lifetime.'},
      {'site':'consume_admitted_owner_once_v1','review':'Current concrete outer observes child, destroys whole child, releases sole child token once, retires acquisition owner, returns scalar only. This fixed ordering is not full generic ownership proof.'},
    ],
    'private_generic_partition':{'site':'RootBoundV1::split_pair_v1','visibility':'module-private; no cfg(test) raw accessor','review':'Returns two complete bound wrappers with exact same original reference; used only in finite original-refusal guard tests. No raw owning projection returned.'},
    'test_review':'Original guard witnesses call actual production generic core; no alternate leaf/ownership state machine. Sentinel mini-leaf removed from new counterpart; historical source and failing receipts remain frozen in original packets. Compile-only positives use actual File facade supplied inputs. H23 checks foreign root ends first. H24 injects Guard destructor panic only; no native File or VM fixture run.',
    'probe_includes':'Three cfg-only include sites take one immutable separately hashed negative fragment per compiler command. No public constructor, root mint, or raw unwrap API added. Exactly one source closure is shared unchanged by all negative commands.',
    'new_source_MIR_layout_prices':'Pending; no old size, floor or quote is approved',
    'forgotten_root_funding_shutdown_full_ownership_joint_retirement':'Pending',
})
write('source-audit.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source146_members':146,'host11_members':11,'changed':changed,'new_distribution_members':0,'host11_byte_identical':True,'IR01_source_barrier_unchanged':True,'canonical_vm_edited':False,'compiler_execution':False,'host_product_execution':False,'native_File_acquisition_or_VM_fixture_execution':False,'source146_tree':digest(source),'host11_tree':digest(host)})
print(json.dumps({'source146_tree':digest(source),'host11_tree':digest(host),'changed':changed,'compiler_execution':False}))
