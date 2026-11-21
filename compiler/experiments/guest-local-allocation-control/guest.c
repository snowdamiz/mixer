#define _POSIX_C_SOURCE 200112L
#include "allocator_control.h"

#include <errno.h>
#include <stdlib.h>

static struct Control control;
static void *blocks[block_limit];
static uint32_t tags[block_limit];

static int canaries(uint32_t index, int write) {
    if (blocks[index] == NULL) {
        return 0;
    }
    uintptr_t address = (uintptr_t)blocks[index];
    if (address % block_alignment != 0 || address > page_bytes - block_bytes) {
        return 0;
    }
    volatile uint8_t *bytes = blocks[index];
    const unsigned offsets[] = {0, block_bytes / 2, block_bytes - 1};
    for (unsigned i = 0; i < sizeof(offsets) / sizeof(offsets[0]); i++) {
        uint8_t expected = (uint8_t)(tags[index] + 53 * i);
        if (write) {
            bytes[offsets[i]] = expected;
        } else if (bytes[offsets[i]] != expected) {
            return 0;
        }
    }
    return 1;
}

static int fill_heap(struct Observation *o) {
    while (o->live < block_limit) {
        void *block = NULL;
        uint32_t index = o->live;
        int status = posix_memalign(&block, block_alignment, block_bytes);
        o->fill_attempts++;
        if (status != 0) {
            o->fill_result = (uint32_t)status;
            return status == ENOMEM && o->live >= 3;
        }
        blocks[index] = block;
        tags[index] = index + 1;
        o->live++;
        if (!canaries(index, 1)) {
            return 0;
        }
    }
    return 0;
}

static int reclaim(struct Observation *o) {
    uint32_t count = o->live;
    uint32_t hole = count / 2;
    for (uint32_t i = 0; i < count; i++) {
        if (!canaries(i, 0)) {
            return 0;
        }
        o->checked_before_release++;
    }

    uintptr_t released_address = (uintptr_t)blocks[hole];
    free(blocks[hole]);
    blocks[hole] = NULL;
    o->freed++;
    o->live--;

    void *replacement = NULL;
    o->retry_result = (uint32_t)posix_memalign(&replacement, block_alignment, block_bytes);
    if (o->retry_result == 0) {
        blocks[hole] = replacement;
        tags[hole] = block_limit + 1;
        o->same_address = (uintptr_t)replacement == released_address;
        o->live++;
        if (!canaries(hole, 1) || !canaries(hole, 0)) {
            return 0;
        }
        o->replacement_checked = 1;
    } else if (o->retry_result != ENOMEM) {
        return 0;
    }

    for (uint32_t i = 0; i < count; i++) {
        if (i == hole) {
            continue;
        }
        if (!canaries(i, 0)) {
            return 0;
        }
        o->survivors_checked++;
    }
    return 1;
}

static int drain_heap(struct Observation *o) {
    for (uint32_t i = 0; i < block_limit; i++) {
        if (blocks[i] != NULL) {
            if (!canaries(i, 0)) {
                return 0;
            }
            free(blocks[i]);
            blocks[i] = NULL;
            o->freed++;
            o->live--;
        }
    }
    return o->live == 0;
}

uint32_t mixer_guest_ui_start_v1(void) {
    control.header[0] = control_magic;
    control.header[1] = event_offset;
    control.header[2] = (uint32_t)(uintptr_t)&control.document;
    control.header[3] = sizeof(control.document);
    control.header[4] = (uint32_t)(uintptr_t)control.event;
    control.header[5] = event_capacity;
    control.document.pages = __builtin_wasm_memory_size(0);
    control.document.enomem = ENOMEM;
    control.document.fill_result = not_attempted;
    control.document.retry_result = not_attempted;
    return (uint32_t)(uintptr_t)&control;
}

uint32_t mixer_guest_ui_event_v1(uint32_t length) {
    struct Observation *o = &control.document;
    if (length != 1 || control.event[0] != o->phase + 1) {
        return 1;
    }
    int ok;
    switch (control.event[0]) {
    case fill: ok = fill_heap(o); break;
    case release_retry: ok = reclaim(o); break;
    case drain: ok = drain_heap(o); break;
    default: return 1;
    }
    if (!ok) {
        return 1;
    }
    o->phase++;
    o->pages = __builtin_wasm_memory_size(0);
    return 0;
}

void mixer_guest_capability_ready_v1(void) {}
