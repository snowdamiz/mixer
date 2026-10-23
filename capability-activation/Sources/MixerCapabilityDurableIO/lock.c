#include "MixerCapabilityDurableIO.h"
#include <sys/file.h>

int mixer_capability_update_flock(int descriptor, int operation) {
    return flock(descriptor, operation);
}
