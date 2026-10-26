//! Private diagnostic row derivation from one real sealed validated owner.
//! Caller keeps the borrowed output/open-file-description quiescent. Success
//! records acknowledged writes only, without durability or artifact authority.
#![allow(dead_code)] // Isolated prerequisite; deliberately no live/public adoption.
use super::ValidatedSwiftReactor;
use std::fs::File;
use std::io::{self, Seek, Write};

const ROWS: u32 = 80_000;
const ROW_BYTES: usize = 32;
const BLOCK_BYTES: usize = 4096;
const ROWS_PER_BLOCK: u32 = 128;
const BLOCK_CALLS: u64 = 32;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(C)]
struct ProfileRowV1 {
    defined: u32,
    type_index: u32,
    body_offset: u64,
    body_len: u64,
    reserved: u64,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(C)]
pub(crate) struct ProfileRowsObservationV1 {
    rows: u64,
    defined_functions: u64,
    imported_functions: u64,
    source_extent: u64,
    type_count: u64,
    output_bytes: u64,
    output_attempts: u64,
    reserved: u64,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(C)]
pub(crate) struct ProfileAdapterErrorV1 {
    code: u32,
    stage: u32,
    offset: u64,
    output_bytes: u64,
    output_attempts: u64,
}
fn error(code: u32, stage: u32, offset: u64) -> ProfileAdapterErrorV1 {
    ProfileAdapterErrorV1 {
        code,
        stage,
        offset,
        output_bytes: 0,
        output_attempts: 0,
    }
}
fn admit(snapshot: &ValidatedSwiftReactor) -> Result<(), ProfileAdapterErrorV1> {
    let o = snapshot.observations();
    if ValidatedSwiftReactor::VALIDATOR_REVISION != 1
        || snapshot.policy_identity() != "swift-reactor-experiment-v1"
        || o.imported_functions != 34
        || o.validated_bodies != o.defined_functions
        || o.types > u32::MAX as usize
    {
        return Err(error(1, 1, 0));
    }
    let total = o
        .imported_functions
        .checked_add(o.defined_functions)
        .ok_or_else(|| error(13, 1, 0))?;
    if total > ROWS as usize {
        return Err(error(1, 1, 0));
    }
    Ok(())
}
fn profile_row_v1(
    snapshot: &ValidatedSwiftReactor,
    absolute: u32,
) -> Result<ProfileRowV1, ProfileAdapterErrorV1> {
    // Widen before multiplying, including requests outside the admitted range.
    let coordinate = u64::from(absolute) * ROW_BYTES as u64;
    if absolute >= ROWS {
        return Err(error(2, 2, coordinate));
    }
    admit(snapshot)?;
    let o = snapshot.observations();
    let end = o
        .imported_functions
        .checked_add(o.defined_functions)
        .ok_or_else(|| error(13, 2, coordinate))?;
    let descriptor = snapshot.execution_function(absolute);
    if (absolute as usize) < o.imported_functions || absolute as usize >= end {
        if descriptor.is_some() {
            return Err(error(4, 2, coordinate));
        }
        return Ok(ProfileRowV1 {
            defined: 0,
            type_index: u32::MAX,
            body_offset: u64::MAX,
            body_len: 0,
            reserved: 0,
        });
    }
    let d = descriptor.ok_or_else(|| error(3, 2, coordinate))?;
    let body_end = d
        .body_offset
        .checked_add(d.body.len())
        .ok_or_else(|| error(13, 2, coordinate))?;
    if d.absolute_index != absolute
        || d.type_index as usize >= o.types
        || body_end > snapshot.source().len()
    {
        return Err(error(4, 2, coordinate));
    }
    Ok(ProfileRowV1 {
        defined: 1,
        type_index: d.type_index,
        body_offset: u64::try_from(d.body_offset).map_err(|_| error(13, 2, coordinate))?,
        body_len: u64::try_from(d.body.len()).map_err(|_| error(13, 2, coordinate))?,
        reserved: 0,
    })
}
fn encode(row: ProfileRowV1, output: &mut [u8]) {
    output[0..4].copy_from_slice(&row.defined.to_le_bytes());
    output[4..8].copy_from_slice(&row.type_index.to_le_bytes());
    output[8..16].copy_from_slice(&row.body_offset.to_le_bytes());
    output[16..24].copy_from_slice(&row.body_len.to_le_bytes());
    output[24..32].copy_from_slice(&row.reserved.to_le_bytes());
}
fn admit_output(output: &mut File) -> Result<(), ProfileAdapterErrorV1> {
    let metadata = output.metadata().map_err(|_| error(5, 3, 0))?;
    if !metadata.is_file() {
        return Err(error(6, 3, 0));
    }
    let position = output.stream_position().map_err(|_| error(7, 3, 0))?;
    if metadata.len() != 0 || position != 0 {
        return Err(error(8, 3, 0));
    }
    Ok(())
}
fn with_progress(mut e: ProfileAdapterErrorV1, bytes: u64, attempts: u64) -> ProfileAdapterErrorV1 {
    e.output_bytes = bytes;
    e.output_attempts = attempts;
    e
}
// The only generic I/O seam is private and cannot replace the snapshot owner.
// Each invocation corresponds to exactly one real write call in production.
fn write_body(
    snapshot: &ValidatedSwiftReactor,
    mut write: impl FnMut(&[u8]) -> io::Result<usize>,
) -> Result<ProfileRowsObservationV1, ProfileAdapterErrorV1> {
    admit(snapshot)?;
    let mut block = [0u8; BLOCK_BYTES];
    let mut bytes = 0u64;
    let mut attempts = 0u64;
    for first in (0..ROWS).step_by(ROWS_PER_BLOCK as usize) {
        for local in 0..ROWS_PER_BLOCK {
            let row = profile_row_v1(snapshot, first + local)
                .map_err(|e| with_progress(e, bytes, attempts))?;
            let start = local as usize * ROW_BYTES;
            encode(row, &mut block[start..start + ROW_BYTES]);
        }
        let mut done = 0usize;
        let mut calls = 0u64;
        while done < BLOCK_BYTES {
            if calls == BLOCK_CALLS {
                return Err(with_progress(error(12, 4, bytes), bytes, attempts));
            }
            // These additions cannot overflow: 625 blocks, <=32 calls/block.
            calls += 1;
            attempts += 1;
            let remaining = BLOCK_BYTES - done;
            match write(&block[done..]) {
                Ok(0) => return Err(with_progress(error(10, 4, bytes), bytes, attempts)),
                Ok(n) if n > remaining => {
                    return Err(with_progress(error(11, 4, bytes), bytes, attempts))
                }
                Ok(n) => {
                    done += n;
                    bytes += n as u64;
                }
                Err(e) if e.kind() == io::ErrorKind::Interrupted => {}
                Err(_) => return Err(with_progress(error(9, 4, bytes), bytes, attempts)),
            }
        }
    }
    let o = snapshot.observations();
    Ok(ProfileRowsObservationV1 {
        rows: u64::from(ROWS),
        defined_functions: u64::try_from(o.defined_functions)
            .map_err(|_| with_progress(error(13, 5, bytes), bytes, attempts))?,
        imported_functions: u64::try_from(o.imported_functions)
            .map_err(|_| with_progress(error(13, 5, bytes), bytes, attempts))?,
        source_extent: u64::try_from(snapshot.source().len())
            .map_err(|_| with_progress(error(13, 5, bytes), bytes, attempts))?,
        type_count: u64::try_from(o.types)
            .map_err(|_| with_progress(error(13, 5, bytes), bytes, attempts))?,
        output_bytes: bytes,
        output_attempts: attempts,
        reserved: 0,
    })
}
pub(crate) fn write_profile_row_body_v1(
    snapshot: &ValidatedSwiftReactor,
    output: &mut File,
) -> Result<ProfileRowsObservationV1, ProfileAdapterErrorV1> {
    admit(snapshot)?;
    admit_output(output)?;
    write_body(snapshot, |bytes| output.write(bytes))
}
#[cfg(test)]
#[path = "diagnostic_profile_tests.rs"]
mod diagnostic_profile_tests;

#[cfg(test)]
#[path = "independent_result_layout_tests.rs"]
mod independent_result_layout_tests;
