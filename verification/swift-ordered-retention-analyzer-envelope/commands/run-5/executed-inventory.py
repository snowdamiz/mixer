#!/usr/bin/env python3
"""Authored complete named-role/source-phase proof, pending independent audit.

No stack/RSS, optimizer, std/allocator/kernel or production qualification.
"""
import hashlib
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent
RESERVATIONS={'wire':3072,'candidate':2048,'io':4096,'metadata':4096,'setup':12288,'control':8192,'report':8192}
EXTRAS={
 'wire':[
  ('private decoded wrapper8; caller/callee wrapper borrows8each; leaf word borrow8',32),
  ('complete prior zero literal96 and conservative next source/move96',192)],
 'candidate':[('sole retained Candidate2048 destination; payload96 is embedded, never a second owner',2048)],
 'io':[], 'metadata':[],
 'setup':[
  ('complete candidate initializer literal/source2048; retained destination in candidate group',2048),
  ('progress complete source144/destination144/conservative move144',432),
  ('progress zero reply literal128 and complete reply constructor128',256),
  ('complete twelve-cell constant literal/address table source96, conservatively charged',96)],
 'report':[
  ('complete retained Progress144 including reply128/discriminator8/cumulative debit8',144),
  ('five complete leaf reply source/return/caller/commit/error128 slots, conservative union',640),
  ('five complete public observation source/project/return/caller/move128 slots',640),
  ('five aggregate/Result source/return/public/caller/branch receiving slots232 each',1160),
  ('complete boundary/reason source/destination enum values4x8',32)],
}
# All complete fixed arrays/large values are charged above or by the accepted
# inventory. Helper leases below contain only additional complete arguments,
# borrows, checked Options, ranges, scalar/loop/error and small return places.
HELPERS={
 'new_core':(256,'extra wrapper admission Results4x40; p/result/arena/public-observation borrows32; enum/branch/error scalar places64'),
 'new_observe':(32,'progress caller/callee borrows16; additional call argument/return borrow places16'),
 'new_walk':(256,'progress caller/callee16; decoded wrapper/record borrows24; StepBudget16+borrows16; extra setup/report unit Results3x40; branch/index/control scalars64'),
 'leaf_locals':(1152,'prior96+next96; scalar/destructure/transition locals256; eight CheckedPair16=128; eight complete checked Option<u64>16=128; eight Range16=128; argument borrows32; slice views96; predicate/error/control locals128; four Range iterator16=64'),
 'word_at':(256,'bytes borrow16/offset8; checked end Option16/end8; slice Option16/slice16; LE source8; Pair source/return/caller4x16=64; all range/error/control scalar places104'),
 'shape':(256,'record8/kind8/function8; complete Option<u64> slots4x16=64; inclusive ranges3x24=72; captured record borrow8/end scalar8/boolean return4; predicate/control76'),
 'reply':(128,'four complete scalar/borrow arguments32; sixteen index/predicate/return borrow temporaries96; complete reply values separately in report'),
 'poisoned':(128,'debit8; fixed discriminator/scalar/borrow/return handling120; complete reply values separately in report'),
 'finalize':(512,'four borrows32; complete expected CheckedPair16 and source/return/caller16x3; input error borrow8; fixed enum/error/eligibility/control/index places408'),
 'project':(256,'progress borrow8/boundary8/reason8/extent1; reply borrow8; complete scalar/field/conditional/return places223; complete observations separately in report'),
 'reason_from_leaf':(128,'input8; complete enum source/return/caller24; fixed dispatch/control96'),
 'leaf_pending':(128,'progress borrow8; bool source/return/caller3; status/index/short-circuit/control117'),
 'reply_debit_valid':(128,'reply/StepBudget borrows16; bool source/return/caller3; fixed debit/state/index/short-circuit/control109'),
 'new_getters':(512,'conservative union of all26self borrows208; scalar/enum-reference return/caller places256; boolean/index/control48'),
}
PHASES={
 'new_wrapper_admission':('setup_budget',['new_core']),
 'new_progress_initialize':('arena_reserve',['new_core']),
 'new_input_metadata':('initial_input_metadata',['new_core','new_observe']),
 'new_context':('context_checked_copy',['new_core','new_observe']),
 'new_profile':('profile_checked_publish',['new_core','new_observe']),
 'new_header_and_candidate_initialize':('header_join',['new_core','new_observe','new_walk']),
 'new_record_framing':('record_fields_identity',['new_core','new_observe','new_walk','leaf_pending']),
 # Deliberately retain the whole larger framing field/helper chain while
 # charging every leaf helper together, even though these lifetimes do not
 # overlap. This is a conservative phase union, never optimizer elision.
 'new_record_leaf_or_guard':('record_fields_identity',['new_core','new_observe','new_walk','leaf_locals','word_at','shape','reply','poisoned','leaf_pending','reply_debit_valid']),
 'new_limited_drain':('limited_drain',['new_core','new_observe','new_walk']),
 'new_footer':('footer_decode_check',['new_core','new_observe','new_walk']),
 'new_final_metadata':('input_final_metadata',['new_core','new_observe']),
 'new_final_projection':('return_or_error',['new_core','finalize','project','reason_from_leaf','word_at']),
 'new_report':('report_digest_echo',['new_core']),
 'new_public_return_or_getters':('return_or_error',['new_core','new_getters']),
}

