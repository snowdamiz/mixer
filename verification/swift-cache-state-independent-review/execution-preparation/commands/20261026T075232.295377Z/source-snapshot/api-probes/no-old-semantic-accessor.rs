#![forbid(unsafe_code)]
extern crate mixer_fixture_cache_state as api;
fn probe(v:&api::ReplayOutcome){let _=v.cache_state();} fn main(){}
