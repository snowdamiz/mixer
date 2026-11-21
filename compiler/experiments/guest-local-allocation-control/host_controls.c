#include "host_expectation.h"

#include <stdio.h>
#include <stdlib.h>

static unsigned failures;

static void check(int condition, const char *label) {
    if (!condition) {
        fprintf(stderr, "%s\n", label);
        failures++;
    }
}

int main(void) {
    const struct Observation filled = {
        .phase = fill, .pages = 1, .enomem = 48, .fill_attempts = 10,
        .fill_result = 48, .retry_result = not_attempted, .live = 9,
    };
    struct Observation different_count = filled;
    different_count.fill_attempts = 9;
    different_count.live = 8;
    check(matches_observation(fill, filled), "exact count refused");
    check(!matches_observation(fill, different_count), "different successful allocation count accepted");

    const struct Observation reclaimed = {
        .phase = release_retry, .pages = 1, .enomem = 48, .fill_attempts = 10,
        .fill_result = 48, .retry_result = 0, .live = 9, .checked_before_release = 9,
        .survivors_checked = 8, .replacement_checked = 1, .same_address = 1, .freed = 1,
    };
    struct Observation refused = reclaimed;
    refused.retry_result = 48;
    refused.live = 8;
    refused.replacement_checked = 0;
    refused.same_address = 0;
    struct Observation different_address = reclaimed;
    different_address.same_address = 0;
    check(matches_observation(release_retry, reclaimed), "exact address retry refused");
    check(!matches_observation(release_retry, refused), "ENOMEM on retry accepted");
    check(!matches_observation(release_retry, different_address), "different address on retry accepted");
    if (failures != 0) {
        return EXIT_FAILURE;
    }
    puts("host refused wrong count, failed retry and different-address retry");
    return EXIT_SUCCESS;
}
