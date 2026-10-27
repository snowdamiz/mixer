#![allow(dead_code)]
#[path = "host_account.rs"] mod host_account;
fn borrowed<'a,'b>(owner: &'b host_account::PrepaidOwnedV1<'a,Vec<u8>>) -> Option<&'b Vec<u8>> { owner.inspect_v1() }
fn retire<'a>(owner: host_account::PrepaidOwnedV1<'a,Vec<u8>>) { if let Some(token) = owner.destroy_owned_v1() { token.release_destroyed_v1(); } }
