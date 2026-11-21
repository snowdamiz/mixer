#ifndef HOST_EXPECTATION_H
#define HOST_EXPECTATION_H

#include "allocator_control.h"

#include <string.h>

enum { wasi_enomem = 48, expected_allocations = 9 };

_Static_assert(sizeof(struct Observation) == 12 * sizeof(uint32_t), "packed observation words");

static const struct Observation expected_observations[] = {
    [0] = {
        .pages = 1, .enomem = wasi_enomem,
        .fill_result = not_attempted, .retry_result = not_attempted,
    },
    [fill] = {
        .phase = fill, .pages = 1, .enomem = wasi_enomem,
        .fill_attempts = expected_allocations + 1, .fill_result = wasi_enomem,
        .retry_result = not_attempted, .live = expected_allocations,
    },
    [release_retry] = {
        .phase = release_retry, .pages = 1, .enomem = wasi_enomem,
        .fill_attempts = expected_allocations + 1, .fill_result = wasi_enomem,
        .live = expected_allocations, .checked_before_release = expected_allocations,
        .survivors_checked = expected_allocations - 1, .replacement_checked = 1,
        .same_address = 1, .freed = 1,
    },
    [drain] = {
        .phase = drain, .pages = 1, .enomem = wasi_enomem,
        .fill_attempts = expected_allocations + 1, .fill_result = wasi_enomem,
        .checked_before_release = expected_allocations,
        .survivors_checked = expected_allocations - 1, .replacement_checked = 1,
        .same_address = 1, .freed = expected_allocations + 1,
    },
};

static int matches_observation(uint8_t phase, struct Observation frame) {
    return phase <= drain && memcmp(&frame, &expected_observations[phase], sizeof(frame)) == 0;
}

#endif
