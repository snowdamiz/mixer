#![allow(dead_code)]
#[path="frozen_host_account.rs"] mod account;
fn check<'a>(o:account::PrepaidOwnedV1<'a,Vec<u8>>)->&'a Vec<u8>{o.inspect_v1().unwrap()}
fn main(){}
