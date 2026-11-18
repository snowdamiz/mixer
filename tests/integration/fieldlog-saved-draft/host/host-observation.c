#include "mixer_ui_binding.h"
#include <pthread.h>
#include <string.h>

// The historical host bridge still owns native resources and checks its
// transport lease. This wrapper records the exact bytes it actually accepted.
extern int32_t mxis_host_apply(uint64_t, uint64_t, uint64_t, uint64_t, uint64_t, const uint8_t *, uint32_t);
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static uint8_t observed[65536];
static uint32_t size;
static uint64_t owner;
static uint64_t recorded_probe;

int32_t mxis_apply(uint64_t facade, uint64_t entry, uint64_t attachment, uint64_t input,
                   uint64_t probe, const uint8_t *packet, uint32_t bytes) {
    int32_t status = mxis_host_apply(facade, entry, attachment, input, probe, packet, bytes);
    if (status == MXUIT_OK && bytes <= sizeof(observed)) {
        pthread_mutex_lock(&lock);
        memcpy(observed, packet, bytes);
        owner = facade;
        size = bytes;
        recorded_probe = probe;
        pthread_mutex_unlock(&lock);
    }
    return status;
}

uint64_t mxfield_recorded_probe(uint64_t facade) {
    pthread_mutex_lock(&lock);
    uint64_t probe = owner == facade ? recorded_probe : 0;
    pthread_mutex_unlock(&lock);
    return probe;
}

uint32_t mxfield_host_packet(uint64_t facade, uint64_t probe, uint8_t *output, uint32_t capacity) {
    pthread_mutex_lock(&lock);
    uint32_t count = owner == facade && probe == recorded_probe && size <= capacity ? size : 0;
    if (count) memcpy(output, observed, count);
    pthread_mutex_unlock(&lock);
    return count;
}
