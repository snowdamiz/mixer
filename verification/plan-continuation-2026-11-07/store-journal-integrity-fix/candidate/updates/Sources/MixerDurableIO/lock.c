#include "MixerDurableIO.h"
#include <sys/file.h>

int mixer_update_flock(int descriptor, int operation) {
    return flock(descriptor, operation);
}
