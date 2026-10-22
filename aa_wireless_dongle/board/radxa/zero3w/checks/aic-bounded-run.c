// SPDX-License-Identifier: MIT
/* A diagnostic deadline must not wait forever for an unkillable kernel task. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t interrupted;

static void stop(int number) { interrupted = number; }

static void pause_briefly(void)
{
    const struct timespec delay = {.tv_nsec = 10000000};
    (void)nanosleep(&delay, NULL);
}

static void kill_group(pid_t child)
{
    (void)kill(-child, SIGKILL);
    (void)kill(child, SIGKILL); /* Also covers failure before setsid(). */
}

int main(int argc, char **argv)
{
    char *end = NULL;
    long seconds = argc > 1 ? strtol(argv[1], &end, 10) : 0;
    if (argc < 3 || !end || !*argv[1] || *end || seconds < 1 || seconds > 600 ||
        getenv("RADXA_BOUNDED_RUN_ACTIVE"))
        return 2;
    struct timespec deadline, now;
    if (clock_gettime(CLOCK_MONOTONIC, &deadline)) return 125;
    deadline.tv_sec += seconds;
    struct sigaction action = {.sa_handler = stop};
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGTERM, &action, NULL) || sigaction(SIGINT, &action, NULL) ||
        sigaction(SIGHUP, &action, NULL)) return 125;
    pid_t child = fork();
    if (child < 0) return 125;
    if (!child) {
        if (setsid() < 0) _exit(126);
        if (setenv("RADXA_BOUNDED_RUN_ACTIVE", "1", 1)) _exit(126);
        action.sa_handler = SIG_DFL;
        (void)sigaction(SIGTERM, &action, NULL);
        (void)sigaction(SIGINT, &action, NULL);
        (void)sigaction(SIGHUP, &action, NULL);
        execvp(argv[2], &argv[2]);
        perror("diagnostic exec");
        _exit(127);
    }
    int status = 0, result = 125;
    for (;;) {
        pid_t reaped = waitpid(child, &status, WNOHANG);
        if (reaped == child) {
            kill_group(child);
            return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
        }
        if (interrupted) { result = 128 + interrupted; break; }
        if (reaped < 0 && errno != EINTR) break;
        if (clock_gettime(CLOCK_MONOTONIC, &now)) break;
        if (now.tv_sec > deadline.tv_sec ||
            (now.tv_sec == deadline.tv_sec && now.tv_nsec >= deadline.tv_nsec)) {
            result = 124;
            break;
        }
        pause_briefly();
    }
    kill_group(child);
    for (int attempt = 0; attempt < 20; attempt++) {
        if (waitpid(child, &status, WNOHANG) == child) return result;
        pause_briefly();
    }
    fprintf(stderr, "Diagnostic child %ld remains unreaped; returning %d.\n",
            (long)child, result);
    return result;
}
