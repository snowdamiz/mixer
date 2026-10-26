#include "../include/mixer_ui_transport.h"
/* Regression suites predate the required progress seam. Their unchanged test
 * bodies link this inert test-only hook; new facade probes test real dispatch. */
void mxuit_progress(uint64_t callback_fence, uint64_t ui_entry_fence, int32_t sticky_fault) {
    (void)callback_fence; (void)ui_entry_fence; (void)sticky_fault;
}
