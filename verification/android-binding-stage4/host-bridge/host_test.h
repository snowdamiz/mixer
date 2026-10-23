#ifndef MIXER_HOST_TEST_H
#define MIXER_HOST_TEST_H
#include "mixer_android_host_bridge.h"
int32_t mxish_start(void);
void mxish_pause(void);
void mxish_resume(void);
int32_t mxish_call_entry(uint64_t facade, uint32_t kind);
int32_t mxish_wait_callbacks(uint64_t count);
int32_t mxish_set_hold(uint32_t point, uint64_t facade);
int32_t mxish_wait_hold(void);
void mxish_release_hold(void);
void mxish_fail_retire(uint64_t facade);
void mxish_partial_retire(uint64_t facade);
void mxish_lose_owner(uint64_t facade);
void mxish_nested(uint64_t facade);
uint64_t mxish_nested_checks(void);
uint64_t mxish_destructors(void);
uint64_t mxish_live_allocations(void);
uint64_t mxish_process_fd_count(void);
uint64_t mxish_process_thread_count(void);
uint64_t mxish_last_id(uint64_t facade, uint32_t kind);
int32_t mxish_inject_syscall(uint32_t operation);
int32_t mxish_set_c_counter(uint32_t which, uint64_t value);
void mxish_debug_mark(uint32_t phase);
int32_t mxish_debug_wait(uint32_t phase);
void mxish_debug_release_point(void);

#endif
