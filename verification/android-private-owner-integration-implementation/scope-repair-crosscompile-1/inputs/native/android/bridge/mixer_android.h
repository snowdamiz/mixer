#ifndef MIXER_ANDROID_H
#define MIXER_ANDROID_H
#include <stdint.h>
#include <stddef.h>
/* No pointers are retained. Caller supplies valid, non-overlapping input/output
 * buffers and a writable size_t. Max input=131072/output=1048576 bytes.
 * operation0 renders; operation1 dispatches existing UIEventEnvelope JSON.
 * status0 success,1 invalid arguments,2 stale/closed handle,3 output capacity,
 * 4 rejected event/engine error. Failed operations never commit model state.
 * written receives required bytes for status3, zero for other failures.
 * Create returns0 on bounded registry exhaustion/error. Destroy invalidates
 * the monotonically assigned handle; repeated/foreign destroy returns2. */
uint64_t mixer_android_create(void);
int32_t mixer_android_destroy(uint64_t handle);
int32_t mixer_android_exchange(uint64_t handle,uint32_t operation,
    const uint8_t *input,size_t input_len,uint8_t *output,size_t output_capacity,size_t *written);
#endif
