#include "mixer_vm.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* Independent physical-arm64 FP-control check. Input is the original minimal
 * f64 constant module; the public C ABI must fail before hardware arithmetic. */
static const uint8_t module[] = {
    0,97,115,109,1,0,0,0,1,5,1,96,0,1,124,3,2,1,0,7,7,1,3,114,117,110,0,0,
    10,13,1,11,0,68,0,0,0,0,0,0,248,63,11
};

static uint64_t read_control(void) {
    uint64_t value;
    __asm__ volatile("mrs %0, fpcr" : "=r"(value));
    return value;
}

static void set_control(uint64_t value) {
    __asm__ volatile("msr fpcr, %0\n\tisb" :: "r"(value) : "memory");
}

static void rejected_control(uint64_t original, uint64_t bit, const char *name) {
    set_control(original | bit);
    uint64_t observed = read_control();
    MixerVmReport report;
    uint32_t status = 0;
    if (observed & bit) {
        status = mixer_vm_invoke_numeric_v2(module, sizeof module,
            (const uint8_t *)"run", 3, NULL, 0, NULL, &report);
    }
    set_control(original);
    assert(read_control() == original);
    if (observed & bit) {
        assert(status == 2);
        assert(strcmp((const char *)report.code, "unsupported_float_environment") == 0);
        printf("%s: exercised and rejected; control restored\n", name);
    } else {
        printf("%s: unavailable on observed CPU; unqualified\n", name);
    }
}

int main(void) {
    uint64_t original = read_control();
    MixerVmReport report;
    assert(mixer_vm_invoke_numeric_v2(module, sizeof module,
        (const uint8_t *)"run", 3, NULL, 0, NULL, &report) == 0);
    rejected_control(original, UINT64_C(1) << 24, "flush-to-zero");
    rejected_control(original, UINT64_C(1) << 8, "invalid-operation hardware trap");
    rejected_control(original, UINT64_C(1) << 22, "rounding toward positive infinity");
    assert(mixer_vm_invoke_numeric_v2(module, sizeof module,
        (const uint8_t *)"run", 3, NULL, 0, NULL, &report) == 0);
    assert((uint64_t)report.value == UINT64_C(0x3ff8000000000000));
    puts("Independent Android C ABI control boundary: passed");
    return 0;
}
