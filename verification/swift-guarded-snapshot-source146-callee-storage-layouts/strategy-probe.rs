#![feature(generic_const_exprs)]
#![allow(incomplete_features, dead_code)]
fn size<T>(_: &T) -> [(); std::mem::size_of::<T>()] { [(); std::mem::size_of::<T>()] }
fn align<T>(_: &T) -> [(); std::mem::align_of::<T>()] { [(); std::mem::align_of::<T>()] }
fn test<P>(x: &mut u64, y: &usize) {
    let closure = || { *x += *y as u64; };
    let _probe_size: [(); usize::MAX] = size(&closure);
    let _probe_align: [(); usize::MAX] = align(&closure);
    let empty = |n: u64| n.checked_add(1);
    let _empty_size: [(); usize::MAX] = size(&empty);
    let _empty_align: [(); usize::MAX] = align(&empty);
}
