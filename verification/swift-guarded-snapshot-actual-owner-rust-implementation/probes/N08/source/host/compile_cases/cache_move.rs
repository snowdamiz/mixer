fn forbidden(mut cache:super::SwiftFunctionCache,control:&mut super::RuntimeControl) {
 let initial=super::InitialProfileBorrowV1 {cache:&cache,control,wasi:None,scalars:super::InitialProfileScalarsV1 {source_extent:0,type_count:0,slot_limit:0,pin_limit:0,initial_nonce:0,cache_base:0,cache_capacity:0,entry_limit:0}};
 drop(cache);
 std::hint::black_box(initial.cache.next_nonce);
}
