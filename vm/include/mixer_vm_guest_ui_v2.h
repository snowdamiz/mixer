#ifndef MIXER_VM_GUEST_UI_V2_H
#define MIXER_VM_GUEST_UI_V2_H
#include "mixer_vm_capability.h"
#ifdef __cplusplus
extern "C" {
#endif
/* UNSELECTED experimental candidate, linked only with experimental-guest-ui-v2-native.
 * V1/default/native-only symbol sets are unchanged. No signed selection is supplied.
 * Same-config complete capability validation requires defined:
 *   mixer_guest_ui_start_v2: () -> i32
 *   mixer_guest_ui_event_v2: (i32) -> i32
 *   mixer_guest_capability_ready_v1: () -> ()
 * Existing module/import/function/global/memory ceilings and numeric preflight,
 * status/report and lifetime rules in mixer_vm_capability.h remain unchanged.
 * No instance, reservation, startup, I/O or signed selection follows validation.
 * Runtime document/event/header rules belong to the V2 bridge, not validation.
 * Candidate little-endian unaligned 32-byte control header:
 *   u32 magic=0x3249554d (MUI2); u32 size=32;
 *   u32 document_offset; u32 document_length in 1..1048576;
 *   u32 event_offset; u32 event_capacity=1048576; u64 reserved=0.
 * Header offset, event offset and capacity are fixed per session. All three
 * complete ranges must be nonwrapping, in bounds and pairwise disjoint at each
 * actual turn harvest. Existing native copies remain <=1MiB per operation.
 * These declarations confer no execution, signed admission or release authority.
 */
#define MIXER_VM_GUEST_UI_V2_CANDIDATE_ABI_VERSION 2u
#define MIXER_VM_GUEST_UI_V2_CANDIDATE_MAGIC 0x3249554du
#define MIXER_VM_GUEST_UI_V2_CANDIDATE_MAXIMUM_BYTES 1048576u
uint32_t mixer_vm_capability_guest_ui_validate_v2(
    const uint8_t *module, size_t module_len,
    const MixerVmLimits *vm_limits,
    const MixerVmCapabilityLimitsV1 *capability_limits, MixerVmReport *out);
#ifdef __cplusplus
}
#endif
#endif
