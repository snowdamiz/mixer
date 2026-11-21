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

int main(int argc, char **argv) {
    if (argc < 2 || argc > 7) return 64;
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

    MixerVmValue args[4] = {0};
    for (int i = 3; i < argc; i++) {
        const char *argument = argv[i];
        if (strncmp(argument, "i32:", 4) == 0) args[i - 3].value_type = 1;
        else if (strncmp(argument, "i64:", 4) == 0) args[i - 3].value_type = 2;
        else return 64;
        char *end;
        errno = 0;
        intmax_t value = strtoimax(argument + 4, &end, 10);
        if (errno || end == argument + 4 || *end) return 64;
        args[i - 3].value = value;
    }

    uint64_t handle = 0;
    status = mixer_vm_session_create_v1(3, module, size, NULL, &handle, &out);
    report("create", status, &out);
    if (status != 0 || handle == 0) return 65;
    status = mixer_vm_session_invoke_v1(handle, (const uint8_t *)argv[2],
                                        strlen(argv[2]), args, argc - 3, &out);
    report("invoke", status, &out);
    status = mixer_vm_session_close_v1(handle, &out);
    report("close", status, &out);
    return status == 0 ? 0 : 65;
}
