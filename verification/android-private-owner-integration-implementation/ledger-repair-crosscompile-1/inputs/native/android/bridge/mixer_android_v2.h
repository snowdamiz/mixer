#ifndef MIXER_ANDROID_V2_H
#define MIXER_ANDROID_V2_H
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Private ordinary-native staging, not a signed presentation capability or a
 * stable public ABI. Uses the same sessions as mixer_android_create/destroy.
 *
 * All buffers and writable metadata must be valid and nonoverlapping for the
 * call. No pointer is retained. Input <=131072 and output capacity <=1048576.
 * Operation 0 renders with no input; operation 1 dispatches UIEventEnvelope JSON.
 * The engine must preserve value semantics and have no external side effects.
 *
 * Success returns packet bytes and a nonzero session-bound token, retaining one
 * candidate engine while leaving the committed engine unchanged. The caller owns
 * the returned bytes; modifying/freeing them cannot change the retained engine.
 * While pending, another prepare and legacy exchange return BUSY. Size failure
 * returns required bytes, token zero, and retains no candidate. Other failures
 * zero each supplied metadata output. Null metadata is INVALID_ARGUMENT.
 *
 * Commit only after native attachment with actions gated and final validation.
 * Abort on failure, including downstream allocation/copy failure. Abort of the
 * last aborted token is idempotent and cannot abort a newer candidate. Commit
 * consumes a token once; foreign/stale/zero tokens fail. Destroy invalidates all
 * pending work. Handles/tokens are local to this registry, never global authority.
 * An unknown commit outcome requires retiring the session and presentation.
 */
enum mixer_android_v2_status {
    MIXER_ANDROID_V2_OK = 0,
    MIXER_ANDROID_V2_INVALID_ARGUMENT = 1,
    MIXER_ANDROID_V2_CLOSED = 2,
    MIXER_ANDROID_V2_CAPACITY = 3,
    MIXER_ANDROID_V2_ENGINE_REJECTED = 4,
    MIXER_ANDROID_V2_BUSY = 5,
    MIXER_ANDROID_V2_STALE_TOKEN = 6,
    MIXER_ANDROID_V2_EXHAUSTED = 7
};

int32_t mixer_android_prepare_v2(uint64_t handle, uint32_t operation,
    const uint8_t *input, size_t input_len, uint8_t *output,
    size_t output_capacity, size_t *written, uint64_t *token);
int32_t mixer_android_commit_v2(uint64_t handle, uint64_t token);
int32_t mixer_android_abort_v2(uint64_t handle, uint64_t token);

#ifdef __cplusplus
}
#endif
#endif
