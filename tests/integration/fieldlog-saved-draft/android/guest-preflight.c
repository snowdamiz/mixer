#include <stdio.h>
#include "mixer_vm_guest_ui_deferred.h"

int main(int argc, char **argv) {
    if (argc != 3) {
        return 2;
    }
    for (int index = 1; index < argc; index++) {
        unsigned char payload[8193];
        FILE *input = fopen(argv[index], "rb");
        if (input == NULL) {
            perror(argv[index]);
            return 2;
        }
        size_t count = fread(payload, 1, sizeof payload, input);
        int badRead = ferror(input);
        if (fclose(input) != 0 || badRead || count == 0 || count == sizeof payload) {
            fprintf(stderr, "Invalid guest input: %s\n", argv[index]);
            return 2;
        }
        MixerVmReport report = {0};
        uint32_t result = mixer_vm_capability_guest_ui_validate_deferred_v1(
            payload, count, NULL, NULL, &report);
        printf("%s bytes=%zu rc=%u status=%u code=%.48s\n",
               argv[index], count, result, report.status, (const char *)report.code);
        if (result != 0 || report.status != 0) {
            return 1;
        }
    }
    return 0;
}
