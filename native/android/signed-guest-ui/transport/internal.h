#ifndef MXUIT_INTERNAL_H
#define MXUIT_INTERNAL_H
#include "include/mixer_ui_transport.h"

/* Platform functions are fixed link symbols, never configurable callbacks. */
int32_t mxuit_platform_register(int fd);
int32_t mxuit_callback(int fd, int input_ready, int failed_event);

#ifdef MIXER_UI_TRANSPORT_TESTING
enum mxuit_test_syscall {
    MXUIT_TEST_PIPE = 1, MXUIT_TEST_FCNTL = 2,
    MXUIT_TEST_READ = 3, MXUIT_TEST_WRITE = 4
};
int32_t mxuit_test_fail_syscall(uint32_t operation, int error, uint32_t times);
int32_t mxuit_test_set_issued(uint64_t value);
int32_t mxuit_test_set_epoch(uint64_t value);
int32_t mxuit_test_set_facade_issued(uint64_t value);
int32_t mxuit_test_set_ui_entry_issued(uint64_t value);
struct mxuit_test_facade_snapshot {
    uint64_t id, current_endpoint, active_entry, last_entry_serial;
    uint32_t closing, terminal_issued;
};
int32_t mxuit_test_inspect_facade(uint64_t facade, struct mxuit_test_facade_snapshot *output);
#endif
#endif
