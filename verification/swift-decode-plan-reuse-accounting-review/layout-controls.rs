
#[cfg(test)]
pub(super) mod independent_accounting {
    use super::*;
    pub const CANDIDATE: bool = REVIEW_CANDIDATE;
    pub fn shapes() -> [usize; 9] {
        [size_of::<SwiftFunctionCache>(), size_of::<Partial>(), size_of::<SwiftScratch<'static>>(),
         size_of::<CacheParts<'static,SwiftMode>>(), cache_cleanup_temporary_bytes().unwrap(),
         cache_header_bytes().unwrap(), cache_construction_bytes().unwrap(),cache_operation_bytes().unwrap(),
         foundation_construction_bytes().unwrap()]
    }
}
