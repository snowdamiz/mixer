fn independent_cache_move(cache:&mut Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>,control:&mut crate::experimental_swift_reactor::control::RuntimeControl) {
let initial=super::InitialProfileBorrowV1 {
 cache: cache.as_ref().unwrap(), control: &*control, wasi: None,
 scalars: super::InitialProfileScalarsV1 { source_extent:0,type_count:0,slot_limit:0,pin_limit:0,initial_nonce:0,cache_base:0,cache_capacity:0,entry_limit:0 },
};
let _taken=cache.take(); std::hint::black_box(&initial);
}
