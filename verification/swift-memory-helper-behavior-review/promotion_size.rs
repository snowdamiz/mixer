use std::cell::Cell;
use std::thread::LocalKey;
fn main() {
 println!("PROMOTED reference_bytes={} reference_align={} backing_bytes={} backing_align={} required_extra_unit_bytes={}",std::mem::size_of::<&LocalKey<Cell<bool>>>(),std::mem::align_of::<&LocalKey<Cell<bool>>>(),std::mem::size_of::<LocalKey<Cell<bool>>>(),std::mem::align_of::<LocalKey<Cell<bool>>>(),4*(std::mem::size_of::<&LocalKey<Cell<bool>>>()+std::mem::size_of::<LocalKey<Cell<bool>>>()));
}
