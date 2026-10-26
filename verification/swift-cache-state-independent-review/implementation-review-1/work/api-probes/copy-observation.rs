#![forbid(unsafe_code)]
extern crate mixer_fixture_cache_state as api;
fn demand<T:Copy>(){} fn main(){demand::<api::FixtureCacheStateObservationV1>();}
