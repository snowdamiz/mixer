// Independent review-only observers. Included only in the copied cache module.
#[cfg(test)]
pub(super) mod grouped_review {
    use super::*;
    use std::cell::Cell;
    #[derive(Clone, Copy, Debug, Default)]
    pub struct Report {
        pub enabled: bool,
        pub before: usize,
        pub after: usize,
        pub capacity: usize,
        pub length: usize,
        pub reserved: usize,
        pub freed_before: usize,
        pub freed_index: usize,
        pub completion: usize,
        pub completion_reserved: usize,
        pub expect_storage_drop: bool,
        pub storage_dropped: bool,
    }
    thread_local! { static REPORT: Cell<Report> = Cell::new(Report::default()); }
    pub fn reset(enabled: bool) {
        REPORT.with(|r|r.set(Report{enabled,..Report::default()}));
    }
    pub fn report() -> Report { REPORT.with(Cell::get) }
    pub fn before(control: &RuntimeControl, wasi: Option<WasiUsage>, index: &Vec<u8>, header: bool) {
        REPORT.with(|r| {
            let mut v=r.get(); if !v.enabled { return; }
            v.before+=1;
            v.capacity=index.capacity(); v.length=index.len();
            v.reserved=control.usage(wasi).reservations.cache.current;
            assert!(v.capacity==0 || (header && v.reserved==cache_header_bytes().unwrap()));
            v.freed_before=super::super::allocation_tests::review_allocator_snapshot().freed_bytes;
            r.set(v);
        });
    }
    pub fn after(control: &RuntimeControl, wasi: Option<WasiUsage>, index: &Vec<u8>) {
        REPORT.with(|r| {
            let mut v=r.get(); if !v.enabled { return; }
            v.after+=1;
            assert_eq!(index.capacity(),0);
            assert_eq!(control.usage(wasi).reservations.cache.current,v.reserved);
            v.freed_index=super::super::allocation_tests::review_allocator_snapshot().freed_bytes-v.freed_before;
            assert_eq!(v.freed_index,v.capacity);
            r.set(v);
        });
    }
    pub fn tail_usage(tail:&CacheCleanupTail<'_>) -> SwiftRunUsage {
        tail.control.usage(tail.wasi.map(AccountedWasi::usage))
    }
    pub struct ReturnedStorage;
    impl Drop for ReturnedStorage {
        fn drop(&mut self) { REPORT.with(|r| {let mut v=r.get();v.storage_dropped=true;r.set(v);}); }
    }
    pub fn expect_storage() { REPORT.with(|r|{let mut v=r.get();v.expect_storage_drop=true;r.set(v);}); }
    pub fn completing(control:&RuntimeControl,wasi:Option<WasiUsage>) {
        REPORT.with(|r| {
            let mut v=r.get();if !v.enabled{return;}
            v.completion+=1;
            v.completion_reserved=control.usage(wasi).reservations.cache.current;
            assert_eq!(v.completion_reserved,cache_header_bytes().unwrap());
            if v.expect_storage_drop {assert!(v.storage_dropped);}
            r.set(v);
        });
    }
}
