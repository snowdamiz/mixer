//! Fixed C values, independent of Rust enum/usize layouts; native feature only.
#[repr(C)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MixerVmCapabilityLimitsV1 {
    pub struct_size: u32,
    pub abi_version: u32,
    pub maximum_requests: u32,
    pub timeout_milliseconds: u32,
    pub turn_milliseconds: u32,
    pub reserved: u32,
    pub reservation_bytes: u64,
}
impl Default for MixerVmCapabilityLimitsV1 {
    fn default() -> Self {
        Self {
            struct_size: 32,
            abi_version: 1,
            maximum_requests: 8,
            timeout_milliseconds: 30000,
            turn_milliseconds: 50,
            reserved: 0,
            reservation_bytes: 8388608,
        }
    }
}
#[repr(C)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MixerVmCapabilityMessageV1 {
    pub struct_size: u32,
    pub abi_version: u32,
    pub kind: u32,
    pub operation: u32,
    pub token: u64,
    pub remaining_milliseconds: u32,
    pub payload_length: u32,
    pub reserved: u64,
}
impl Default for MixerVmCapabilityMessageV1 {
    fn default() -> Self {
        Self {
            struct_size: 40,
            abi_version: 1,
            kind: 0,
            operation: 0,
            token: 0,
            remaining_milliseconds: 0,
            payload_length: 0,
            reserved: 0,
        }
    }
}
#[repr(C)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MixerVmCapabilityResultV1 {
    pub struct_size: u32,
    pub abi_version: u32,
    pub kind: u32,
    pub remaining_milliseconds: u32,
    pub reserved: u64,
}
impl Default for MixerVmCapabilityResultV1 {
    fn default() -> Self {
        Self {
            struct_size: 24,
            abi_version: 1,
            kind: 0,
            remaining_milliseconds: 0,
            reserved: 0,
        }
    }
}

// The same checks compile in each admitted cross-target archive, independently
// of host unit execution. Unsupported targets remain preflight-rejected.
#[cfg(all(
    target_pointer_width = "64",
    any(target_arch = "aarch64", target_arch = "x86_64")
))]
const _: () = {
    use std::mem::{align_of, offset_of, size_of};
    assert!(size_of::<MixerVmCapabilityLimitsV1>() == 32);
    assert!(align_of::<MixerVmCapabilityLimitsV1>() == 8);
    assert!(offset_of!(MixerVmCapabilityLimitsV1, struct_size) == 0);
    assert!(offset_of!(MixerVmCapabilityLimitsV1, abi_version) == 4);
    assert!(offset_of!(MixerVmCapabilityLimitsV1, maximum_requests) == 8);
    assert!(offset_of!(MixerVmCapabilityLimitsV1, timeout_milliseconds) == 12);
    assert!(offset_of!(MixerVmCapabilityLimitsV1, turn_milliseconds) == 16);
    assert!(offset_of!(MixerVmCapabilityLimitsV1, reserved) == 20);
    assert!(offset_of!(MixerVmCapabilityLimitsV1, reservation_bytes) == 24);
    assert!(size_of::<MixerVmCapabilityMessageV1>() == 40);
    assert!(align_of::<MixerVmCapabilityMessageV1>() == 8);
    assert!(offset_of!(MixerVmCapabilityMessageV1, struct_size) == 0);
    assert!(offset_of!(MixerVmCapabilityMessageV1, abi_version) == 4);
    assert!(offset_of!(MixerVmCapabilityMessageV1, kind) == 8);
    assert!(offset_of!(MixerVmCapabilityMessageV1, operation) == 12);
    assert!(offset_of!(MixerVmCapabilityMessageV1, token) == 16);
    assert!(offset_of!(MixerVmCapabilityMessageV1, remaining_milliseconds) == 24);
    assert!(offset_of!(MixerVmCapabilityMessageV1, payload_length) == 28);
    assert!(offset_of!(MixerVmCapabilityMessageV1, reserved) == 32);
    assert!(size_of::<MixerVmCapabilityResultV1>() == 24);
    assert!(align_of::<MixerVmCapabilityResultV1>() == 8);
    assert!(offset_of!(MixerVmCapabilityResultV1, struct_size) == 0);
    assert!(offset_of!(MixerVmCapabilityResultV1, abi_version) == 4);
    assert!(offset_of!(MixerVmCapabilityResultV1, kind) == 8);
    assert!(offset_of!(MixerVmCapabilityResultV1, remaining_milliseconds) == 12);
    assert!(offset_of!(MixerVmCapabilityResultV1, reserved) == 16);
};
