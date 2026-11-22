/* Link against the installed experimental capability archive and public headers. */
#include "mixer_vm_guest_ui.h"

#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_MODULE_BYTES (4 * 1024 * 1024)
static uint8_t module[MAX_MODULE_BYTES + 1];

static void report(const char *phase, uint32_t status, const MixerVmReport *out) {
    printf("%s\t%" PRIu32 "\t%" PRIu32 "\t%" PRIu32 "\t%" PRIu32
           "\t%" PRId64 "\t%" PRIu64 "\t%" PRIu64 "\t%.48s\n",
           phase, status, out->status, out->abi_version, out->value_type,
           out->value, out->fuel_used, out->host_calls_used, (const char *)out->code);
}

static int invoke(uint64_t handle, const char *phase, int argc, char **argv) {
    if (argc < 1 || argc > 5) return 64;
    MixerVmValue args[4] = {0};
    for (int i = 1; i < argc; i++) {
        const char *argument = argv[i];
        if (strncmp(argument, "i32:", 4) == 0) args[i - 1].value_type = 1;
        else if (strncmp(argument, "i64:", 4) == 0) args[i - 1].value_type = 2;
        else if (strncmp(argument, "f32:", 4) == 0) args[i - 1].value_type = 3;
        else if (strncmp(argument, "f64:", 4) == 0) args[i - 1].value_type = 4;
        else return 64;
        char *end;
        errno = 0;
        intmax_t value = strtoimax(argument + 4, &end, 10);
        if (errno || end == argument + 4 || *end) return 64;
        if (args[i - 1].value_type == 3 && (value < 0 || value > UINT32_MAX)) return 64;
        args[i - 1].value = value;
    }

    MixerVmReport out = {0};
    uint32_t status = mixer_vm_session_invoke_v1(
        handle, (const uint8_t *)argv[0], strlen(argv[0]), args, argc - 1, &out);
    report(phase, status, &out);
    return 0;
}

static int call_length(int argc, char **argv) {
    int count = 0;
    while (count < argc && strcmp(argv[count], "--") != 0) count++;
    return count;
}

static int run_session(size_t size, int argc, char **argv, int sequence, int reset) {
    MixerVmReport out = {0};
    uint64_t handle = 0;
    uint32_t status = mixer_vm_session_create_v1(3, module, size, NULL, &handle, &out);
    report(reset ? "reset-create" : "create", status, &out);
    if (status != 0 || handle == 0) return 65;

    int result = 0;
    if (sequence) {
        int start = 0;
        for (int index = 0; start < argc && result == 0; index++) {
            int length = call_length(argc - start, argv + start);
            char phase[32];
            snprintf(phase, sizeof(phase), "invoke-%d", index);
            result = invoke(handle, phase, length, argv + start);
            start += length;
            if (start == argc) break;
            if (++start == argc) result = 64;
        }
    } else {
        result = invoke(handle, reset ? "reset-invoke" : "invoke", argc, argv);
    }

    status = mixer_vm_session_close_v1(handle, &out);
    report(reset ? "reset-close" : "close", status, &out);
    return status == 0 ? result : 65;
}

int main(int argc, char **argv) {
    if (argc < 2) return 64;
    FILE *file = fopen(argv[1], "rb");
    if (!file) return 66;
    size_t size = fread(module, 1, sizeof(module), file);
    int read_error = ferror(file);
    if (fclose(file) || read_error || size == 0 || size > MAX_MODULE_BYTES) return 66;

    MixerVmReport out = {0};
    uint32_t status;
    if (argc == 2) {
        status = mixer_vm_validate_table_memory_v3(module, size, NULL, &out);
        report("validate", status, &out);
        status = mixer_vm_capability_guest_ui_validate_v1(module, size, NULL, NULL, &out);
        report("guest_ui_v1_validate", status, &out);
        return 0;
    }

    if (strcmp(argv[2], "--sequence") != 0) {
        return run_session(size, argc - 2, argv + 2, 0, 0);
    }
    if (argc < 4) return 64;
    int result = run_session(size, argc - 3, argv + 3, 1, 0);
    if (result != 0) return result;
    return run_session(size, call_length(argc - 3, argv + 3), argv + 3, 0, 1);
}
