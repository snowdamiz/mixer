use std::cell::Cell;
struct W {
 a: std::thread::local_impl::EagerStorage<Cell<bool>>,
 b: core::num::niche_types::UsizeNoHighBit,
 c: *const std::sync::ArcInner<std::sync::atomic::AtomicBool>,
 d: *const std::sync::atomic::private::Align8<usize>,
}
fn main(){}
