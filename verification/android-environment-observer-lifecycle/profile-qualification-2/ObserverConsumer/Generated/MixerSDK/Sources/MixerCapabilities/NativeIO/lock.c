#include "MixerCapabilityIO.h"
#include <sys/file.h>
int mixer_capability_lock(int descriptor, int operation) { return flock(descriptor, operation); }
