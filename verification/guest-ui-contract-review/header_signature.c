#include "mixer_vm_guest_ui.h"
#include "mixer_vm_guest_ui.h"

typedef uint32_t (*ExpectedGuestUIValidateV1)(
    const uint8_t *, size_t, const MixerVmLimits *,
    const MixerVmCapabilityLimitsV1 *, MixerVmReport *);

_Static_assert(MIXER_VM_GUEST_UI_ABI_VERSION == 1u, "optional ABI version");
_Static_assert(_Generic(&mixer_vm_capability_guest_ui_validate_v1,
                       ExpectedGuestUIValidateV1: 1, default: 0),
               "exact accepted validate-only declaration");
_Static_assert(sizeof(MixerVmLimits) == 32, "inherited LP64 limits layout");
_Static_assert(sizeof(MixerVmCapabilityLimitsV1) == 32, "inherited capability limits layout");
_Static_assert(sizeof(MixerVmReport) == 352, "inherited LP64 report layout");
