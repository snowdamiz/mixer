#include <stdint.h>
#include "fixture.h"

#define MIXER_IMPORT(name) __attribute__((import_module("mixer.capability.v1"), import_name(name)))
MIXER_IMPORT("storage_get")
extern uint32_t storage_get(const void *, uint32_t, uint64_t *);
MIXER_IMPORT("poll")
extern uint32_t poll(uint64_t, void *, uint32_t, uint32_t *);

static struct {
    uint32_t magic, header_size, document, document_size, event, event_capacity, reserved[2];
    char event_bytes[4096];
} ui;
static uint64_t token;
static char response[512];

uint32_t mixer_guest_ui_start_v1(void) {
    ui.magic = 0x3155494d;
    ui.header_size = 32;
    ui.event = (uint32_t)(uintptr_t)ui.event_bytes;
    ui.event_capacity = sizeof(ui.event_bytes);
    return (uint32_t)(uintptr_t)&ui;
}

uint32_t mixer_guest_ui_hydrate_v1(void) {
#if defined(F11_PRIVATE)
    static const char query[] = "{\"key\":\"note\",\"namespace\":\"fieldlog-d8-f04-task\"}";
#else
    static const char query[] = "{\"key\":\"note\",\"namespace\":\"fieldlog-d8-f11-note\"}";
#endif
    return storage_get(query, sizeof(query) - 1, &token);
}

static int contains(const char *pattern, uint32_t length, uint32_t pattern_length) {
    for (uint32_t offset = 0; offset + pattern_length <= length; ++offset) {
        uint32_t index = 0;
        while (index < pattern_length && response[offset + index] == pattern[index]) {
            ++index;
        }
        if (index == pattern_length) {
            return 1;
        }
    }
    return 0;
}

void mixer_guest_capability_ready_v1(void) {
    uint32_t length = 0;
    uint32_t status = poll(token, response, sizeof(response), &length);
    if (status == 1) {
        return;
    }
    if (status != 0 || length > sizeof(response)) {
        __builtin_trap();
    }
    if (contains(expected_note, length, sizeof(expected_note) - 1)) {
        ui.document = (uint32_t)(uintptr_t)restored_frame;
        ui.document_size = sizeof(restored_frame) - 1;
        return;
    }
#if defined(F11_PRIVATE)
    if (contains(denied, length, sizeof(denied) - 1)) {
        ui.document = (uint32_t)(uintptr_t)unavailable_frame;
        ui.document_size = sizeof(unavailable_frame) - 1;
        return;
    }
#endif
    __builtin_trap();
}

uint32_t mixer_guest_ui_event_v1(uint32_t length) {
    (void)length;
    return 1;
}
