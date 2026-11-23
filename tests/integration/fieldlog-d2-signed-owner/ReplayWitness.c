#include "FieldLogHostTest.h"
#include <stdatomic.h>
static _Atomic uint64_t latest;
int32_t mxis_recorded_apply(uint64_t, uint64_t, uint64_t, uint64_t, uint64_t, const uint8_t *, uint32_t);
int32_t mxis_apply(uint64_t facade, uint64_t entry, uint64_t attachment, uint64_t input,
                   uint64_t probe, const uint8_t *packet, uint32_t size) {
    int32_t result = mxis_recorded_apply(facade, entry, attachment, input, probe, packet, size);
    if (result == 0) atomic_store(&latest, facade);
    return result;
}
uint64_t replay_find_facade(void) { return atomic_load(&latest); }
