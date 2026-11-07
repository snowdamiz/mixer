//! Numeric pointer preflight for the proposed capability C boundary.
//!
//! No pointer is dereferenced here. Passing these checks does not prove that a
//! native address refers to live, readable or writable storage. The trusted C
//! caller retains that obligation, including the complete call's lifetime.

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Access {
    Read,
    Write,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Invalid {
    Null,
    Length,
    Overflow,
    Overlap,
}

#[derive(Clone, Copy, Debug)]
pub(super) struct Range {
    start: usize,
    end: usize,
    access: Access,
}

impl Range {
    pub(super) fn bytes(
        address: usize,
        length: usize,
        maximum: usize,
        access: Access,
    ) -> Result<Self, Invalid> {
        if length > maximum || length > isize::MAX as usize {
            return Err(Invalid::Length);
        }
        if length != 0 && address == 0 {
            return Err(Invalid::Null);
        }
        let end = address.checked_add(length).ok_or(Invalid::Overflow)?;
        Ok(Self {
            start: address,
            end,
            access,
        })
    }

    pub(super) fn elements<T>(
        address: usize,
        count: usize,
        maximum_count: usize,
        access: Access,
    ) -> Result<Self, Invalid> {
        if count > maximum_count {
            return Err(Invalid::Length);
        }
        let length = count
            .checked_mul(std::mem::size_of::<T>())
            .ok_or(Invalid::Overflow)?;
        Self::bytes(address, length, isize::MAX as usize, access)
    }

    fn conflicts(self, other: Self) -> bool {
        (self.access == Access::Write || other.access == Access::Write)
            && self.start < self.end
            && other.start < other.end
            && self.start < other.end
            && other.start < self.end
    }
}

/// Include every input/output range, including the report, before any write.
/// Optional null structures are represented as empty ranges by the caller.
/// A fixed-size stack array keeps preflight allocation-free and bounded.
pub(super) fn preflight<const N: usize>(
    ranges: [Result<Range, Invalid>; N],
) -> Result<(), Invalid> {
    for (index, range) in ranges.iter().enumerate() {
        let range = (*range)?;
        for other in &ranges[..index] {
            if range.conflicts((*other)?) {
                return Err(Invalid::Overlap);
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_null_nonempty_lengths_and_address_wrap_before_use() {
        assert_eq!(
            Range::bytes(0, 1, 8, Access::Read).unwrap_err(),
            Invalid::Null
        );
        assert_eq!(
            Range::bytes(1, 9, 8, Access::Read).unwrap_err(),
            Invalid::Length
        );
        assert_eq!(
            Range::bytes(1, isize::MAX as usize + 1, usize::MAX, Access::Read).unwrap_err(),
            Invalid::Length
        );
        assert_eq!(
            Range::bytes(usize::MAX, 1, 8, Access::Write).unwrap_err(),
            Invalid::Overflow
        );
        assert!(Range::bytes(usize::MAX - 1, 1, 8, Access::Write).is_ok());
        assert!(Range::bytes(0, 0, 0, Access::Read).is_ok());
        assert!(Range::bytes(usize::MAX, 0, 0, Access::Write).is_ok());
    }

    #[test]
    fn typed_arrays_check_count_and_byte_multiplication() {
        assert_eq!(
            Range::elements::<u64>(1, 9, 8, Access::Read).unwrap_err(),
            Invalid::Length
        );
        assert_eq!(
            Range::elements::<u64>(1, usize::MAX, usize::MAX, Access::Read).unwrap_err(),
            Invalid::Overflow
        );
        assert_eq!(
            Range::elements::<u64>(1, isize::MAX as usize / 8 + 1, usize::MAX, Access::Read)
                .unwrap_err(),
            Invalid::Length
        );
        // Fixed C structures need no alignment to be copied with read/write_unaligned.
        assert!(Range::elements::<u64>(3, 1, 1, Access::Write).is_ok());
        assert!(Range::elements::<u64>(0, 0, 8, Access::Read).is_ok());
    }

    #[test]
    fn every_writable_alias_is_rejected_and_read_only_overlap_is_allowed() {
        for a in 1..=16 {
            for b in 1..=16 {
                for n in 0..=12 {
                    for m in 0..=12 {
                        let overlap = (a..a + n).any(|byte| (b..b + m).contains(&byte));
                        for left in [Access::Read, Access::Write] {
                            for right in [Access::Read, Access::Write] {
                                let expected =
                                    overlap && (left == Access::Write || right == Access::Write);
                                let first = Range::bytes(a, n, 12, left);
                                let second = Range::bytes(b, m, 12, right);
                                assert_eq!(preflight([first, second]).is_err(), expected);
                                assert_eq!(preflight([second, first]).is_err(), expected);
                            }
                        }
                    }
                }
            }
        }
    }

    #[test]
    fn report_is_a_participating_write_range_and_empty_ranges_are_disjoint() {
        let input = Range::bytes(8, 8, 8, Access::Read);
        let output = Range::bytes(32, 8, 8, Access::Write);
        let report = Range::bytes(64, 352, 352, Access::Write);
        assert_eq!(preflight([input, output, report]), Ok(()));
        for start in [8, 15, 32, 39] {
            assert_eq!(
                preflight([input, output, Range::bytes(start, 352, 352, Access::Write)]),
                Err(Invalid::Overlap)
            );
        }
        assert_eq!(
            preflight([report, Range::bytes(65, 0, 0, Access::Write)]),
            Ok(())
        );
        assert_eq!(
            preflight([report, Range::bytes(64 + 352, 1, 1, Access::Read)]),
            Ok(())
        );
        assert_eq!(
            preflight([report, Range::bytes(64 + 351, 1, 1, Access::Read)]),
            Err(Invalid::Overlap)
        );
    }
}
