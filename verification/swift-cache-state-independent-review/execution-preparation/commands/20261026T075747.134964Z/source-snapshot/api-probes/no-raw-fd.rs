#![forbid(unsafe_code)]
extern crate mixer_fixture_cache_state as api;
fn probe(a:i32,b:i32,c:i32,d:i32){let _=api::analyze_fixture_cache_state_v1(a,b,c,d);} fn main(){}
