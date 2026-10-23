/* Owned static VM is linked by the native build. No alternate runtime fallback. */
#include "mixer_vm.h"
_Static_assert(sizeof(MixerVmLimits) == 32, "MixerVmLimits ABI mismatch");
_Static_assert(sizeof(MixerVmValue) == 16, "MixerVmValue ABI mismatch");
_Static_assert(sizeof(MixerVmReport) == 352, "MixerVmReport ABI mismatch");
