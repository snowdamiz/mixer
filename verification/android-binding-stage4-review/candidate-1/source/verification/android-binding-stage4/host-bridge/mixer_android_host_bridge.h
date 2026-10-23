#ifndef MIXER_ANDROID_HOST_BRIDGE_H
#define MIXER_ANDROID_HOST_BRIDGE_H
#include <stdint.h>
struct mxis_host_snapshot {
    uint64_t facade, generation, final_entry;
    uint32_t published, cleared, tree_live, listener_live, weak_owner_live;
    uint32_t packet_bytes, interaction;
};
int32_t mxis_host_slot_acquire(uint64_t facade, uint64_t entry, uint64_t *generation);
int32_t mxis_host_inspect(uint64_t facade, uint64_t entry, struct mxis_host_snapshot *output);
int32_t mxis_host_release_destroyed(uint64_t facade, uint64_t generation);
#endif
