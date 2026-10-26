// Sibling insertion MUST reject this intended private type/literal access (E0603).
use super::initial_profile_v1::{InitialProfileBorrowV1,InitialProfileScalarsV1};
fn independent_private_guard(cache:&crate::experimental_swift_reactor::cache::SwiftFunctionCache,control:&crate::experimental_swift_reactor::control::RuntimeControl) {
 let _=InitialProfileBorrowV1 {cache,control,wasi:None,scalars:InitialProfileScalarsV1 {source_extent:0,type_count:0,slot_limit:0,pin_limit:0,initial_nonce:0,cache_base:0,cache_capacity:0,entry_limit:0}};
}
