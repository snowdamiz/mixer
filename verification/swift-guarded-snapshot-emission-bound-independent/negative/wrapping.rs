//! Unselected pure arithmetic candidate. No admission path calls this helper.
use super::{AError, SnapshotShapeV1};

// 19_537 = accepted encoder fixed14_224 + writer fixed1_217 + initializer4_096.
// 299_377 = encoder nonempty-call ceiling291_214 + writer block4_259
//           +32 attempts * writer attempt122. Native requested bytes add32E.
// Only a private validated shape supplies E/blocks; this is not shape authority.
pub(super) fn checked_snapshot_emission_bound_v1(shape: &SnapshotShapeV1) -> Result<u64, AError> {
    let blocks = Some(shape.blocks.wrapping_mul(299_377u64)).ok_or(AError::Arithmetic)?;
    let transfers = shape.extent.checked_mul(32u64).ok_or(AError::Arithmetic)?;
    let fixed_and_transfers = 19_537u64.checked_add(transfers).ok_or(AError::Arithmetic)?;
    blocks.checked_add(fixed_and_transfers).ok_or(AError::Arithmetic)
}
