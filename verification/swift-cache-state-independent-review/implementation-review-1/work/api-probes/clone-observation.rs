#![forbid(unsafe_code)]
extern crate mixer_fixture_cache_state as api;
fn demand<T:Clone>(){} fn main(){demand::<api::FixtureCacheStateObservationV1>();}
