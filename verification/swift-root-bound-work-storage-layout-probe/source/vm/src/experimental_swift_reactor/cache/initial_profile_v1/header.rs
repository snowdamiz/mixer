use super::*;
// A fixed checked copy is the only scalar handoff. No owner or proof is copied.
pub(super) fn profile_scalars_v1(initial:&InitialProfileBorrowV1<'_>)->Result<InitialProfileScalarsV1,ProfileHeaderErrorV1> {
    let s=&initial.scalars;
    if !(1..=64).contains(&s.slot_limit) || !(1..=64).contains(&s.pin_limit) || s.initial_nonce!=1 {
        return Err(profile_error(5,4,56));
    }
    if s.cache_base>s.cache_capacity {return Err(profile_error(7,4,80));}
    Ok(InitialProfileScalarsV1 {source_extent:s.source_extent,type_count:s.type_count,slot_limit:s.slot_limit,
        pin_limit:s.pin_limit,initial_nonce:s.initial_nonce,cache_base:s.cache_base,cache_capacity:s.cache_capacity,entry_limit:s.entry_limit})
}
pub(super) fn encode_profile_header_v1(initial:&InitialProfileBorrowV1<'_>,claims:&UnverifiedProfileDigestBytesV1)
    ->Result<UnverifiedProfileHeaderV1,ProfileHeaderErrorV1> {
    let s=profile_scalars_v1(initial)?;
    let mut bytes=[0u8;512];
    bytes[..8].copy_from_slice(b"MIXPRF01");
    for (offset,value) in [(8,1u64),(16,512),(24,32),(32,80000),(40,s.source_extent),(48,s.type_count),
        (56,s.slot_limit),(64,s.pin_limit),(72,s.initial_nonce),(80,s.cache_base),(88,s.cache_capacity),(96,s.entry_limit)] {
        bytes[offset..offset+8].copy_from_slice(&value.to_le_bytes());
    }
    bytes[128..160].copy_from_slice(&claims.baseline);
    bytes[160..192].copy_from_slice(&claims.candidate);
    bytes[192..224].copy_from_slice(&claims.original_input);
    bytes[224..256].copy_from_slice(&claims.event_schema);
    bytes[256..288].copy_from_slice(&claims.profile_adapter_binary);
    bytes[288..320].copy_from_slice(&claims.layout_receipt);
    bytes[320..352].copy_from_slice(&claims.original_validated_snapshot);
    bytes[352..384].copy_from_slice(&claims.profile_row_body);
    Ok(UnverifiedProfileHeaderV1 {bytes})
}
