#include <errno.h>
#include <stdio.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Expected executable and optional arguments\n");
        return 2;
    }

    pid_t child = fork();
    if (child < 0) {
        perror("fork");
        return 2;
    }
    if (child == 0) {
        execv(argv[1], argv + 1);
        perror("execv");
        _exit(127);
    }

    int status;
    struct rusage usage;
    pid_t reaped;
    do {
        reaped = wait4(child, &status, 0, &usage);
    } while (reaped < 0 && errno == EINTR);
    if (reaped != child) {
        perror("wait4");
        return 2;
    }
    if (!WIFEXITED(status)) {
        fprintf(stderr, "Measured process terminated by signal %d\n", WTERMSIG(status));
        return 2;
    }
    if (WEXITSTATUS(status) != 0) {
        return WEXITSTATUS(status);
    }

    fprintf(stderr, "peak-rss-kib=%ld\n", usage.ru_maxrss);
    return 0;
}
