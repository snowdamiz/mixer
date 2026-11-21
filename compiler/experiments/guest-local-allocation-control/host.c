#include "host_expectation.h"
#include "mixer_vm_guest_ui.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const uint8_t startup[] = "mixer_guest_ui_start_v1";
static const uint8_t event[] = "mixer_guest_ui_event_v1";
static const MixerVmLimits limits = {
    sizeof(MixerVmLimits), MIXER_VM_ABI_VERSION, 1000000, 1, 4096, 64, 0,
};
static const MixerVmCapabilityLimitsV1 caps = {
    sizeof(MixerVmCapabilityLimitsV1), MIXER_VM_CAPABILITY_ABI_VERSION, 8, 30000, 50, 0, 8388608,
};

static uint64_t active;
static uint32_t input_offset;
static uint32_t document_offset;
static MixerVmReport report;
static uint8_t module[page_bytes];

static void cleanup(void) {
    if (active != 0) {
        uint32_t code = mixer_vm_capability_session_close_v1(active, &report);
        fprintf(stderr, "failure-path close: %" PRIu32 " (%s)\n", code, (char *)report.code);
    }
}

static void check(int condition, const char *where) {
    if (!condition) {
        fprintf(stderr, "%s failed\n", where);
        exit(1);
    }
}

static void expect_status(const char *where, uint32_t status, uint32_t expected) {
    if (status != expected || report.status != status || report.abi_version != MIXER_VM_ABI_VERSION ||
        report.host_calls_used != 0) {
        fprintf(stderr, "%s: status=%" PRIu32 " report=%" PRIu32 " hostCalls=%" PRIu64
                " fuel=%" PRIu64 " code=%s message=%s\n", where, status, report.status,
                report.host_calls_used, report.fuel_used, (char *)report.code, (char *)report.message);
        exit(1);
    }
}

static uint64_t open_session(size_t length) {
    expect_status("create", mixer_vm_capability_session_create_v1(
        module, length, startup, sizeof(startup) - 1, &limits, &caps, &active, &report), 0);
    check(active != 0, "created handle");
    expect_status("startup", mixer_vm_capability_session_startup_v1(active, &report), 0);
    const int64_t last_header_start = page_bytes - (int64_t)sizeof(struct Control);
    check(report.value_type == 1 && report.value > 0 &&
          report.value <= last_header_start, "startup header address");
    uint32_t base = (uint32_t)report.value;
    uint64_t startup_fuel = report.fuel_used;
    check(startup_fuel > 0 && startup_fuel <= limits.fuel, "startup fuel");
    expect_status("ready", mixer_vm_capability_session_enable_v1(active, &report), 0);

    uint32_t header[8];
    expect_status("header read", mixer_vm_capability_session_read_v1(
        active, base, (uint8_t *)header, sizeof(header), &report), 0);
    check(header[0] == control_magic && header[1] == event_offset &&
          header[2] == base + event_offset + event_capacity &&
          header[3] == sizeof(struct Observation) && header[4] == base + event_offset &&
          header[5] == event_capacity && header[6] == 0 && header[7] == 0, "compact header");
    input_offset = header[4];
    document_offset = header[2];
    return startup_fuel;
}

static struct Observation frame(void) {
    struct Observation o;
    expect_status("document read", mixer_vm_capability_session_read_v1(
        active, document_offset, (uint8_t *)&o, sizeof(o), &report), 0);
    check(o.pages == 1 && o.enomem == wasi_enomem, "runtime memory size and pinned WASI ENOMEM");
    return o;
}

static struct Observation turn(uint8_t phase, uint64_t *fuel) {
    expect_status("event write", mixer_vm_capability_session_write_v1(
        active, input_offset, &phase, 1, &report), 0);
    const MixerVmValue length = {1, 0, 1};
    expect_status("event invoke", mixer_vm_capability_session_invoke_v1(
        active, event, sizeof(event) - 1, &length, 1, &report), 0);
    check(report.value_type == 1 && report.value == 0, "guest event acknowledgement");
    *fuel = report.fuel_used;
    check(*fuel > 0 && *fuel <= limits.fuel, "bounded event fuel");
    struct Observation o = frame();
    check(o.phase == phase, "frame phase");
    return o;
}

static void print_frame(struct Observation o, uint64_t fuel) {
    printf("{\"phase\":%u,\"pages\":%u,\"fuel\":%" PRIu64 ",\"hostCalls\":0,\"enomem\":%u,"
           "\"fillAttempts\":%u,\"fillResult\":%u,\"retryResult\":%u,\"live\":%u,"
           "\"checkedBeforeRelease\":%u,\"survivorsChecked\":%u,\"replacementChecked\":%u,"
           "\"sameAddress\":%u,\"freed\":%u}\n",
           o.phase, o.pages, fuel, o.enomem, o.fill_attempts, o.fill_result, o.retry_result,
           o.live, o.checked_before_release, o.survivors_checked, o.replacement_checked,
           o.same_address, o.freed);
}

static void exercise(struct Observation initial, uint64_t startup_fuel) {
    check(matches_observation(0, initial), "fresh session state");
    print_frame(initial, startup_fuel);

    uint64_t fuel;
    struct Observation filled = turn(fill, &fuel);
    check(matches_observation(fill, filled), "nine allocations then WASI ENOMEM on attempt ten");
    print_frame(filled, fuel);

    struct Observation retry = turn(release_retry, &fuel);
    check(matches_observation(release_retry, retry), "exact-address retry and survivor canaries");
    print_frame(retry, fuel);

    struct Observation drained = turn(drain, &fuel);
    check(matches_observation(drain, drained), "ten successful allocations freed");
    print_frame(drained, fuel);
}

static uint64_t close_session(void) {
    uint64_t retired = active;
    expect_status("close", mixer_vm_capability_session_close_v1(active, &report), 0);
    active = 0;
    expect_status("closed generation refused", mixer_vm_capability_session_startup_v1(retired, &report), 3);
    printf("{\"closeStatus\":0,\"retiredStartupStatus\":3}\n");
    return retired;
}

int main(int argc, char **argv) {
    check(argc == 2 && atexit(cleanup) == 0, "arguments and cleanup");
    FILE *file = fopen(argv[1], "rb");
    check(file != NULL, "open linked fixture");
    size_t length = fread(module, 1, sizeof(module), file);
    check(length > 0 && feof(file) && !ferror(file), "read bounded fixture");
    check(fclose(file) == 0, "close fixture");

    expect_status("Guest UI V1 validation", mixer_vm_capability_guest_ui_validate_v1(
        module, length, &limits, &caps, &report), 0);
    printf("{\"guestUiV1ValidationStatus\":0}\n");

    uint64_t fuel = open_session(length);
    struct Observation first = frame();
    exercise(first, fuel);
    uint64_t retired = close_session();

    fuel = open_session(length);
    struct Observation fresh = frame();
    check(active != retired && (uint32_t)active == (uint32_t)retired, "registry generation and slot reuse");
    expect_status("retired generation refused after reopen",
                  mixer_vm_capability_session_startup_v1(retired, &report), 3);
    check(memcmp(&first, &fresh, sizeof(first)) == 0, "identical reopened frame");
    printf("{\"sameRegistrySlot\":true,\"newGeneration\":true,\"retiredAfterReopenStatus\":3,"
           "\"identicalFreshFrame\":true}\n");
    exercise(fresh, fuel);
    close_session();
    return 0;
}
