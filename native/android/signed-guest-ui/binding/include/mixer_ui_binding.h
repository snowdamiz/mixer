#ifndef MIXER_UI_BINDING_H
#define MIXER_UI_BINDING_H
#include "../../transport/include/mixer_ui_transport.h"
int32_t mxis_apply(uint64_t facade, uint64_t entry, uint64_t attachment,
                   uint64_t input, uint64_t probe,
                   const uint8_t *packet, uint32_t packet_bytes);
int32_t mxis_interaction(uint64_t facade, uint64_t entry, uint32_t enabled);
int32_t mxis_retire(uint64_t facade, uint64_t entry, uint32_t final_facade);

enum mxis_guest_ui_witness_kind {
    MXIS_WITNESS_DRAWN = 1,
    MXIS_WITNESS_TOGGLE_TAPPED = 2
};
/* For the registered native renderer on the installation/UI thread.
 * Report a draw only after the current attached view draws. Pass its probe
 * token from mxis_apply. Report toggle activation only from the current
 * observed view's enabled callback for the node with ID "toggle", using
 * its input token.
 * Both operations use the facade and attachment from that same apply.
 * Returns mxuit_status. The call retains no native view or listener. */
int32_t mxis_guest_ui_witness(uint64_t facade, uint64_t attachment, uint64_t token, uint32_t kind);
#endif
