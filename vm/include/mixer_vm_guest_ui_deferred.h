#ifndef MIXER_VM_GUEST_UI_DEFERRED_H
#define MIXER_VM_GUEST_UI_DEFERRED_H
#include "mixer_vm_guest_ui.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Same preflight and report contract, additionally requiring a defined
 * mixer_guest_ui_hydrate_v1: () -> i32 for signed deferred-startup mode. */
uint32_t mixer_vm_capability_guest_ui_validate_deferred_v1(
    const uint8_t *module, size_t module_len,
    const MixerVmLimits *vm_limits,
    const MixerVmCapabilityLimitsV1 *capability_limits, MixerVmReport *out);
#ifdef __cplusplus
}
#endif
#endif
