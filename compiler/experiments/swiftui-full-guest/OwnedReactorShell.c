#include "OwnedReactorShell.h"

#include <inttypes.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>

#if defined(__ANDROID__)
#include <sys/system_properties.h>
#elif defined(__APPLE__)
#include <mach/mach.h>
#endif

extern int mixer_s2b_replay(const char *path, bool fixed34);

static uint64_t main_started;

static uint64_t monotonic_micros(void) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
        perror("clock_gettime");
        exit(11);
    }
    return (uint64_t)now.tv_sec * 1000000 + (uint64_t)now.tv_nsec / 1000;
}

static uint64_t resident_bytes(void) {
#if defined(__ANDROID__)
    FILE *status = fopen("/proc/self/status", "r");
    if (!status) {
        return 0;
    }
    char line[256];
    uint64_t kib = 0;
    while (fgets(line, sizeof(line), status)) {
        if (sscanf(line, "VmRSS: %" SCNu64 " kB", &kib) == 1) {
            break;
        }
    }
    fclose(status);
    return kib * 1024;
#elif defined(__APPLE__)
    mach_task_basic_info_data_t memory;
    mach_msg_type_number_t count = MACH_TASK_BASIC_INFO_COUNT;
    return task_info(mach_task_self(), MACH_TASK_BASIC_INFO, (task_info_t)&memory, &count)
        == KERN_SUCCESS ? memory.resident_size : 0;
#endif
}

void mixer_s2b_checkpoint(const char *stage, size_t length, uint64_t elapsed_micros) {
    uint64_t since_main = monotonic_micros() - main_started;
    uint64_t rss = resident_bytes();
    struct rusage usage;
    uint64_t peak = 0;
    if (getrusage(RUSAGE_SELF, &usage) == 0 && usage.ru_maxrss > 0) {
        peak = (uint64_t)usage.ru_maxrss;
#if defined(__ANDROID__)
        peak *= 1024;
#endif
    }
    fprintf(stderr, "s2b_stage=%.*s elapsed_us=%" PRIu64 " since_main_us=%" PRIu64
            " rss_bytes=%" PRIu64 " peak_rss_bytes=%" PRIu64 "\n",
            (int)length, stage, elapsed_micros, since_main, rss, peak);
}

#define CHECKPOINT(stage) mixer_s2b_checkpoint(stage, sizeof(stage) - 1, 0)

_Noreturn void mixer_s2b_finish(int status) {
    CHECKPOINT("pre_exit");
    fprintf(stderr, "s2b_exit=%d pid=%d\n", status, getpid());
    exit(status);
}

int main(int argc, char *argv[]) {
    main_started = monotonic_micros();
    if (argc != 2) {
        fprintf(stderr, "Expected one mode: native, ui256 or fixed34\n");
        return 11;
    }
    const char *mode = argv[1];
    const bool native = strcmp(mode, "native") == 0;
    const bool fixed34 = strcmp(mode, "fixed34") == 0;
    if (!native && !fixed34 && strcmp(mode, "ui256") != 0) {
        fprintf(stderr, "Unknown mode: %s\n", mode);
        return 11;
    }
#if defined(__ANDROID__)
    char api[PROP_VALUE_MAX];
    if (__system_property_get("ro.build.version.sdk", api) <= 0 || strcmp(api, "28") != 0) {
        fprintf(stderr, "The matched Android measurement requires API 28\n");
        return 11;
    }
    const char *platform = "android-api28";
#elif defined(__APPLE__)
    const char *platform = "macos";
#endif
    fprintf(stderr, "s2b_start=%s pid=%d platform=%s\n", mode, getpid(), platform);
    CHECKPOINT("baseline");
    if (native) {
        mixer_s2b_start_native();
        mixer_s2b_finish(20);
    }
    mixer_s2b_finish(mixer_s2b_replay("./reactor-base.wasm", fixed34));
}
