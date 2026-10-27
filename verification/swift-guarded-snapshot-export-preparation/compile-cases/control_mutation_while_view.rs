use super::*;
fn forbidden(cache:&mut SwiftFunctionCache,control:&mut RuntimeControl) {
 let scalars=InitialProfileScalarsV1 {source_extent:0,type_count:0,slot_limit:0,pin_limit:0,initial_nonce:0,cache_base:0,cache_capacity:0,entry_limit:0};
 let g=InitialProfileBorrowV1 {cache,control,wasi:None,scalars};
 let v=crate::experimental::swift::snapshot_export_preparation_v1::borrow_logical_snapshot_v1(&g);
 let _mutable=&mut *control;
 if let Ok(v)=v {let _=v.source();}
}

