#include "mixer_android.h"
#include "mixer_android_v2.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { CAPACITY = 1048576 };
static unsigned checks;
#define CHECK(condition) do { \
    ++checks; \
    if (!(condition)) { \
        fprintf(stderr, "check %u failed at line %d: %s\n", checks, __LINE__, #condition); \
        exit(1); \
    } \
} while (0)

/* Test-fixture extraction from the owned canonical packet, not a product parser. */
static uint64_t title_generation(const char *packet) {
    const char *identities = strstr(packet, "\"identities\":[");
    CHECK(identities != NULL);
    const char *id = strstr(identities, ",\"id\":\"title\"}");
    CHECK(id != NULL);
    const char *start = id;
    while (start > identities && *start != '{') --start;
    uint64_t generation = 0;
    CHECK(sscanf(start, "{\"generation\":%" SCNu64, &generation) == 1);
    CHECK(generation != 0);
    return generation;
}

static size_t render(uint64_t handle, uint8_t *output) {
    size_t written = SIZE_MAX;
    CHECK(mixer_android_exchange(handle, 0, NULL, 0, output, CAPACITY, &written) == 0);
    CHECK(written > 0 && written < CAPACITY);
    CHECK(output[CAPACITY] == 0xA7);
    output[written] = 0;
    return written;
}

