#ifndef MIXER_UI_BINDING_H
#define MIXER_UI_BINDING_H
#include "../../transport/include/mixer_ui_transport.h"
int32_t mxis_apply(uint64_t facade, uint64_t entry, uint64_t attachment,
                   uint64_t input, uint64_t probe,
                   const uint8_t *packet, uint32_t packet_bytes);
int32_t mxis_interaction(uint64_t facade, uint64_t entry, uint32_t enabled);
int32_t mxis_retire(uint64_t facade, uint64_t entry, uint32_t final_facade);
#endif
