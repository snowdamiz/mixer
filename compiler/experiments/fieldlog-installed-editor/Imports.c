#include <stdint.h>

/* The Swift 6.3.3 wasm extern lowering adds implicit arguments. Keep these
 * wrappers at the exact existing capability ABI. */
__attribute__((import_module("mixer.capability.v1"), import_name("storage_get")))
int32_t storage_get(const void *, uint32_t, uint64_t *);
__attribute__((import_module("mixer.capability.v1"), import_name("storage_put")))
int32_t storage_put(const void *, uint32_t, uint64_t *);
__attribute__((import_module("mixer.capability.v1"), import_name("poll")))
int32_t capability_poll(uint64_t, void *, uint32_t, uint32_t *);

int32_t editor_get(const void *bytes, uint32_t length, uint64_t *token) {
    return storage_get(bytes, length, token);
}
int32_t editor_put(const void *bytes, uint32_t length, uint64_t *token) {
    return storage_put(bytes, length, token);
}
int32_t editor_poll(uint64_t token, void *bytes, uint32_t capacity, uint32_t *length) {
    return capability_poll(token, bytes, capacity, length);
}
