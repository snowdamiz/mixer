/* Declaration fixture only. No implementations, witnesses or native authority. */
#include <stdint.h>
#include <stddef.h>
#include "mixer_ui_binding.h"
struct mxis_native_slot {
    uint64_t facade, slot_generation, attach_serial, final_entry;
    uint64_t attachment, input, probe;
    uint32_t disposition, packet_bytes;
};
int32_t mxis_apply(uint64_t facade, uint64_t entry, uint64_t attachment, uint64_t input, uint64_t probe, const uint8_t *packet, uint32_t packet_bytes);
int32_t mxis_interaction(uint64_t facade, uint64_t entry, uint32_t enabled);
int32_t mxis_retire(uint64_t facade, uint64_t entry, uint32_t final_facade);
int32_t mxisi_attach_begin(uint64_t facade, uint64_t entry, uint64_t presentation, uint64_t *attach_serial);
int32_t mxisi_attach_commit(uint64_t facade, uint64_t entry, uint64_t presentation, uint64_t attach_serial, uint64_t slot_generation);
int32_t mxisi_attach_abort(uint64_t facade, uint64_t entry, uint64_t attach_serial, uint32_t failure);
int32_t mxisi_activate(uint64_t facade, uint64_t entry, uint64_t attachment, uint64_t input, uint64_t revision, const uint8_t *node_id, uint32_t node_id_bytes, uint64_t generation);
int32_t mxisi_observe(uint64_t facade, uint64_t entry, uint64_t attachment, uint64_t probe, uint64_t draw_serial, uint64_t frame_time_nanos);
int32_t mxisi_request_close(uint64_t facade, uint32_t reason);
int32_t mxisi_detach_ui(uint64_t facade, uint64_t entry, uint64_t attachment);
int32_t mxis_native_slot_read(uint64_t facade, uint64_t entry, struct mxis_native_slot *out);
int32_t mxis_native_observation_take(uint64_t facade, uint64_t entry, uint64_t attachment, uint64_t probe, uint64_t draw_serial, uint64_t frame_time_nanos);
int32_t mxis_native_slot_reserve(uint64_t facade, uint64_t *slot_generation);
int32_t mxis_native_slot_release(uint64_t facade, uint64_t slot_generation, uint64_t final_entry);
int32_t mxis_native_slot_abort_empty(uint64_t facade, uint64_t slot_generation);
#if defined(__cplusplus)
static_assert(sizeof(mxis_native_slot) == 64, "slot size");
static_assert(alignof(mxis_native_slot) == 8, "slot alignment");
static_assert(offsetof(mxis_native_slot, disposition) == 56, "slot fields");
#else
_Static_assert(sizeof(struct mxis_native_slot) == 64, "slot size");
_Static_assert(_Alignof(struct mxis_native_slot) == 8, "slot alignment");
_Static_assert(offsetof(struct mxis_native_slot, disposition) == 56, "slot fields");
#endif
