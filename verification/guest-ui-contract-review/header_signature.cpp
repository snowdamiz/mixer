#include "mixer_vm_guest_ui.h"
#include "mixer_vm_guest_ui.h"

using ExpectedGuestUIValidateV1 = uint32_t (*)(
    const uint8_t *, size_t, const MixerVmLimits *,
    const MixerVmCapabilityLimitsV1 *, MixerVmReport *);

static_assert(MIXER_VM_GUEST_UI_ABI_VERSION == 1u, "optional ABI version");
static_assert(__is_same(decltype(&mixer_vm_capability_guest_ui_validate_v1),
                        ExpectedGuestUIValidateV1),
              "exact accepted C++ declaration");
static_assert(sizeof(MixerVmLimits) == 32, "inherited LP64 limits layout");
static_assert(sizeof(MixerVmCapabilityLimitsV1) == 32, "inherited capability limits layout");
static_assert(sizeof(MixerVmReport) == 352, "inherited LP64 report layout");
