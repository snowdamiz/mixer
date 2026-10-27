#![allow(dead_code)]
#[path="frozen_host_account.rs"] mod account;
fn check(t:account::ReservationV1<'_>){let _=t.dispatch_v1(||1);let _=t.dispatch_v1(||2);}
fn main(){}