int main(void) {
    uint8_t *output = malloc(CAPACITY + 1), *initial = malloc(CAPACITY + 1);
    CHECK(output != NULL && initial != NULL);
    output[CAPACITY] = initial[CAPACITY] = 0xA7;
    const uint64_t handle = mixer_android_create(), other = mixer_android_create();
    CHECK(handle != 0 && other > handle);
    const size_t initial_size = render(handle, initial);
    uint64_t token = UINT64_MAX;
    size_t written = SIZE_MAX;

    CHECK(mixer_android_prepare_v2(handle, 0, NULL, 0, NULL, 0, &written, &token) == MIXER_ANDROID_V2_CAPACITY);
    CHECK(written == initial_size && token == 0);
    CHECK(render(handle, output) == initial_size && memcmp(initial, output, initial_size) == 0);

    token = 17; written = 19;
    CHECK(mixer_android_prepare_v2(handle, 0, NULL, 0, output, CAPACITY, NULL, &token) == MIXER_ANDROID_V2_INVALID_ARGUMENT);
    CHECK(token == 0);
    CHECK(mixer_android_prepare_v2(handle, 0, NULL, 0, output, CAPACITY, &written, NULL) == MIXER_ANDROID_V2_INVALID_ARGUMENT);
    CHECK(written == 0);
    const size_t invalid_lengths[] = {131073, SIZE_MAX};
    for (size_t i = 0; i < sizeof invalid_lengths / sizeof invalid_lengths[0]; ++i) {
        token = 17; written = 19;
        CHECK(mixer_android_prepare_v2(handle, 1, NULL, invalid_lengths[i], output, CAPACITY, &written, &token) == MIXER_ANDROID_V2_INVALID_ARGUMENT);
        CHECK(token == 0 && written == 0);
    }
    const size_t invalid_capacities[] = {CAPACITY + 1, SIZE_MAX};
    for (size_t i = 0; i < sizeof invalid_capacities / sizeof invalid_capacities[0]; ++i) {
        token = 17; written = 19;
        CHECK(mixer_android_prepare_v2(handle, 0, NULL, 0, output, invalid_capacities[i], &written, &token) == MIXER_ANDROID_V2_INVALID_ARGUMENT);
        CHECK(token == 0 && written == 0);
    }
    CHECK(mixer_android_prepare_v2(handle, 2, NULL, 0, output, CAPACITY, &written, &token) == MIXER_ANDROID_V2_INVALID_ARGUMENT);
    CHECK(mixer_android_prepare_v2(handle, 0, (const uint8_t *)"x", 1, output, CAPACITY, &written, &token) == MIXER_ANDROID_V2_INVALID_ARGUMENT);
    CHECK(mixer_android_prepare_v2(handle, 0, NULL, 0, NULL, 1, &written, &token) == MIXER_ANDROID_V2_INVALID_ARGUMENT);
    CHECK(mixer_android_prepare_v2(handle, 1, NULL, 0, output, CAPACITY, &written, &token) == MIXER_ANDROID_V2_ENGINE_REJECTED);
    CHECK(token == 0 && written == 0);
    CHECK(render(handle, output) == initial_size && memcmp(initial, output, initial_size) == 0);

    char *event = malloc(1024);
    CHECK(event != NULL);
    const int event_size = snprintf(event, 1024,
        "{\"revision\":1,\"identity\":{\"id\":\"title\",\"generation\":%" PRIu64 "},"
        "\"event\":\"textChange\",\"value\":\"C bridge Café 東京 🧪\"}", title_generation((const char *)initial));
    CHECK(event_size > 0 && event_size < 1024);
    CHECK(mixer_android_prepare_v2(handle, 1, (const uint8_t *)event, (size_t)event_size, output, CAPACITY, &written, &token) == MIXER_ANDROID_V2_OK);
    CHECK(token != 0 && written > 0 && written < CAPACITY && output[CAPACITY] == 0xA7);
    const uint64_t aborted = token;
    output[written] = 0;
    CHECK(strstr((const char *)output, "C bridge Café 東京 🧪") != NULL);
    CHECK(mixer_android_exchange(handle, 0, NULL, 0, output, CAPACITY, &written) == MIXER_ANDROID_V2_BUSY);
    CHECK(written == 0);
    CHECK(mixer_android_prepare_v2(handle, 0, NULL, 0, output, CAPACITY, &written, &token) == MIXER_ANDROID_V2_BUSY);
    CHECK(token == 0 && written == 0);
    CHECK(mixer_android_commit_v2(other, aborted) == MIXER_ANDROID_V2_STALE_TOKEN);
    CHECK(mixer_android_abort_v2(other, aborted) == MIXER_ANDROID_V2_STALE_TOKEN);
    CHECK(mixer_android_abort_v2(handle, aborted) == MIXER_ANDROID_V2_OK);
    CHECK(mixer_android_abort_v2(handle, aborted) == MIXER_ANDROID_V2_OK);
    CHECK(mixer_android_commit_v2(handle, aborted) == MIXER_ANDROID_V2_STALE_TOKEN);
    CHECK(render(handle, output) == initial_size && memcmp(initial, output, initial_size) == 0);

    CHECK(mixer_android_prepare_v2(handle, 1, (const uint8_t *)event, (size_t)event_size, output, CAPACITY, &written, &token) == MIXER_ANDROID_V2_OK);
    const uint64_t committed = token;
    CHECK(committed > aborted);
    /* Packet and input ownership end at return, before the decision. */
    memset(event, 0xDA, 1024); free(event);
    memset(output, 0xBC, CAPACITY);
    CHECK(mixer_android_abort_v2(handle, aborted) == MIXER_ANDROID_V2_OK);
    CHECK(mixer_android_exchange(handle, 0, NULL, 0, output, CAPACITY, &written) == MIXER_ANDROID_V2_BUSY);
    CHECK(mixer_android_commit_v2(handle, 0) == MIXER_ANDROID_V2_STALE_TOKEN);
    CHECK(mixer_android_commit_v2(handle, committed) == MIXER_ANDROID_V2_OK);
    CHECK(mixer_android_commit_v2(handle, committed) == MIXER_ANDROID_V2_STALE_TOKEN);
    CHECK(mixer_android_abort_v2(handle, committed) == MIXER_ANDROID_V2_STALE_TOKEN);
    (void)render(handle, output);
    CHECK(strstr((const char *)output, "C bridge Café 東京 🧪") != NULL);
    CHECK(strstr((const char *)output, "\"revision\":2") != NULL);
    CHECK(mixer_android_prepare_v2(handle, 0, NULL, 0, output, CAPACITY, &written, &token) == MIXER_ANDROID_V2_OK);
    const uint64_t destroyed = token;
    CHECK(mixer_android_destroy(handle) == 0);
    CHECK(mixer_android_commit_v2(handle, destroyed) == MIXER_ANDROID_V2_CLOSED);
    CHECK(mixer_android_abort_v2(handle, destroyed) == MIXER_ANDROID_V2_CLOSED);
    CHECK(mixer_android_prepare_v2(handle, 0, NULL, 0, output, CAPACITY, &written, &token) == MIXER_ANDROID_V2_CLOSED);
    CHECK(written == 0 && token == 0);
    const uint64_t replacement = mixer_android_create();
    CHECK(replacement > other);
    CHECK(mixer_android_commit_v2(replacement, destroyed) == MIXER_ANDROID_V2_STALE_TOKEN);
    CHECK(mixer_android_destroy(replacement) == 0 && mixer_android_destroy(other) == 0);
    CHECK(output[CAPACITY] == 0xA7 && initial[CAPACITY] == 0xA7);
    free(output); free(initial);
    printf("PASS %u C ABI assertions\n", checks);
    return 0;
}
