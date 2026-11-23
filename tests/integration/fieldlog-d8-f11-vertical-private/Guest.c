#include <stdint.h>
#include "fixture.h"
#include "vertical.h"

#define IMPORT(name) __attribute__((import_module("mixer.capability.v1"), import_name(name)))
IMPORT("storage_get") extern uint32_t storage_get(const void *, uint32_t, uint64_t *);
IMPORT("storage_put") extern uint32_t storage_put(const void *, uint32_t, uint64_t *);
IMPORT("storage_delete") extern uint32_t storage_delete(const void *, uint32_t, uint64_t *);
IMPORT("poll") extern uint32_t poll(uint64_t, void *, uint32_t, uint32_t *);

static struct {
    uint32_t magic, header_size, document, document_size, event, event_capacity, reserved[2];
    char event_bytes[4096];
} ui;
static uint64_t token;
static enum { initial, reading, editing, awaiting_put_denial, awaiting_delete_denial, edited } phase;
static char response[512], edited_frame[1024];
static uint32_t edited_size;

static int equal(const char *a, const char *b, uint32_t length) {
    for (uint32_t i = 0; i < length; ++i)
        if (a[i] != b[i]) return 0;
    return 1;
}

static int contains(const char *needle, uint32_t length, uint32_t needle_length) {
    for (uint32_t i = 0; i + needle_length <= length; ++i)
        if (equal(response + i, needle, needle_length)) return 1;
    return 0;
}

static void paint(const char *data, uint32_t length) {
    ui.document = (uint32_t)(uintptr_t)data;
    ui.document_size = length;
}

uint32_t mixer_guest_ui_start_v1(void) {
    ui.magic = 0x3155494d;
    ui.header_size = 32;
    ui.event = (uint32_t)(uintptr_t)ui.event_bytes;
    ui.event_capacity = sizeof(ui.event_bytes);
    return (uint32_t)(uintptr_t)&ui;
}

uint32_t mixer_guest_ui_hydrate_v1(void) {
    static const char get[] = "{\"key\":\"note\",\"namespace\":\"fieldlog-d8-f11-note\"}";
    phase = reading;
    return storage_get(get, sizeof(get) - 1, &token);
}

void mixer_guest_capability_ready_v1(void) {
    uint32_t length = 0;
    uint32_t status = poll(token, response, sizeof(response), &length);
    if (status == 1) return;
    if (status != 0 || length > sizeof(response)) __builtin_trap();
    switch (phase) {
    case reading:
        if (!contains(expected_note, length, sizeof(expected_note) - 1)) __builtin_trap();
        phase = editing;
#if defined(wrong_field)
        paint(wrong_field_frame, sizeof(wrong_field_frame) - 1);
#elif defined(wrong_action)
        paint(wrong_action_frame, sizeof(wrong_action_frame) - 1);
#else
        paint(valid_frame, sizeof(valid_frame) - 1);
#endif
        return;
    case awaiting_put_denial:
    case awaiting_delete_denial: {
        static const char denied[] = "\"code\":\"permissionDenied\"";
        if (!contains(denied, length, sizeof(denied) - 1)) __builtin_trap();
        if (phase == awaiting_put_denial) {
            static const char key[] = "{\"key\":\"note\",\"namespace\":\"fieldlog-d8-f11-note\"}";
            if (storage_delete(key, sizeof(key) - 1, &token) != 0) __builtin_trap();
            phase = awaiting_delete_denial;
            return;
        }
        phase = edited;
        paint(edited_frame, edited_size);
        return;
    }
    default:
        __builtin_trap();
    }
}

uint32_t mixer_guest_ui_event_v1(uint32_t length) {
    const uint32_t prefix = sizeof(event_prefix) - 1;
    const uint32_t value_size = sizeof(expected_edit) - 1;
    if (phase != editing || length != prefix + value_size + 1 ||
        !equal(ui.event_bytes, event_prefix, prefix) ||
        !equal(ui.event_bytes + prefix, expected_edit, value_size) ||
        ui.event_bytes[length - 1] != '}') return 1;
    uint32_t size = 0;
    for (uint32_t i = 0; i < sizeof(edit_frame_prefix) - 1; ++i) edited_frame[size++] = edit_frame_prefix[i];
    for (uint32_t i = 0; i < value_size; ++i) edited_frame[size++] = ui.event_bytes[prefix + i];
    for (uint32_t i = 0; i < sizeof(edit_frame_suffix) - 1; ++i) edited_frame[size++] = edit_frame_suffix[i];
    static const char put[] = "{\"key\":\"note\",\"namespace\":\"fieldlog-d8-f11-note\",\"valueBase64\":\"AQ==\"}";
    if (storage_put(put, sizeof(put) - 1, &token) != 0) return 1;
    edited_size = size;
    phase = awaiting_put_denial;
    return 0;
}
