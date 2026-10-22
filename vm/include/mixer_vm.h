#ifndef MIXER_VM_H
#define MIXER_VM_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define MIXER_VM_ABI_VERSION 1u
/* status: 0 success, 1 validation rejection, 2 execution/instantiation failure,
 * 3 invalid API arguments/limits, 4 contained internal panic. */
/* value_type: 0 void, 1 signed i32 (must fit int32_t), 2 signed i64. */
typedef struct MixerVmLimits {
    uint32_t struct_size;
    uint32_t abi_version;
    uint64_t fuel;
    uint32_t memory_pages;
    uint32_t operand_stack;
    uint32_t call_depth;
    uint32_t host_calls;
} MixerVmLimits;
typedef struct MixerVmValue {
    uint32_t value_type;
    uint32_t reserved; /* must be zero */
    int64_t value;
} MixerVmValue;
typedef struct MixerVmReport {
    uint32_t abi_version;
    uint32_t status;
    uint32_t value_type;
    uint32_t reserved;
    int64_t value;
    uint64_t fuel_used;
    uint64_t host_calls_used;
    uint32_t function; /* UINT32_MAX when no function is known */
    uint32_t offset; /* absolute byte offset in original module */
    uint8_t code[48]; /* NUL-terminated ASCII error code */
    uint8_t message[256]; /* NUL-terminated diagnostic; may truncate UTF-8 */
} MixerVmReport;
/* All input pointers must reference readable buffers for the full call; out must
 * reference writable sizeof(MixerVmReport) bytes. Inputs/out must not overlap.
 * Null data/export/args is permitted only with the corresponding length zero.
 * Null limits chooses published defaults. Non-null limits must reference the
 * full struct and match struct_size/version. Unaligned structs are accepted.
 * No pointer is retained. No Rust panic unwinds across this C ABI. This cannot
 * make dangling or otherwise invalid caller-provided pointers safe. */
uint32_t mixer_vm_validate(const uint8_t *data, size_t len,
                          const MixerVmLimits *limits, MixerVmReport *out);
/* Decode and instantiate a fresh instance for each invocation. No WASI or
 * arbitrary host callbacks are exposed by this profile. */
uint32_t mixer_vm_invoke(const uint8_t *data, size_t len,
                        const uint8_t *export_name, size_t export_len,
                        const MixerVmValue *args, size_t args_len,
                        const MixerVmLimits *limits, MixerVmReport *out);
/* Explicit opt-in numeric-v2 entry points. Existing symbols stay integer-v1.
 * value_type3 stores f32 IEEE bits in low32 bits of value (upper bits zero).
 * value_type4 stores all f64 IEEE bits in value, interpreted as uint64_t.
 * Return report uses those same bit encodings; no layout/ABI-version change.
 * Numeric-v2 rejects changed rounding, enabled hardware traps and flush modes.
 * Host FP control settings are untouched; arithmetic can set sticky flags. */
uint32_t mixer_vm_validate_numeric_v2(const uint8_t *data, size_t len,
                          const MixerVmLimits *limits, MixerVmReport *out);
uint32_t mixer_vm_invoke_numeric_v2(const uint8_t *data, size_t len,
                        const uint8_t *export_name, size_t export_len,
                        const MixerVmValue *args, size_t args_len,
                        const MixerVmLimits *limits, MixerVmReport *out);
/* Explicit table-memory-v3 entry points. Same v1 struct sizes/layouts; its
 * fixed table ceiling is 65,536 elements. No table quota field is added to the
 * legacy limits struct. Rust Limits may narrow the v3 table ceiling. */
uint32_t mixer_vm_validate_table_memory_v3(const uint8_t *data, size_t len,
                          const MixerVmLimits *limits, MixerVmReport *out);
uint32_t mixer_vm_invoke_table_memory_v3(const uint8_t *data, size_t len,
                        const uint8_t *export_name, size_t export_len,
                        const MixerVmValue *args, size_t args_len,
                        const MixerVmLimits *limits, MixerVmReport *out);
#ifdef __cplusplus
}
#endif
#endif
