#![allow(dead_code)]
#[path = "host_account.rs"] mod host_account;
fn fake(reservation: host_account::ReservationV1<'_>) -> host_account::DestroyedStorageV1<'_> { host_account::DestroyedStorageV1 { reservation } }
