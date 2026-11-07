use mixer_absence::*;
fn inspect(x:&FixtureEnvelopeOutcomeV1)->bool {
    let _=x.framing();let e=x.envelope();
    let _=(e.boundary(),e.reason(),e.observed_records(),e.state(),e.phase(),e.mask(),e.last_operation(),e.active_operation(),e.requested_function(),e.pin_failure(),e.terminal_failure(),e.last_work(),e.last_instructions(),e.envelope_debit());
    x.full_replay_accepted()||e.semantic_metrics_valid()||x.stored_prefix_validated()
}
fn main(){let _f:fn(&mut std::fs::File,&mut std::fs::File,&mut std::fs::File,&mut std::fs::File)->Result<FixtureEnvelopeOutcomeV1,AnalyzerError>=analyze_fixture_envelope_v1;let _i:fn(&FixtureEnvelopeOutcomeV1)->bool=inspect;}
