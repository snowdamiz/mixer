#ifndef MIXER_VM_CAPABILITY_H
#define MIXER_VM_CAPABILITY_H
#include "mixer_vm.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Experimental ABI declarations, available only in experimental-capability-native
 * archives. Default and guest-only archives do not export these functions.
 * Combined-boundary independent review must precede use by consumers.
 * LP64 arm64/x86_64 only; all structures may be unaligned. */
#define MIXER_VM_CAPABILITY_ABI_VERSION 1u
typedef struct MixerVmCapabilityLimitsV1 {
    uint32_t struct_size;
    uint32_t abi_version;
    uint32_t maximum_requests;
    uint32_t timeout_milliseconds;
    uint32_t turn_milliseconds;
    uint32_t reserved;
    uint64_t reservation_bytes;
} MixerVmCapabilityLimitsV1;
typedef struct MixerVmCapabilityMessageV1 {
    uint32_t struct_size;
    uint32_t abi_version;
    uint32_t kind; /* none0, call1, cancel2, tooSmall3 */
    uint32_t operation; /* HTTP1,get2,put3,delete4; unused0 */
    uint64_t token;
    uint32_t remaining_milliseconds;
    uint32_t payload_length;
    uint64_t reserved;
} MixerVmCapabilityMessageV1;
typedef struct MixerVmCapabilityResultV1 {
    uint32_t struct_size;
    uint32_t abi_version;
    uint32_t kind; /* accepted0,terminal1,acknowledged2; meaningful only status0 */
    uint32_t remaining_milliseconds;
    uint64_t reserved;
} MixerVmCapabilityResultV1;
/* Complete numeric preflight includes the report and every participating buffer.
 * Null required pointers, wrap/oversize, or any writable overlap return3 without
 * writing ANY output. Read-only inputs may overlap; empty ranges do not overlap.
 * After valid preflight, outputs are initialized (handle/flag0; structures with
 * size/version and otherwise0) before semantic work. Outputs are never read.
 * Callers guarantee live readable/writable storage for the entire call. Numeric
 * checks cannot validate dangling pointers. Fixed structures may be unaligned.
 * Null is allowed only for optional limits or empty byte/value arrays.
 * Module<=4MiB; names nonempty UTF8<=4096; invoke values<=4096 and legacy bit
 * encodings; memory copy<=1MiB; take capacity0..524288; post length1..524288.
 * VM limits retain existing ABI/ceilings. Capability limits: size32/version1,
 * reserved0, requests1..8, timeout1..30000ms, turn1..50ms, reservation1..8388608.
 * A raw token is scoped to its supplied handle. Equal bits may exist elsewhere.
 * Operation must match that handle's stored owner-bound ticket. No native I/O,
 * JSON/grant validation, scheduler or Swift continuation is performed here.
 * Status matrix (same report status0..4):
 * 0 successful protocol action; post/deadline-existing-terminal=>kind1 (deadline
 *   remaining0, never a renewed timeout); duplicate exit
 *   retained identity=>kind2. kind0 alone never proves success.
 * 1 full validation/startup/wake rejection (validate/create only).
 * 2 execution/instantiation failure or terminal live session. Zero remaining duration is
 *   expiry, never a renewed timeout or permission to perform I/O.
 * 3 API rejection: bad limits/value/range/name, stale/foreign family/identity,
 *   operation mismatch, busy instance, post after consumed/released identity,
 *   post/deadline after an early exit with no existing terminal, pool exhausted. A closed
 *   registry handle rejects3; an admitted live operation observing stop returns2.
 * 4 contained panic, denied access to poisoned/quarantined state or invariant violation; no
 *   fabricated exit ack/reclamation. Payload allocation refusal=>2 preserves
 *   request/retry/deadline state and does not imply terminal state or native exit.
 * Mailbox precedence is retained: stale/consumed identity rejects3 first;
 * existing unconsumed terminal yields post/deadline status0/kind1 even after
 * exit acknowledgement; only early ack with no terminal yields ordering error3.
 * Cleanup exception: cancel/close on a quarantined but unpoisoned owner may
 * return0 for a completed stop/close transition only. Quarantine remains sticky
 * and pins capacity; live ordinary access and retained-closing ack still reject4
 * (ordinary closed handles reject3). Mailbox poison during close returns4.
 * Successful take Call durably retains/counts one exit obligation; None,
 * tooSmall and Cancel create none. Only first successful ack decrements it.
 * Close/cancel permanently stop admission without waiting for guest mutex;
 * ordinary closed access rejects. Only ack_exit can use a retained closing
 * generation. Native caller must cancel/register work against its own closed
 * activation latch and acknowledge actual cleanup. No implicit exit on drop.
 */
uint32_t mixer_vm_capability_validate_v1(const uint8_t *module, size_t module_len,
    const uint8_t *startup_name, size_t startup_len, const MixerVmLimits *vm_limits,
    const MixerVmCapabilityLimitsV1 *capability_limits, MixerVmReport *out);
uint32_t mixer_vm_capability_session_create_v1(const uint8_t *module, size_t module_len,
    const uint8_t *startup_name, size_t startup_len, const MixerVmLimits *vm_limits,
    const MixerVmCapabilityLimitsV1 *capability_limits, uint64_t *out_handle, MixerVmReport *out);
uint32_t mixer_vm_capability_session_startup_v1(uint64_t handle, MixerVmReport *out);
uint32_t mixer_vm_capability_session_enable_v1(uint64_t handle, MixerVmReport *out);
uint32_t mixer_vm_capability_session_invoke_v1(uint64_t handle,
    const uint8_t *export_name, size_t export_len, const MixerVmValue *args, size_t args_len, MixerVmReport *out);
uint32_t mixer_vm_capability_session_wake_v1(uint64_t handle, uint32_t *out_did_invoke, MixerVmReport *out);
uint32_t mixer_vm_capability_session_read_v1(uint64_t handle, uint32_t offset,
    uint8_t *destination, size_t length, MixerVmReport *out);
uint32_t mixer_vm_capability_session_write_v1(uint64_t handle, uint32_t offset,
    const uint8_t *source, size_t length, MixerVmReport *out);
uint32_t mixer_vm_capability_session_cancel_v1(uint64_t handle, MixerVmReport *out);
uint32_t mixer_vm_capability_session_close_v1(uint64_t handle, MixerVmReport *out);
uint32_t mixer_vm_capability_take_v1(uint64_t handle, MixerVmCapabilityMessageV1 *out_message,
    uint8_t *output, size_t capacity, MixerVmReport *out);
uint32_t mixer_vm_capability_post_v1(uint64_t handle, uint64_t token, uint32_t operation,
    const uint8_t *completion, size_t length, MixerVmCapabilityResultV1 *out_result, MixerVmReport *out);
uint32_t mixer_vm_capability_ack_exit_v1(uint64_t handle, uint64_t token, uint32_t operation,
    MixerVmCapabilityResultV1 *out_result, MixerVmReport *out);
uint32_t mixer_vm_capability_limit_deadline_v1(uint64_t handle, uint64_t token, uint32_t operation,
    uint32_t timeout_milliseconds, MixerVmCapabilityResultV1 *out_result, MixerVmReport *out);
uint32_t mixer_vm_capability_expire_v1(uint64_t handle, MixerVmReport *out);
#ifdef __cplusplus
}
#endif
#endif
