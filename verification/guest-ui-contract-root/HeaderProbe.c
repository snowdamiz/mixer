#include "mixer_vm_guest_ui.h"
typedef uint32_t (*GuestUIValidationSignature)(const uint8_t *, size_t,
    const MixerVmLimits *, const MixerVmCapabilityLimitsV1 *, MixerVmReport *);
GuestUIValidationSignature mixer_guest_ui_header_signature =
    &mixer_vm_capability_guest_ui_validate_v1;
#if defined(__cplusplus)
static_assert(MIXER_VM_GUEST_UI_ABI_VERSION == 1u, "UI version");
static_assert(sizeof(MixerVmReport) == 352, "existing report layout");
static_assert(sizeof(MixerVmCapabilityLimitsV1) == 32, "existing limits layout");
#else
_Static_assert(MIXER_VM_GUEST_UI_ABI_VERSION == 1u, "UI version");
_Static_assert(sizeof(MixerVmReport) == 352, "existing report layout");
_Static_assert(sizeof(MixerVmCapabilityLimitsV1) == 32, "existing limits layout");
#endif
