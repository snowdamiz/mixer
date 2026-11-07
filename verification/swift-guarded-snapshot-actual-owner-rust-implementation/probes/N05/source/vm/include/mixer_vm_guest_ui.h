#ifndef MIXER_VM_GUEST_UI_H
#define MIXER_VM_GUEST_UI_H
#include "mixer_vm_capability.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Additive validate-only ABI in the selected experimental-capability-native
 * archive. Default and guest-only archives do not export this symbol. This
 * declaration is not authority to select, execute, present or enable a guest.
 * Existing capability and legacy headers and their status domains are unchanged.
 *
 * Full same-config capability validation, then require defined function exports:
 *   mixer_guest_ui_start_v1: () -> i32
 *   mixer_guest_ui_event_v1: (i32) -> i32
 *   mixer_guest_capability_ready_v1: () -> ()
 * Exactly one defined nonshared memory and unchanged v3 limits/imports apply.
 * No instance, mailbox, registry reservation, startup or native I/O is created.
 * Runtime control-header/document/event validation remains the bridge's duty.
 *
 * The complete numeric preflight/lifetime contract in mixer_vm_capability.h
 * applies to module, optional limits and report. Invalid null/range/wrap/alias
 * returns 3 without writing ANY output. Module length <= 4 MiB. Fixed structures
 * may be unaligned. Optional null limits use the existing defaults. Caller must
 * supply actual live storage; numeric checks cannot validate dangling pointers.
 * After valid preflight the report is initialized. Success returns 0. Complete
 * validation or required-export rejection returns 1. Export rejection uses
 * exact machine code capability_export, function UINT32_MAX and offset 0, with
 * zero fuel/host calls; messages never classify failures. Invalid limits return
 * 3, contained panic returns 4. No new native status or machine-code domain.
 */
#define MIXER_VM_GUEST_UI_ABI_VERSION 1u
uint32_t mixer_vm_capability_guest_ui_validate_v1(
    const uint8_t *module, size_t module_len,
    const MixerVmLimits *vm_limits,
    const MixerVmCapabilityLimitsV1 *capability_limits, MixerVmReport *out);
#ifdef __cplusplus
}
#endif
#endif
