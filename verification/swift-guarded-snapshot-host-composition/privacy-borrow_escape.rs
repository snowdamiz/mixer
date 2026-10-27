#![allow(dead_code)]
#[path = "host_account.rs"] mod host_account;
fn escape<'a>(owned: host_account::PrepaidOwnedV1<'a, Vec<u8>>) -> &'a Vec<u8> {
    owned.inspect_v1().unwrap()
}
fn main() {}
