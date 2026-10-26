#![forbid(unsafe_code)]
extern crate mixer_fixture_cache_state as api;
fn probe(a:&mut std::fs::File,b:&mut std::fs::File,c:&mut std::fs::File,d:&mut std::fs::File){let _=api::analyze_fixture_cache_state_v1(a,b,c,d,true);} fn main(){}
