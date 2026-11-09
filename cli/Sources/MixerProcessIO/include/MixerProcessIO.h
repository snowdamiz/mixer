#ifndef MIXER_PROCESS_IO_H
#define MIXER_PROCESS_IO_H
#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>
typedef struct { int32_t pid; int stdout_fd; int stderr_fd; int gate_fd; } mx_child;
int mx_launch(char *const argv[], char *const environment[], const char *cwd, mx_child *child);
ssize_t mx_read(int fd, void *bytes, size_t capacity, int *error);
int mx_release(int fd);
int mx_peek_exit(int32_t pid, int *exited);
int mx_kill_group(int32_t pid);
int mx_reap(int32_t pid, int32_t *exit_code, int *reaped);
int mx_group_absent(int32_t pid, int *absent);
int mx_close(int fd);
uint64_t mx_monotonic_ns(void);
int mx_pause_ms(int milliseconds);
int mx_sync_directory(const char *path);
int mx_persist(const char *staging, const char *destination, const char *directory, const void *bytes, size_t count);
#endif
