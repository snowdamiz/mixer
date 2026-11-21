#include <stdint.h>

// Swift 6.3.3's direct wasm externs add two implicit i32 arguments.
// Bind the existing Mixer imports with their exact C-compatible Wasm signatures.
__attribute__((import_module("mixer.capability.v1"), import_name("storage_get")))
int32_t storage_get(const void *, uint32_t, uint64_t *);

__attribute__((import_module("mixer.capability.v1"), import_name("poll")))
int32_t storage_poll(uint64_t, void *, uint32_t, uint32_t *);

int32_t fieldlog_get(const void *arguments, uint32_t length, uint64_t *token) {
    return storage_get(arguments, length, token);
}

int32_t fieldlog_poll(uint64_t token, void *response, uint32_t capacity, uint32_t *length) {
    return storage_poll(token, response, capacity, length);
}
