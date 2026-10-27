#![allow(dead_code)]
#[path = "host_account.rs"] mod host_account;
fn needs_sync<T: Sync>() {}
fn main() { needs_sync::<host_account::TrustedHostAccountV1>(); }
