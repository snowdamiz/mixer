//! Independent private guard witnesses. No product edits or cfg(test) harness.
use super::*;
fn words(v:&FixtureCacheStateObservationV1)->[u64;32]{
let b=match v.boundary(){FixtureCacheStateBoundaryV1::Unavailable=>0,FixtureCacheStateBoundaryV1::ClosedFixtureObserved=>1,FixtureCacheStateBoundaryV1::CapCutUnknownTail=>2,FixtureCacheStateBoundaryV1::Refused=>3,FixtureCacheStateBoundaryV1::AnalysisLimited=>4,FixtureCacheStateBoundaryV1::InternalPoisoned=>5,FixtureCacheStateBoundaryV1::ApplicabilityUnavailable=>6};
let r=match v.reason(){FixtureCacheStateReasonV1::Observed=>0,FixtureCacheStateReasonV1::Steps=>1,FixtureCacheStateReasonV1::FramingUnavailable=>2,FixtureCacheStateReasonV1::FramingInvalid=>3,FixtureCacheStateReasonV1::EnvelopeRefused=>4,FixtureCacheStateReasonV1::EnvelopeUnavailable=>5,FixtureCacheStateReasonV1::Identity=>6,FixtureCacheStateReasonV1::Resident=>7,FixtureCacheStateReasonV1::Plan=>8,FixtureCacheStateReasonV1::Victim=>9,FixtureCacheStateReasonV1::Bytes=>10,FixtureCacheStateReasonV1::Token=>11,FixtureCacheStateReasonV1::Nonce=>12,FixtureCacheStateReasonV1::Invariant=>13,FixtureCacheStateReasonV1::FailureApplicability=>14,FixtureCacheStateReasonV1::IncompleteBoundary=>15,FixtureCacheStateReasonV1::InternalPoison=>16,FixtureCacheStateReasonV1::OutputUnavailable=>17};
[b,r,v.observed_records(),v.cache_state_records(),v.stop_record(),v.last_sequence(),v.last_work(),v.last_instructions(),v.active_operation(),v.requested_function(),v.resident_count(),v.resident_bytes(),v.held_pins(),v.next_nonce(),v.active_plan_cell(),v.selected_mask(),v.taken_mask(),v.committed_mask(),v.pending_victim(),v.destination(),v.failure_coordinate(),v.semantic_debit(),v.semantic_setup_paid(),v.semantic_finish_paid(),v.fixture_state_observed(),v.tail_unknown(),u64::from(v.stored_prefix_validated()),u64::from(v.full_replay_accepted()),u64::from(v.semantic_metrics_valid()),u64::from(v.real_binding_verified()),v.reserved0(),v.reserved1()]}
pub(crate) fn run(){
let f=Fixture{cap:4,mask:33,extent:4096,types:2,slots:3,pins:3,base:0,capacity:10,entry:10};
let paid=Paid{setup:1,finish:1,records:4};
let mut s=Framing::new(4);s.framed=4;s.last_work=20;s.last_instructions=30;s.last_operation=2;s.flags=1;s.complete=true;
let input:Result<bool,AnalyzerError>=Ok(true);
{
let q:[u64;16]=[4, 20, 30, 0, 2, 513, 2, 6, 1, 4, 2, 0, 0, 1, 1, 1];
let p=Progress{calls:4,latch:0,q};
let env=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::CapCutUnknownTail,reason:FixtureEnvelopeReasonV1::Observed,observed_records:4,state:0,phase:0,mask:1,last_operation:2,active_operation:2,requested_function:513,pin_failure:0,terminal_failure:0,last_work:20,last_instructions:30,envelope_debit:2281,full_replay_accepted:0,stored_prefix_validated:0};
let valid=shape_q(&p.q,p.calls,p.terminal(),s.framed,&f);
let observed=projection(&p,&paid,&s,&input,&env,Some(&f));
println!("{{\"id\":\"idle-baseline\",\"shape_guard\":{},\"words\":{:?}}}",valid,words(&observed));
}
{
let q:[u64;16]=[4, 20, 30, 0, 2, 513, 2, 6, 1, 4, 8, 0, 0, 1, 1, 1];
let p=Progress{calls:4,latch:0,q};
let env=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::CapCutUnknownTail,reason:FixtureEnvelopeReasonV1::Observed,observed_records:4,state:0,phase:0,mask:1,last_operation:2,active_operation:2,requested_function:513,pin_failure:0,terminal_failure:0,last_work:20,last_instructions:30,envelope_debit:2281,full_replay_accepted:0,stored_prefix_validated:0};
let valid=shape_q(&p.q,p.calls,p.terminal(),s.framed,&f);
let observed=projection(&p,&paid,&s,&input,&env,Some(&f));
println!("{{\"id\":\"idle-inactive-selected-outside\",\"shape_guard\":{},\"words\":{:?}}}",valid,words(&observed));
}
{
let q:[u64;16]=[4, 20, 30, 0, 2, 513, 2, 6, 1, 4, 0, 4, 0, 1, 1, 1];
let p=Progress{calls:4,latch:0,q};
let env=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::CapCutUnknownTail,reason:FixtureEnvelopeReasonV1::Observed,observed_records:4,state:0,phase:0,mask:1,last_operation:2,active_operation:2,requested_function:513,pin_failure:0,terminal_failure:0,last_work:20,last_instructions:30,envelope_debit:2281,full_replay_accepted:0,stored_prefix_validated:0};
let valid=shape_q(&p.q,p.calls,p.terminal(),s.framed,&f);
let observed=projection(&p,&paid,&s,&input,&env,Some(&f));
println!("{{\"id\":\"idle-inactive-taken-not-subset\",\"shape_guard\":{},\"words\":{:?}}}",valid,words(&observed));
}
{
let q:[u64;16]=[4, 20, 30, 7, 2, 513, 2, 6, 1, 4, 2, 0, 0, 1, 1, 1];
let p=Progress{calls:4,latch:0,q};
let env=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::CapCutUnknownTail,reason:FixtureEnvelopeReasonV1::Observed,observed_records:4,state:7,phase:0,mask:1,last_operation:2,active_operation:2,requested_function:513,pin_failure:0,terminal_failure:0,last_work:20,last_instructions:30,envelope_debit:2281,full_replay_accepted:0,stored_prefix_validated:0};
let valid=shape_q(&p.q,p.calls,p.terminal(),s.framed,&f);
let observed=projection(&p,&paid,&s,&input,&env,Some(&f));
println!("{{\"id\":\"pending7-baseline\",\"shape_guard\":{},\"words\":{:?}}}",valid,words(&observed));
}
{
let q:[u64;16]=[4, 20, 30, 7, 2, 513, 2, 6, 1, 4, 2, 0, 0, 1, 1, 0];
let p=Progress{calls:4,latch:0,q};
let env=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::CapCutUnknownTail,reason:FixtureEnvelopeReasonV1::Observed,observed_records:4,state:7,phase:0,mask:1,last_operation:2,active_operation:2,requested_function:513,pin_failure:0,terminal_failure:0,last_work:20,last_instructions:30,envelope_debit:2281,full_replay_accepted:0,stored_prefix_validated:0};
let valid=shape_q(&p.q,p.calls,p.terminal(),s.framed,&f);
let observed=projection(&p,&paid,&s,&input,&env,Some(&f));
println!("{{\"id\":\"pending7-feasible-false\",\"shape_guard\":{},\"words\":{:?}}}",valid,words(&observed));
}
{
let q:[u64;16]=[4, 20, 30, 8, 2, 513, 2, 6, 1, 4, 2, 2, 0, 1, 1, 1];
let p=Progress{calls:4,latch:0,q};
let env=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::CapCutUnknownTail,reason:FixtureEnvelopeReasonV1::Observed,observed_records:4,state:8,phase:0,mask:1,last_operation:2,active_operation:2,requested_function:513,pin_failure:0,terminal_failure:0,last_work:20,last_instructions:30,envelope_debit:2281,full_replay_accepted:0,stored_prefix_validated:0};
let valid=shape_q(&p.q,p.calls,p.terminal(),s.framed,&f);
let observed=projection(&p,&paid,&s,&input,&env,Some(&f));
println!("{{\"id\":\"pending8-baseline\",\"shape_guard\":{},\"words\":{:?}}}",valid,words(&observed));
}
{
let q:[u64;16]=[4, 20, 30, 8, 2, 513, 2, 6, 1, 4, 2, 2, 0, 1, 1, 0];
let p=Progress{calls:4,latch:0,q};
let env=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::CapCutUnknownTail,reason:FixtureEnvelopeReasonV1::Observed,observed_records:4,state:8,phase:0,mask:1,last_operation:2,active_operation:2,requested_function:513,pin_failure:0,terminal_failure:0,last_work:20,last_instructions:30,envelope_debit:2281,full_replay_accepted:0,stored_prefix_validated:0};
let valid=shape_q(&p.q,p.calls,p.terminal(),s.framed,&f);
let observed=projection(&p,&paid,&s,&input,&env,Some(&f));
println!("{{\"id\":\"pending8-feasible-false\",\"shape_guard\":{},\"words\":{:?}}}",valid,words(&observed));
}
}
