#![allow(dead_code)]
#[path="frozen_host_account.rs"] mod account;
fn check(a:&account::TrustedHostAccountV1,q:account::ReviewedWholeQuoteV1){
    let owner=a.reserve_whole_v1(q).unwrap().dispatch_v1(||vec![1u8]);
    assert_eq!(owner.inspect_v1().unwrap().as_slice(),&[1u8]);
    let token=owner.destroy_owned_v1().unwrap();
    token.release_destroyed_v1();
}
fn main(){}
