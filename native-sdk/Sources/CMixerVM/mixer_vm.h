#ifndef MIXER_SWIFT_FEATURE_VM_H
#define MIXER_SWIFT_FEATURE_VM_H
#include <stddef.h>
#include <stdint.h>

void *mixer_swift_ui_open_profile_v1(const uint8_t *bytes, size_t count, uint32_t profile_id);
ptrdiff_t mixer_swift_ui_frame_v1(void *owner, uint8_t *bytes, size_t capacity);
int32_t mixer_swift_ui_event_v1(void *owner, const uint8_t *bytes, size_t count);
ptrdiff_t mixer_swift_ui_error_v1(void *owner, uint8_t *bytes, size_t capacity);
int32_t mixer_swift_ui_consume_v1(void *owner, uint64_t *actual_ledger);
#endif
