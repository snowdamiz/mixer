#include <stdint.h>

#define MIXER_IMPORT(name) __attribute__((import_module("mixer.capability.v1"), import_name(name)))

MIXER_IMPORT("storage_get")
extern uint32_t mixer_storage_get(const void *bytes, uint32_t count, uint64_t *token);
MIXER_IMPORT("storage_put")
extern uint32_t mixer_storage_put(const void *bytes, uint32_t count, uint64_t *token);
MIXER_IMPORT("poll")
extern uint32_t mixer_poll(uint64_t token, void *bytes, uint32_t capacity, uint32_t *length);

uint32_t fieldlog_storage_get(const void *bytes, uint32_t count, uint64_t *token) {
    return mixer_storage_get(bytes, count, token);
}

uint32_t fieldlog_storage_put(const void *bytes, uint32_t count, uint64_t *token) {
    return mixer_storage_put(bytes, count, token);
}

uint32_t fieldlog_poll(uint64_t token, void *bytes, uint32_t capacity, uint32_t *length) {
    return mixer_poll(token, bytes, capacity, length);
}
