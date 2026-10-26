#![forbid(unsafe_code)]
extern crate mixer_fixture_cache_state as api;
fn probe(v:&api::FixtureCacheStateOutcomeV1){let _: &api::ReplayOutcome=v.framing();let _: &api::FixtureEnvelopeObservationV1=v.envelope();let _: &api::FixtureCacheStateObservationV1=v.cache_state();} fn main(){}