def build():
    old=json.loads((BASE/'inputs/accepted-inventory.json').read_text())
    assert old['named_role_upper_total']==14248
    used=dict(old['named_role_upper_by_group'])
    for group,roles in EXTRAS.items():used[group]+=sum(n for _,n in roles)
    phases={}
    for name,(base,helpers) in PHASES.items():
        n=old['phases'][base]['control_upper']+sum(HELPERS[h][0] for h in helpers)
        phases[name]=dict(control_upper=n,accepted_phase=base,additional_helpers=helpers)
    used['control']=max(old['named_role_upper_by_group']['control'],max(p['control_upper'] for p in phases.values()))
    for group,n in used.items():assert n<=RESERVATIONS[group],(group,n,RESERVATIONS[group])
    assert sum(RESERVATIONS.values())==41984
    hashes={name:hashlib.sha256((BASE/name).read_bytes()).hexdigest() for name in ['src/analyzer.rs','src/envelope.rs','inputs/accepted-inventory.json']}
    return dict(schema=1,kind='complete-conservative-composed-named-role-inventory-awaiting-independent-source-review',source_hashes=hashes,reservations=RESERVATIONS,named_role_upper_by_group=used,named_role_upper_total=sum(used.values()),reserved_total=41984,transient_ceiling=65536,unassigned_margin_unused=23552,arena_bytes=8388608,arena_used=7873120,arena_spare=515488,report_bytes=49152,future_host_bytes=8192,aggregate_report_bytes=57344,extra_roles={g:[dict(roles=s,bytes=n) for s,n in r] for g,r in EXTRAS.items()},additional_helper_leases={k:dict(bytes=n,roles=s) for k,(n,s) in HELPERS.items()},phases=phases,scope='one safe-File fixture call and caller receiving/move places; whole accepted framing inventory retained; no stack/TLS/RSS/std/kernel/allocator/optimizer qualification',candidate_lifetime='one2048 walk local; complete2048 source ends before loop; no by-value candidate argument/return/drop/move wrapper; payload96 embedded',coordinate_owners='Framing80 complete retained wire cursor; twelve96 arena cells owned solely by leaf; prior96/next96/decoded128/reply128 all separately charged',results='old complete File/Metadata/Stamp/Reader/Budget/error Results all retained; actual232 aggregate Results and128 observations include full caller/source/destination/error/return/move slots',selection='authored source/role proof only; independent review required; no real replay or report authority')

def main():
    value=build();(BASE/'logical-inventory.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(total=value['named_role_upper_total'],groups=value['named_role_upper_by_group'],max_phase=max(value['phases'],key=lambda n:value['phases'][n]['control_upper']))))
if __name__=='__main__':main()
