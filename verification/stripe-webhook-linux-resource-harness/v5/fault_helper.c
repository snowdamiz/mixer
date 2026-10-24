/* Mixer-owned private Linux launcher and finite resource faults. No setuid bit.
 * Setup runs in the selected child cgroup before a namespace/role/helper fork.
 * This file deliberately has no host-stress or namespace-less fallback.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <unistd.h>
#ifdef __linux__
#include <fcntl.h>
#include <signal.h>
#include <time.h>
#include <limits.h>
#include <sched.h>
#include <dirent.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <sys/mman.h>
#include <net/if.h>
#include <linux/capability.h>
#include <grp.h>

static volatile sig_atomic_t child_pid = -1;
static const char *fault_stage = "none";
static void lifecycle(unsigned stage, const char *name) {
    if (strcmp(fault_stage, name) == 0) {
        printf("{\"schema\":1,\"event\":\"lifecycle\",\"stage\":%u,\"reached\":1,\"injected\":1}\n", stage);
        if (fflush(stdout) != 0) _exit(78);
        _exit(79);
    }
}
static unsigned long namespace_inode(const char *kind) {
    char path[80];
    struct stat st;
    int n = snprintf(path, sizeof(path), "/proc/self/ns/%s", kind);
    if (n <= 0 || (size_t)n >= sizeof(path) || stat(path, &st) != 0) _exit(78);
    return (unsigned long)st.st_ino;
}
static void namespaces_observed(int pid_namespace_active) {
    printf("{\"schema\":1,\"event\":\"namespace\",\"pidNs\":%lu,\"mountNs\":%lu,\"netNs\":%lu,\"ipcNs\":%lu,\"utsNs\":%lu}\n",
        pid_namespace_active ? namespace_inode("pid") : 0UL, namespace_inode("mnt"), namespace_inode("net"),
        namespace_inode("ipc"), namespace_inode("uts"));
    if (fflush(stdout) != 0) _exit(78);
}
static void forward(int sig) { if (child_pid > 0) (void)kill((pid_t)child_pid, sig); }
static void die(void) { _exit(78); }
static void check(int ok) { if (!ok) die(); }
static uint64_t monotonic_ns(void) {
    struct timespec ts;
    check(clock_gettime(CLOCK_MONOTONIC, &ts) == 0);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}
static void pathcat(char *out, size_t n, const char *a, const char *b) {
    int r = snprintf(out, n, "%s/%s", a, b);
    check(r > 0 && (size_t)r < n);
}
static void exact_write(int fd, const char *s) {
    size_t n = strlen(s);
    check(write(fd, s, n) == (ssize_t)n);
}
static void close_fds_except_control(int control) {
    if (control != 3) check(dup2(control, 3) == 3);
    check(fcntl(3, F_SETFD, 0) == 0);
    /* close_range is mandatory; do not silently leave high inherited FDs. */
    check(syscall(SYS_close_range, 4U, ~0U, 0U) == 0);
}
static void limits(void) {
    struct rlimit none = {0, 0}, files = {256, 256};
    check(setrlimit(RLIMIT_CORE, &none) == 0);
    check(setrlimit(RLIMIT_FSIZE, &none) == 0);
    check(setrlimit(RLIMIT_NOFILE, &files) == 0);
    check(prctl(PR_SET_DUMPABLE, 0, 0, 0, 0) == 0);
}
static void drop_privileges(void) {
    /* Drop bounding set while privileged, then all IDs and all cap sets. */
    int last = 0;
    FILE *f = fopen("/proc/sys/kernel/cap_last_cap", "re");
    check(f != NULL && fscanf(f, "%d", &last) == 1 && last >= 0 && last <= 63);
    check(fclose(f) == 0);
    for (int cap = 0; cap <= last; cap++) check(prctl(PR_CAPBSET_DROP, cap, 0, 0, 0) == 0);
    check(prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL, 0, 0, 0) == 0);
    check(setgroups(0, NULL) == 0);
    check(setresgid(65534, 65534, 65534) == 0);
    check(setresuid(65534, 65534, 65534) == 0);
    struct __user_cap_header_struct h = {_LINUX_CAPABILITY_VERSION_3, 0};
    struct __user_cap_data_struct d[2];
    memset(d, 0, sizeof(d));
    check(syscall(SYS_capset, &h, d) == 0);
    check(prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) == 0);
    check(prctl(PR_SET_DUMPABLE, 0, 0, 0, 0) == 0);
    memset(d, 0xff, sizeof(d));
    check(syscall(SYS_capget, &h, d) == 0);
    for (size_t i = 0; i < 2; i++) check(d[i].effective == 0 && d[i].permitted == 0 && d[i].inheritable == 0);
    check(prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_IS_SET, 0, 0, 0) == 0);
}
static void loopback_only(void) {
    int fd = socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    struct ifreq req;
    check(fd >= 0);
    memset(&req, 0, sizeof(req));
    memcpy(req.ifr_name, "lo", 3);
    check(ioctl(fd, SIOCGIFFLAGS, &req) == 0);
    req.ifr_flags = (short)(req.ifr_flags | IFF_UP);
    check(ioctl(fd, SIOCSIFFLAGS, &req) == 0);
    check(close(fd) == 0);
}
static void bind_ro(const char *source, const char *target, unsigned long extra) {
    check(mount(source, target, NULL, MS_BIND, NULL) == 0);
    check(mount(NULL, target, NULL, MS_BIND | MS_REMOUNT | MS_RDONLY | MS_NOSUID | extra, NULL) == 0);
}
static int launch(int argc, char **argv) {
    check(argc == 13 && geteuid() == 0);
    const char *phase = argv[11];
    check(strcmp(phase, "idle") == 0 || strcmp(phase, "h1_body") == 0
          || strcmp(phase, "h2_reader_frozen") == 0 || strcmp(phase, "blocked_response") == 0);
    fault_stage = argv[12];
    const char *allowed[] = {"none", "launcher_entered", "launcher_limits_set", "launcher_cgroup_joined",
        "launcher_namespaces_created", "launcher_mounts_sealed", "launcher_reaper_started",
        "launcher_privileges_dropped", "launcher_role_exec_entered", "role_nif_secured",
        "role_transport_started", "role_phase_armed", "role_ready_sent"};
    int found = 0;
    for (size_t i = 0; i < sizeof(allowed) / sizeof(allowed[0]); i++)
        if (strcmp(fault_stage, allowed[i]) == 0) found = 1;
    check(found);
    lifecycle(13, "launcher_entered");
    const char *cg = argv[2], *root = argv[3], *target = argv[4], *generation = argv[6], *case_id = argv[7];
    check(cg[0] == '/' && root[0] == '/' && target[0] == '/' && argv[8][0] == '/');
    check(strlen(generation) == 32 && strspn(generation, "0123456789abcdef") == 32);
    check(strlen(case_id) == 3 && case_id[0] == 'R' && atoi(case_id + 1) >= 1 && atoi(case_id + 1) <= 18);
    char *end = NULL;
    long descriptor = strtol(argv[5], &end, 10);
    check(end && *end == '\0' && descriptor >= 3 && descriptor < 256);
    struct ucred peer;
    socklen_t plen = sizeof(peer);
    check(getsockopt((int)descriptor, SOL_SOCKET, SO_PEERCRED, &peer, &plen) == 0);
    check(plen == sizeof(peer) && peer.uid == getuid() && peer.pid == (pid_t)strtol(argv[9], NULL, 10));
    /* SO_PEERCRED proves the pre-fork creator, not the later role sender. */
    int type = 0;
    socklen_t tlen = sizeof(type);
    check(getsockopt((int)descriptor, SOL_SOCKET, SO_TYPE, &type, &tlen) == 0 && type == SOCK_SEQPACKET);
    char filename[PATH_MAX], exe[PATH_MAX];
    limits(); /* inherited hard limits exist before the first task is contained */
    lifecycle(14, "launcher_limits_set");
    pathcat(filename, sizeof(filename), cg, "cgroup.procs");
    int cfd = open(filename, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    check(cfd >= 0);
    char pidtext[32];
    check(snprintf(pidtext, sizeof(pidtext), "%ld", (long)getpid()) > 0);
    exact_write(cfd, pidtext);
    check(close(cfd) == 0);
    lifecycle(15, "launcher_cgroup_joined");
    /* From this point every descendant inherits the owned kill domain. */
    check(unshare(CLONE_NEWNS | CLONE_NEWNET | CLONE_NEWPID | CLONE_NEWIPC | CLONE_NEWUTS) == 0);
    check(mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) == 0);
    loopback_only();
    namespaces_observed(0);
    lifecycle(16, "launcher_namespaces_created");
    check(mkdir(target, 0700) == 0);
    check(mount(root, target, NULL, MS_BIND, NULL) == 0);
    ssize_t exelen = readlink("/proc/self/exe", exe, sizeof(exe) - 1);
    check(exelen > 0 && exelen < (ssize_t)sizeof(exe));
    exe[exelen] = '\0';
    pathcat(filename, sizeof(filename), target, "opt/harness/fault_helper");
    bind_ro(exe, filename, 0);
    pathcat(filename, sizeof(filename), target, "opt/harness/role.exs");
    bind_ro(argv[8], filename, MS_NODEV | MS_NOEXEC);
    pathcat(filename, sizeof(filename), target, "opt/harness/control_nif.so");
    bind_ro(argv[10], filename, MS_NODEV);
    pathcat(filename, sizeof(filename), target, "dev/null");
    bind_ro("/dev/null", filename, MS_NOEXEC);
    pathcat(filename, sizeof(filename), target, "tmp");
    check(mount("tmpfs", filename, "tmpfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "size=8388608,mode=1777") == 0);
    check(mount(NULL, target, NULL, MS_BIND | MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV, NULL) == 0);
    lifecycle(17, "launcher_mounts_sealed");
    close_fds_except_control((int)descriptor);
    child_pid = fork();
    check(child_pid >= 0);
    if (child_pid == 0) {
        /* This is owned namespace PID 1. It reaps every role/helper descendant. */
        pathcat(filename, sizeof(filename), target, "proc");
        check(mount("proc", filename, "proc", MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL) == 0);
        check(chdir(target) == 0 && chroot(".") == 0 && chdir("/") == 0);
        namespaces_observed(1);
        lifecycle(18, "launcher_reaper_started");
        drop_privileges();
        lifecycle(19, "launcher_privileges_dropped");
        limits();
        child_pid = fork();
        check(child_pid >= 0);
        if (child_pid == 0) {
            check(getpid() == 2);
            char generation_env[80], case_env[32], phase_env[96], fault_env[128];
            check(snprintf(generation_env, sizeof(generation_env), "MIXER_HARNESS_GENERATION=%s", generation) > 0);
            check(snprintf(case_env, sizeof(case_env), "MIXER_HARNESS_CASE=%s", case_id) > 0);
            check(snprintf(phase_env, sizeof(phase_env), "MIXER_HARNESS_PHASE=%s", phase) > 0);
            check(snprintf(fault_env, sizeof(fault_env), "MIXER_HARNESS_FAULT_STAGE=%s", fault_stage) > 0);
            char *environment[] = {"PATH=/usr/bin:/bin", "LANG=C.UTF-8", "LC_ALL=C.UTF-8",
                "ERL_CRASH_DUMP=/dev/null", "ERL_CRASH_DUMP_SECONDS=0", generation_env, case_env, phase_env, fault_env, NULL};
            char *command[] = {"/usr/bin/elixir", "--erl",
                "+S 2:2 +SDcpu 1 +SDio 1 +A 2 +P 32768 +Q 1024 -start_epmd false",
                "/opt/harness/role.exs", NULL};
            lifecycle(20, "launcher_role_exec_entered");
            execve(command[0], command, environment);
            die();
        }
        check(close(3) == 0);
        (void)signal(SIGTERM, forward);
        (void)signal(SIGINT, forward);
        int status = 0, role_status = 0;
        pid_t role = (pid_t)child_pid, waited;
        while ((waited = waitpid(-1, &status, 0)) > 0 || errno == EINTR) {
            if (waited == role) role_status = status;
        }
        _exit(WIFEXITED(role_status) ? WEXITSTATUS(role_status) : 128 + WTERMSIG(role_status));
    }
    check(close(3) == 0);
    drop_privileges();
    (void)signal(SIGTERM, forward);
    int status = 0;
    while (waitpid((pid_t)child_pid, &status, 0) < 0) check(errno == EINTR);
    /* Namespace exit removes its private mounts; nothing remounts the host. */
    return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}
static void fault_report(unsigned attempts, unsigned reached, uint64_t start, unsigned kind) {
    printf("{\"schema\":1,\"event\":\"fault\",\"attempts\":%u,\"limitReached\":%u,\"elapsedNs\":%llu,\"kind\":%u}\n",
           attempts, reached, (unsigned long long)(monotonic_ns() - start), kind);
    check(fflush(stdout) == 0);
}
static int fault(const char *kind) {
    check(geteuid() == 65534 && prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0) == 1);
    check(getpid() > 2); /* only a child of the contained role */
    check(access("/sys/fs/cgroup/cgroup.procs", F_OK) != 0);
    limits();
    uint64_t start = monotonic_ns();
    if (strcmp(kind, "cpu") == 0) {
        alarm(6);
        volatile uint64_t value = 1;
        unsigned iterations = 0;
        while (monotonic_ns() - start < 5000000000ULL) {
            for (unsigned i = 0; i < 4096; i++) value = value * 6364136223846793005ULL + 1;
            iterations++;
        }
        (void)value;
        fault_report(iterations, 1, start, 1);
    } else if (strcmp(kind, "tasks") == 0) {
        pid_t children[160];
        unsigned count = 0, attempted = 0, reached = 0;
        for (unsigned i = 0; i < 160; i++) {
            attempted++;
            pid_t child = fork();
            if (child == -1) { check(errno == EAGAIN); reached = 1; break; }
            if (child == 0) { alarm(8); for (;;) pause(); }
            children[count++] = child;
        }
        for (unsigned i = 0; i < count; i++) check(kill(children[i], SIGTERM) == 0);
        for (unsigned i = 0; i < count; i++) {
            while (waitpid(children[i], NULL, 0) < 0) check(errno == EINTR);
        }
        fault_report(attempted, reached, start, 2);
    } else if (strcmp(kind, "fds") == 0) {
        int opened[320];
        unsigned count = 0, attempted = 0, reached = 0;
        for (unsigned i = 0; i < 320; i++) {
            attempted++;
            int fd = socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
            if (fd < 0) { check(errno == EMFILE); reached = 1; break; }
            opened[count++] = fd;
        }
        for (unsigned i = 0; i < count; i++) check(close(opened[i]) == 0);
        fault_report(attempted, reached, start, 3);
    } else if (strcmp(kind, "oom") == 0) {
        alarm(30);
        const size_t cap = (size_t)1280 * 1024 * 1024;
        volatile unsigned char *region = mmap(NULL, cap, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        check(region != MAP_FAILED);
        for (size_t i = 0; i < cap; i += 4096) region[i] = 0x5a;
        check(munmap((void *)region, cap) == 0);
        /* Reaching this report means the expected cgroup OOM did not happen. */
        fault_report(1, 0, start, 4);
    } else if (strcmp(kind, "crash") == 0) {
        check(kill(getppid(), SIGABRT) == 0);
        (void)raise(SIGABRT);
        die();
    } else die();
    return 0;
}
#endif
int main(int argc, char **argv) {
#ifdef __linux__
    if (argc > 1 && strcmp(argv[1], "launch") == 0) return launch(argc, argv);
    if (argc == 3 && strcmp(argv[1], "fault") == 0) return fault(argv[2]);
#else
    (void)argc; (void)argv;
#endif
    return 78;
}
