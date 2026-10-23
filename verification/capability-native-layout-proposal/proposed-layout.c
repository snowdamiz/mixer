#include <stdint.h>
#include <stddef.h>
typedef struct MixerVmCapabilityLimitsV1 {
    uint32_t struct_size;             /* offset0, must be32 */
    uint32_t abi_version;             /* offset4, must be1 */
    uint32_t maximum_requests;        /* offset8, 1..8 */
    uint32_t timeout_milliseconds;    /* offset12, 1..30000 */
    uint32_t turn_milliseconds;       /* offset16, 1..50 */
    uint32_t reserved;                /* offset20, must be0 */
    uint64_t reservation_bytes;       /* offset24, narrowed<=8388608 */
} MixerVmCapabilityLimitsV1;           /* size32, alignment8 */

typedef struct MixerVmCapabilityMessageV1 {
    uint32_t struct_size;             /* offset0, returned40 */
    uint32_t abi_version;             /* offset4, returned1 */
    uint32_t kind;                    /* offset8: none0, call1, cancel2, tooSmall3 */
    uint32_t operation;               /* offset12: HTTP1, get2, put3, delete4 */
    uint64_t token;                   /* offset16: originating session only */
    uint32_t remaining_milliseconds;  /* offset24: private clock duration */
    uint32_t payload_length;          /* offset28: complete/required bytes */
    uint64_t reserved;                /* offset32, returned0 */
} MixerVmCapabilityMessageV1;          /* size40, alignment8 */

typedef struct MixerVmCapabilityResultV1 {
    uint32_t struct_size;             /* offset0, returned24 */
    uint32_t abi_version;             /* offset4, returned1 */
    uint32_t kind;                    /* offset8: accepted0, terminal1, acknowledged2 */
    uint32_t remaining_milliseconds;  /* offset12: deadline narrowing only */
    uint64_t reserved;                /* offset16, returned0 */
} MixerVmCapabilityResultV1;           /* size24, alignment8 */

_Static_assert(sizeof(void*) == 8, "LP64 pointer width");
_Static_assert(sizeof(size_t) == 8, "LP64 size_t width");
_Static_assert(sizeof(MixerVmCapabilityLimitsV1) == 32, "MixerVmCapabilityLimitsV1 size");
_Static_assert(_Alignof(MixerVmCapabilityLimitsV1) == 8, "MixerVmCapabilityLimitsV1 alignment");
_Static_assert(offsetof(MixerVmCapabilityLimitsV1, struct_size) == 0, "MixerVmCapabilityLimitsV1.struct_size");
_Static_assert(offsetof(MixerVmCapabilityLimitsV1, abi_version) == 4, "MixerVmCapabilityLimitsV1.abi_version");
_Static_assert(offsetof(MixerVmCapabilityLimitsV1, maximum_requests) == 8, "MixerVmCapabilityLimitsV1.maximum_requests");
_Static_assert(offsetof(MixerVmCapabilityLimitsV1, timeout_milliseconds) == 12, "MixerVmCapabilityLimitsV1.timeout_milliseconds");
_Static_assert(offsetof(MixerVmCapabilityLimitsV1, turn_milliseconds) == 16, "MixerVmCapabilityLimitsV1.turn_milliseconds");
_Static_assert(offsetof(MixerVmCapabilityLimitsV1, reserved) == 20, "MixerVmCapabilityLimitsV1.reserved");
_Static_assert(offsetof(MixerVmCapabilityLimitsV1, reservation_bytes) == 24, "MixerVmCapabilityLimitsV1.reservation_bytes");
_Static_assert(sizeof(MixerVmCapabilityMessageV1) == 40, "MixerVmCapabilityMessageV1 size");
_Static_assert(_Alignof(MixerVmCapabilityMessageV1) == 8, "MixerVmCapabilityMessageV1 alignment");
_Static_assert(offsetof(MixerVmCapabilityMessageV1, struct_size) == 0, "MixerVmCapabilityMessageV1.struct_size");
_Static_assert(offsetof(MixerVmCapabilityMessageV1, abi_version) == 4, "MixerVmCapabilityMessageV1.abi_version");
_Static_assert(offsetof(MixerVmCapabilityMessageV1, kind) == 8, "MixerVmCapabilityMessageV1.kind");
_Static_assert(offsetof(MixerVmCapabilityMessageV1, operation) == 12, "MixerVmCapabilityMessageV1.operation");
_Static_assert(offsetof(MixerVmCapabilityMessageV1, token) == 16, "MixerVmCapabilityMessageV1.token");
_Static_assert(offsetof(MixerVmCapabilityMessageV1, remaining_milliseconds) == 24, "MixerVmCapabilityMessageV1.remaining_milliseconds");
_Static_assert(offsetof(MixerVmCapabilityMessageV1, payload_length) == 28, "MixerVmCapabilityMessageV1.payload_length");
_Static_assert(offsetof(MixerVmCapabilityMessageV1, reserved) == 32, "MixerVmCapabilityMessageV1.reserved");
_Static_assert(sizeof(MixerVmCapabilityResultV1) == 24, "MixerVmCapabilityResultV1 size");
_Static_assert(_Alignof(MixerVmCapabilityResultV1) == 8, "MixerVmCapabilityResultV1 alignment");
_Static_assert(offsetof(MixerVmCapabilityResultV1, struct_size) == 0, "MixerVmCapabilityResultV1.struct_size");
_Static_assert(offsetof(MixerVmCapabilityResultV1, abi_version) == 4, "MixerVmCapabilityResultV1.abi_version");
_Static_assert(offsetof(MixerVmCapabilityResultV1, kind) == 8, "MixerVmCapabilityResultV1.kind");
_Static_assert(offsetof(MixerVmCapabilityResultV1, remaining_milliseconds) == 12, "MixerVmCapabilityResultV1.remaining_milliseconds");
_Static_assert(offsetof(MixerVmCapabilityResultV1, reserved) == 16, "MixerVmCapabilityResultV1.reserved");
int main(void) { return 0; }
