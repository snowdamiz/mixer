#if defined(__linux__)
#define _GNU_SOURCE
#endif
#include "MixerProcessIO.h"
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#ifdef __APPLE__
#include <spawn.h>
#elif defined(__linux__)
#include <sys/syscall.h>
#endif

static int descriptor_flags(int fd, int nonblocking) {
    if (fcntl(fd, F_SETFD, FD_CLOEXEC) == -1) return errno;
    if (nonblocking) {
        int flags = fcntl(fd, F_GETFL);
        if (flags == -1 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) == -1) return errno;
    }
    return 0;
}
static void child_report(int fd, int status) {
    const char *p = (const char *)&status;
    size_t left = sizeof(status);
    while (left) {
        ssize_t n = write(fd, p, left);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) _exit(126);
        p += n; left -= (size_t)n;
    }
}
int mx_launch(char *const argv[], char *const environment[], const char *cwd, mx_child *child) {
    int out[2] = {-1, -1}, err[2] = {-1, -1}, gate[2] = {-1, -1}, status = 0;
    *child = (mx_child){0, -1, -1, -1};
#ifdef __APPLE__
    // Build the complete exec whitelist before fork; the child never allocates spawn objects.
    posix_spawnattr_t attributes; posix_spawn_file_actions_t actions;
    int attributes_ready = 0, actions_ready = 0;
    if ((status = posix_spawnattr_init(&attributes))) return status;
    attributes_ready = 1;
    if ((status = posix_spawn_file_actions_init(&actions))) goto failed;
    actions_ready = 1;
    if ((status = posix_spawnattr_setflags(&attributes, POSIX_SPAWN_SETEXEC | POSIX_SPAWN_CLOEXEC_DEFAULT))) goto failed;
    for (int fd = 0; fd < 3; ++fd) {
        if ((status = posix_spawn_file_actions_addinherit_np(&actions, fd))) goto failed;
    }
#elif !defined(__linux__) || !defined(SYS_close_range)
    return ENOTSUP;
#endif
    if (pipe(out) || pipe(err) || socketpair(AF_UNIX, SOCK_STREAM, 0, gate)) { status = errno; goto failed; }
    int *descriptors[] = {&out[0], &out[1], &err[0], &err[1], &gate[0], &gate[1]};
    for (size_t i = 0; i < 6; ++i) {
        if (*descriptors[i] < 3) {
            int replacement = fcntl(*descriptors[i], F_DUPFD_CLOEXEC, 3);
            if (replacement < 0) { status = errno; goto failed; }
            if (close(*descriptors[i])) { status = errno; close(replacement); goto failed; }
            *descriptors[i] = replacement;
        }
    }
    for (int i = 0; i < 2; ++i) {
        if ((status = descriptor_flags(out[i], i == 0)) ||
            (status = descriptor_flags(err[i], i == 0)) ||
            (status = descriptor_flags(gate[i], i == 0))) goto failed;
    }
#ifdef __APPLE__
    { int enabled = 1; if (setsockopt(gate[0], SOL_SOCKET, SO_NOSIGPIPE, &enabled, sizeof(enabled))) { status = errno; goto failed; } }
#endif
    pid_t pid = fork();
    if (pid < 0) { status = errno; goto failed; }
    if (pid == 0) {
        /* No allocation, Foundation, locks, or non-async-signal-safe runtime here. */
        close(out[0]); close(err[0]); close(gate[0]);
        if (setsid() == -1) { child_report(gate[1], errno); _exit(126); }
        int null_fd = open("/dev/null", O_RDONLY);
        if (null_fd < 0 || dup2(null_fd, 0) == -1 || dup2(out[1], 1) == -1 || dup2(err[1], 2) == -1) {
            child_report(gate[1], errno); _exit(126);
        }
        if (cwd && chdir(cwd) == -1) { child_report(gate[1], errno); _exit(126); }
        struct sigaction action;
        memset(&action, 0, sizeof(action)); action.sa_handler = SIG_DFL; sigemptyset(&action.sa_mask);
        for (int s = 1; s < NSIG; ++s) if (s != SIGKILL && s != SIGSTOP) sigaction(s, &action, NULL);
        sigset_t empty; sigemptyset(&empty); sigprocmask(SIG_SETMASK, &empty, NULL);
        // Complete descriptor retirement is independent of the current RLIMIT_NOFILE.
#if defined(__linux__) && defined(SYS_close_range)
        // Keep the readiness channel usable until release; all nonstdio fds close at exec.
        if (syscall(SYS_close_range, 3U, UINT_MAX, 1U << 2) == -1) { child_report(gate[1], errno); _exit(126); }
#endif
        child_report(gate[1], 0);
        char release = 0; ssize_t n;
        do { n = read(gate[1], &release, 1); } while (n < 0 && errno == EINTR);
        if (n != 1 || release != 'R') _exit(126);
        if (close(gate[1])) _exit(126);
#ifdef __APPLE__
        // Darwin SETEXEC replaces this gated leader, with only 0/1/2 inherited.
        // All spawn allocation/initialization was completed in the parent.
        posix_spawn(NULL, "/usr/bin/env", &actions, &attributes, argv, environment);
#else
        execve("/usr/bin/env", argv, environment);
#endif
        _exit(127);
    }
    /* Ownership is returned even if closing a parent descriptor fails. */
    *child = (mx_child){(int32_t)pid, out[0], err[0], gate[0]};
    if (close(out[1]) == -1) status = errno;
    if (close(err[1]) == -1 && !status) status = errno;
    if (close(gate[1]) == -1 && !status) status = errno;
    goto finished;
failed:
    for (int i = 0; i < 2; ++i) { if (out[i] >= 0) close(out[i]); if (err[i] >= 0) close(err[i]); if (gate[i] >= 0) close(gate[i]); }
finished:
#ifdef __APPLE__
    if (actions_ready) { int code = posix_spawn_file_actions_destroy(&actions); if (!status) status = code; }
    if (attributes_ready) { int code = posix_spawnattr_destroy(&attributes); if (!status) status = code; }
#endif
    return status;
}
ssize_t mx_read(int fd, void *bytes, size_t capacity, int *error) {
    ssize_t n = read(fd, bytes, capacity); *error = n < 0 ? errno : 0; return n;
}
int mx_release(int fd) {
#ifdef MSG_NOSIGNAL
    ssize_t n = send(fd, "R", 1, MSG_NOSIGNAL);
#else
    ssize_t n = send(fd, "R", 1, 0);
#endif
    return n == 1 ? 0 : (n < 0 ? errno : EIO);
}
int mx_peek_exit(int32_t pid, int *exited) {
    siginfo_t info; memset(&info, 0, sizeof(info));
    if (waitid(P_PID, (id_t)pid, &info, WEXITED | WNOHANG | WNOWAIT)) return errno;
    *exited = info.si_pid == pid; return 0;
}
int mx_kill_group(int32_t pid) {
    if (pid <= 1) return EINVAL;
    if (kill(-pid, SIGKILL) == 0 || errno == ESRCH) return 0;
    return errno;
}
int mx_reap(int32_t pid, int32_t *exit_code, int *reaped) {
    int status = 0; pid_t result = waitpid(pid, &status, WNOHANG);
    if (result < 0) return errno;
    *reaped = result == pid;
    if (*reaped) {
        if (WIFEXITED(status)) *exit_code = WEXITSTATUS(status);
        else if (WIFSIGNALED(status)) *exit_code = WTERMSIG(status);
        else return EPROTO;
    }
    return 0;
}
int mx_group_absent(int32_t pid, int *absent) {
    if (pid <= 1) return EINVAL;
    if (kill(-pid, 0) == 0) { *absent = 0; return 0; }
    if (errno == ESRCH) { *absent = 1; return 0; }
    return errno;
}
int mx_close(int fd) { return close(fd) == 0 ? 0 : errno; }
uint64_t mx_monotonic_ns(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return 0;
    return (uint64_t)t.tv_sec * 1000000000ULL + (uint64_t)t.tv_nsec;
}
int mx_pause_ms(int milliseconds) {
    struct timespec delay = {milliseconds / 1000, (milliseconds % 1000) * 1000000L};
    return nanosleep(&delay, NULL) == 0 || errno == EINTR ? 0 : errno;
}
int mx_persist(const char *staging, const char *destination, const char *directory, const void *bytes, size_t count) {
    int fd = open(staging, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (fd < 0) return errno;
    int status = 0; const char *p = bytes;
    while (count) {
        ssize_t n = write(fd, p, count);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) { status = n < 0 ? errno : EIO; break; }
        p += n; count -= (size_t)n;
    }
    if (!status && fsync(fd)) status = errno;
    if (close(fd) && !status) status = errno;
    if (status) return status;
    if (rename(staging, destination)) return errno;
    int parent = open(directory, O_RDONLY | O_CLOEXEC);
    if (parent < 0) return errno;
    if (fsync(parent)) status = errno;
    if (close(parent) && !status) status = errno;
    return status;
}

int mx_sync_directory(const char *path) {
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) return errno;
    int status = fsync(fd) == 0 ? 0 : errno;
    if (close(fd) && !status) status = errno;
    return status;
}
