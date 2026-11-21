#ifndef MIXER_EXPERIMENTAL_SWIFT_CAPABILITY_H
#define MIXER_EXPERIMENTAL_SWIFT_CAPABILITY_H
/* Supply only the pinned experimental builder's include directory. */
#include <mixer_vm_capability.h>
#include <mixer_vm_guest_ui.h>
#include <mixer_vm_guest_ui_deferred.h>
/* Private Swift host bridge. This is not a guest import. */
uint32_t mixer_private_guest_ui_commit_request_v1(
    uint64_t handle, uint64_t token, uint64_t facts_token, uint32_t *accepted, MixerVmReport *report);
#ifdef MIXER_PRIVATE_F10
/* Only defined by the macOS private-fieldlog-f10 build. Pointer contract matches V1. */
uint32_t mixer_private_f10_validate(const uint8_t *, size_t, const MixerVmLimits *, const MixerVmCapabilityLimitsV1 *, MixerVmReport *);
uint32_t mixer_private_f10_create(const uint8_t *, size_t, const MixerVmLimits *, const MixerVmCapabilityLimitsV1 *, uint64_t *, MixerVmReport *);
#endif
#endif
