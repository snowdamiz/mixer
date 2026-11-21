#ifndef ALLOCATOR_CONTROL_H
#define ALLOCATOR_CONTROL_H

#include <stdint.h>

enum {
    control_magic = 827672909,
    event_offset = 32,
    event_capacity = 4096,
    document_capacity = 2048,
    page_bytes = 65536,
    block_bytes = 4096,
    block_alignment = 64,
    block_limit = 24,
    fill = 1,
    release_retry = 2,
    drain = 3,
    not_attempted = UINT32_MAX,
};

struct Observation {
    uint32_t phase;
    uint32_t pages;
    uint32_t enomem;
    uint32_t fill_attempts;
    uint32_t fill_result;
    uint32_t retry_result;
    uint32_t live;
    uint32_t checked_before_release;
    uint32_t survivors_checked;
    uint32_t replacement_checked;
    uint32_t same_address;
    uint32_t freed;
};

struct Control {
    uint32_t header[8];
    uint8_t event[event_capacity];
    struct Observation document;
    uint8_t padding[document_capacity - sizeof(struct Observation)];
};

_Static_assert(sizeof(struct Control) == 6176, "compact layout");

#endif
